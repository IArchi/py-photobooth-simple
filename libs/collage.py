import os
import cv2
import tempfile
import numpy as np
from kivy.logger import Logger

from libs.file_utils import FileUtils

class Collage:
    def __init__(self, count=1, print_params={}, squared=False, overlay=None):
        Logger.info('Collage: __init__()')
        self._count = count
        self._print_params = print_params
        self._squared = squared
        self._margin_percent = 5
        _module_dir = os.path.dirname(os.path.abspath(__file__))
        self._dummy = os.path.join(_module_dir, '../doc/dummy.png')
        self._overlay = os.path.join(_module_dir, overlay)

    def get_photos_required(self):
        Logger.info('Collage: get_photos_required()')
        return self._count

    def is_squared(self):
        Logger.info('Collage: is_squared()')
        return self._squared

    def get_print_params(self):
        Logger.info('Collage: get_print_params()')
        return self._print_params

    def get_preview(self):
        pass

    def assemble(self, image_paths, target_size=(1000, 1000), output_path=None):
        pass

    def _resize(self, image, max_size=(1080, 1920)):
        # Get original dimensions
        height, width = image.shape[:2]

        # Calculate aspect ratio
        aspect_ratio = width / height

        # Determine new dimensions based on the aspect ratio
        if width > max_size[1] or height > max_size[0]:
            if (max_size[1] / width) < (max_size[0] / height):
                new_width = max_size[1]
                new_height = int(new_width / aspect_ratio)
            else:
                new_height = max_size[0]
                new_width = int(new_height * aspect_ratio)

            resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        else:
            # If image is within the maximum dimensions, return the original image
            resized_image = image

        return resized_image

    def _apply_overlay(self, image, overlay_path):
        # Read the overlay image
        overlay = cv2.imread(overlay_path, cv2.IMREAD_UNCHANGED)

        # Ensure the overlay is the same size as the target image
        overlay = cv2.resize(overlay, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_AREA)

        if overlay.shape[2] == 4:  # If overlay has alpha channel
            alpha_overlay = overlay[:, :, 3] / 255.0
            alpha_image = 1.0 - alpha_overlay

            for c in range(0, 3):
                image[:, :, c] = (alpha_overlay * overlay[:, :, c] + alpha_image * image[:, :, c])
        else:
            # If no alpha channel, just blend with some transparency (optional)
            alpha_overlay = 0.5  # This can be adjusted
            image = cv2.addWeighted(image, 1 - alpha_overlay, overlay, alpha_overlay, 0)

        return image

class FullpageCollage(Collage):
    def __init__(self, overlay=None):
        super(FullpageCollage, self).__init__(count=1, print_params={'PageSize':'w288h432', 'print-scaling':'fit'}, squared=False, overlay=overlay)

    def get_preview(self):
        collage = self.assemble([self._dummy])
        collage = FileUtils.resize(collage)

        # Dump to temp file
        _, tmp_output = tempfile.mkstemp(suffix='.jpg')
        cv2.imwrite(tmp_output, collage)
        return tmp_output

    def assemble(self, image_paths, target_size=(2880, 4370), output_path=None):
        # Read the original image
        img = cv2.imread(image_paths[0], cv2.IMREAD_COLOR)

        # Calculate margin size
        margin_height = int(target_size[0] * (self._margin_percent / 100))
        margin_width = int(target_size[1] * (self._margin_percent / 100))

        # Calculate new size considering margins
        new_height = target_size[0] - 2 * margin_height
        new_width = target_size[1] - 2 * margin_width

        # Resize the image
        img_resized = FileUtils.resize_and_crop(img, (new_height, new_width))

        # Create a new image with the target size and fill it with white
        new_img = np.full((target_size[0], target_size[1], 3), 255, dtype=np.uint8)

        # Paste the resized image onto the new image with margins
        new_img[margin_height:margin_height + new_height, margin_width:margin_width + new_width] = img_resized

        # Add overlay
        new_img = self._apply_overlay(new_img, self._overlay)

        # Dump to file
        if output_path:
            cv2.imwrite(output_path, new_img)

            # Create preview
            small = FileUtils.resize(new_img)
            cv2.imwrite(FileUtils.get_small_path(output_path), small)

        return new_img

class StripCollage(Collage):
    def __init__(self, overlay=None):
        super(StripCollage, self).__init__(count=3, print_params={'PageSize':'w288h432-div2', 'print-scaling':'fit'}, squared=True, overlay=overlay)

    def get_preview(self):
        image_paths = [self._dummy for _ in range(self._count)]
        collage = self.assemble(image_paths)
        collage = FileUtils.resize(collage)

        # Dump to temp file
        _, tmp_output = tempfile.mkstemp(suffix='.jpg')
        cv2.imwrite(tmp_output, collage)
        return tmp_output

    def assemble(self, image_paths, target_size=(4370, 1440), output_path=None):
        # Calculate margin size
        margin_height = int(target_size[0] * (self._margin_percent / 100))
        margin_width = int(target_size[1] * (self._margin_percent / 100))
        margin_width = margin_height = min(margin_height, margin_width)

        # Calculate new size considering margins
        new_width = target_size[1] - 2 * margin_width

        # Load images
        images = [cv2.imread(img_path) for img_path in image_paths]

        if self._squared:
            # Resize images to square
            images = [FileUtils.resize_and_crop(img, (new_width, new_width)) for img in images]
        else:
            # Resize to fit width
            images = [FileUtils.resize_and_crop(img, (None, new_width)) for img in images]

        # Create a new image with the target size and fill it with white
        new_img = np.full((target_size[0], target_size[1], 3), 255, dtype=np.uint8)

        # Calculate vertical position to align images (as many as possible)
        current_y = margin_height
        for img in images:
            height, width = img.shape[:2]
            if current_y + height <= target_size[0]:  # Check if there's enough space vertically
                new_img[current_y:current_y + height, margin_width:margin_width + width] = img
                current_y += height + margin_height
            else:
                break

        # Add overlay
        new_img = self._apply_overlay(new_img, self._overlay)

        # Dump to file
        if output_path:
            # Print two strips at once
            new_img = cv2.hconcat([new_img, new_img])
            cv2.imwrite(output_path, new_img)

            # Create preview
            small = FileUtils.resize(new_img)
            cv2.imwrite(FileUtils.get_small_path(output_path), small)

        return new_img
