import cv2
import numpy as np
from kivy.logger import Logger

class Collage:
    def __init__(self, count=1, print_params={}, squared=False):
        Logger.info('Collage: __init__()')
        self._count = count
        self._print_params = print_params
        self._squared = squared
        self._margin_percent = 5

    def get_photos_required(self):
        Logger.info('Collage: get_photos_required()')
        return self._count

    def is_squared(self):
        Logger.info('Collage: is_squared()')
        return self._squared

    def get_print_params(self):
        Logger.info('Collage: get_print_params()')
        return self._print_params

    def get_preview(self, overlay=None):
        pass

    def assemble(self, image_paths, overlay=None):
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

    def _resize_and_crop(self, image, target_size):
        # Calculate aspect ratios
        aspect_ratio_image = image.shape[1] / image.shape[0]

        if target_size[0] is None:
            # Calculate new height based on the provided target width and original aspect ratio
            new_width = target_size[1]
            new_height = int(new_width / aspect_ratio_image)
        elif target_size[1] is None:
            # Calculate new width based on the provided target height and original aspect ratio
            new_height = target_size[0]
            new_width = int(new_height * aspect_ratio_image)
        else:
            aspect_ratio_target = target_size[1] / target_size[0]
            if aspect_ratio_image > aspect_ratio_target:
                # Image is wider than the target: fit height, crop width
                new_height = target_size[0]
                new_width = int(new_height * aspect_ratio_image)
            else:
                # Image is taller than the target: fit width, crop height
                new_width = target_size[1]
                new_height = int(new_width / aspect_ratio_image)

        # Resize image to the new size
        resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)

        # Center crop to the target size if both dimensions are provided
        if target_size[0] is not None and target_size[1] is not None:
            crop_x = (new_width - target_size[1]) // 2
            crop_y = (new_height - target_size[0]) // 2
            cropped_image = resized_image[crop_y:crop_y + target_size[0], crop_x:crop_x + target_size[1]]
            return cropped_image
        else:
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
    def __init__(self):
        super(FullpageCollage, self).__init__(count=1, print_params={'PageSize':'w288h432', 'print-scaling':'fill'}, squared=False)

    def get_preview(self, overlay=None):
        collage = self.assemble(['../doc/dummy.png'], overlay=overlay)
        collage = self._resize(collage)
        return collage

    def assemble(self, image_paths, target_size=(2480, 3840), margin_percent=5, overlay=None):
        # Read the original image
        img = cv2.imread(image_paths[0], cv2.IMREAD_COLOR)

        # Calculate margin size
        margin_height = int(target_size[0] * (margin_percent / 100))
        margin_width = int(target_size[1] * (margin_percent / 100))

        # Calculate new size considering margins
        new_height = target_size[0] - 2 * margin_height
        new_width = target_size[1] - 2 * margin_width

        # Resize the image
        img_resized = self._resize_and_crop(img, (new_height, new_width))

        # Create a new image with the target size and fill it with white
        new_img = np.full((target_size[0], target_size[1], 3), 255, dtype=np.uint8)

        # Paste the resized image onto the new image with margins
        new_img[margin_height:margin_height + new_height, margin_width:margin_width + new_width] = img_resized

        # Add overlay
        if overlay: new_img = self._apply_overlay(new_img, overlay)

        return new_img

class StripCollage(Collage):
    def __init__(self):
        super(StripCollage, self).__init__(count=4, print_params={'PageSize':'w288h432-div2', 'print-scaling':'fill'}, squared=True)

    def get_preview(self, overlay=None):
        image_paths = ['../doc/dummy.png' for _ in range(self._count)]
        collage = self.assemble(image_paths, overlay=overlay)
        collage = self._resize(collage)
        return collage

    def assemble(self, image_paths, target_size=(3840, 1240), overlay=None):
        # Calculate margin size
        margin_height = int(target_size[0] * (self._margin_percent / 100))
        margin_width = int(target_size[1] * (self._margin_percent / 100))
        margin_width = margin_height = min(margin_height, margin_width)

        # Calculate new size considering margins
        new_height = target_size[0] - 2 * margin_height
        new_width = target_size[1] - 2 * margin_width

        # Load images
        images = [cv2.imread(img_path) for img_path in image_paths]

        if self._squared:
            # Resize images to square
            images = [self._resize_and_crop(img, (new_width, new_width)) for img in images]
        else:
            # Resize to fit width
            images = [self._resize_and_crop(img, (None, new_width)) for img in images]

        # Create a new image with the target size and fill it with white
        new_img = np.full((target_size[0], target_size[1], 3), 255, dtype=np.uint8)

        # Calculate vertical position to align images (as many as possible)
        total_height = sum(img.shape[0] for img in images)
        current_y = margin_height
        for img in images:
            height, width = img.shape[:2]
            if current_y + height <= target_size[0]:  # Check if there's enough space vertically
                new_img[current_y:current_y + height, margin_width:margin_width + width] = img
                current_y += height + margin_height
            else:
                break

        # Add overlay
        if overlay: new_img = self._apply_overlay(new_img, overlay)

        return new_img

# Main program to process the images
if __name__ == "__main__":
    strip =  StripCollage()
    strip_preview = strip.get_preview(overlay='../overlay.png')
    strip_collage = strip.assemble(['../doc/dummy.png' for _ in range(4)], overlay='../overlay.png')

    fullpge = FullpageCollage()
    fullpge_preview = fullpge.get_preview(overlay='../overlay.png')
    fullpge_collage = fullpge.assemble(['../doc/dummy.png'], overlay='../overlay.png')

    # Display the final image
    cv2.imshow('Preview', strip_preview)
    cv2.imshow('Collage', strip_collage)
    cv2.waitKey(0)
    cv2.imshow('Preview', fullpge_preview)
    cv2.imshow('Collage', fullpge_collage)
    cv2.waitKey(0)
