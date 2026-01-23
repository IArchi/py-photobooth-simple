import os
import cv2
import numpy as np

class FileUtils:
    @staticmethod
    def get_small_path(path):
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        name, ext = os.path.splitext(filename)
        new_filename = f"{name}_small{ext}"
        return os.path.join(directory, new_filename)

    @staticmethod
    def resize(image, max_height=1080, max_width=1920):
        # Get original dimensions
        height, width = image.shape[:2]

        # Calculate aspect ratio
        aspect_ratio = width / height

        # Determine new dimensions based on the aspect ratio
        if width > max_width or height > max_height:
            if (max_width / width) < (max_height / height):
                new_width = max_width
                new_height = int(new_width / aspect_ratio)
            else:
                new_height = max_height
                new_width = int(new_height * aspect_ratio)

            resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        else:
            # If image is within the maximum dimensions, return the original image
            resized_image = image

        return resized_image

    @staticmethod
    def resize_and_crop(image, target_size):
        """
        Resize and crop an image to exactly match the target size.
        OPTIMIZED: Single-pass resize when possible to improve performance.
        
        Args:
            image: Input image (numpy array)
            target_size: Tuple (height, width) - exact target dimensions
            
        Returns:
            Image with exactly the target dimensions
        """
        if target_size[0] is None and target_size[1] is None:
            return image
        
        img_height, img_width = image.shape[:2]
        target_height, target_width = target_size
        
        # Handle cases where only one dimension is specified
        if target_size[0] is None:
            new_width = target_width
            new_height = int(new_width * img_height / img_width)
            return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        if target_size[1] is None:
            new_height = target_height
            new_width = int(new_height * img_width / img_height)
            return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        # Both dimensions specified - optimize for single resize when possible
        aspect_ratio_image = img_width / img_height
        aspect_ratio_target = target_width / target_height
        
        # Calculate intermediate size for resize
        if aspect_ratio_image > aspect_ratio_target:
            # Image is wider: crop width, keep height proportional
            scale = target_height / img_height
            crop_width = int(target_width / scale)
            crop_x = (img_width - crop_width) // 2
            
            # Crop first, then resize (more efficient)
            cropped = image[:, crop_x:crop_x + crop_width]
            return cv2.resize(cropped, (target_width, target_height), interpolation=cv2.INTER_AREA)
        else:
            # Image is taller: crop height, keep width proportional
            scale = target_width / img_width
            crop_height = int(target_height / scale)
            crop_y = (img_height - crop_height) // 2
            
            # Crop first, then resize (more efficient)
            cropped = image[crop_y:crop_y + crop_height, :]
            return cv2.resize(cropped, (target_width, target_height), interpolation=cv2.INTER_AREA)

    @staticmethod
    def zoom(im, zoom=(1.0, 0, 0)):
        h, w, _ = [ int(zoom[0] * i) for i in im.shape ]
        if zoom[0] < 1.0: raise Exception('Zoom must be greater than 1.0')
        cx, cy = w/2, h/2
        im = cv2.resize(im, (0, 0), fx=zoom[0], fy=zoom[0])
        cx = cx - zoom[1]
        cy = cy - zoom[2]
        y_start = max(0, int(round(cy - h / (2 * zoom[0]))))
        y_end = min(int(round(cy + h / (2 * zoom[0]))), im.shape[0])
        x_start = max(0, int(round(cx - w / (2 * zoom[0]))))
        x_end = min(int(round(cx + w / (2 * zoom[0]))), im.shape[1])
        return im[y_start:y_end, x_start:x_end, :]

    @staticmethod
    def blurry_borders(im, size):
        """
        Add blurry borders to an image.
        OPTIMIZED: Reduced blur kernel size from (101,101) to (51,51) for 4x faster performance.
        """
        width, height = size
        im_height, im_width = im.shape[:2]

        # Resize image to match screen
        scale_factor = min(height / im_height, width / im_width)
        new_size = (int(im_width * scale_factor), int(im_height * scale_factor))
        im = cv2.resize(im, new_size, interpolation=cv2.INTER_AREA)

        # Generate blur on sides (OPTIMIZED: reduced kernel from 101 to 51)
        blurred_image = cv2.GaussianBlur(im, (51, 51), 0)
        im_height, im_width = im.shape[:2]
        difference_h = int((width - im_width) // 2)
        difference_v = int((height - im_height) // 2)
        if difference_h > 0:
            left_blur = blurred_image[:, :difference_h]
            right_blur = blurred_image[:, max(0, im_width - difference_h):]
            combined_image = np.hstack((left_blur, im, right_blur))
        elif difference_v > 0:
            top_blur = blurred_image[:difference_v, :]
            bottom_blur = blurred_image[max(0, im_height - difference_v):, :]
            combined_image = np.vstack((top_blur, im, bottom_blur))
        else:
            combined_image = im
        
        return combined_image
