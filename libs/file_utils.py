import os
import tempfile
import cv2
import numpy as np

class FileUtils:
    @staticmethod
    def _odd_kernel_size(limit, preferred=51):
        size = max(1, min(int(preferred), int(limit)))
        if size % 2 == 0:
            size = max(1, size - 1)
        return size

    @staticmethod
    def get_small_path(path):
        directory = os.path.dirname(path)
        filename = os.path.basename(path)
        name, ext = os.path.splitext(filename)
        new_filename = f"{name}_small{ext}"
        return os.path.join(directory, new_filename)

    @staticmethod
    def write_image(path, image):
        """Write an image atomically and raise on failure."""
        directory = os.path.dirname(path) or '.'
        os.makedirs(directory, exist_ok=True)

        fd, tmp_path = tempfile.mkstemp(prefix='.tmp_', suffix=os.path.splitext(path)[1] or '.img', dir=directory)
        os.close(fd)

        try:
            if image is None:
                raise ValueError(f'Cannot write empty image to {path}')
            if not cv2.imwrite(tmp_path, image):
                raise IOError(f'cv2.imwrite failed for {path}')
            os.replace(tmp_path, path)
        except Exception:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            raise

        return path

    @staticmethod
    def move_file(src_path, dst_path):
        """Move a file and raise with context on failure."""
        src_path = os.fspath(src_path)
        dst_path = os.fspath(dst_path)

        if not os.path.isfile(src_path):
            raise FileNotFoundError(f'Source file does not exist: {src_path}')

        dst_dir = os.path.dirname(dst_path) or '.'
        os.makedirs(dst_dir, exist_ok=True)

        try:
            os.replace(src_path, dst_path)
        except Exception as exc:
            raise OSError(f'Failed to move {src_path} to {dst_path}: {exc}') from exc

        return dst_path

    @staticmethod
    def remove_file(path, missing_ok=True):
        """Remove a file with optional tolerance for missing paths."""
        path = os.fspath(path)

        try:
            os.remove(path)
        except FileNotFoundError:
            if missing_ok:
                return False
            raise
        except IsADirectoryError as exc:
            raise OSError(f'Expected file but found directory: {path}') from exc
        except Exception as exc:
            raise OSError(f'Failed to remove file {path}: {exc}') from exc

        return True

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
    def blurry_borders(im, size, blur_cache=None, refresh_blur=True, return_cache=False):
        """
        Add blurry borders to an image.
        OPTIMIZED: Reduced blur kernel size from (101,101) to (51,51) for 4x faster performance.
        """
        width, height = (max(1, int(size[0])), max(1, int(size[1])))
        im_height, im_width = im.shape[:2]

        if im_width <= 0 or im_height <= 0:
            return im

        # Resize image to match screen
        scale_factor = min(height / im_height, width / im_width)
        new_size = (int(im_width * scale_factor), int(im_height * scale_factor))
        if new_size[0] <= 0 or new_size[1] <= 0:
            return (im, blur_cache) if return_cache else im
        im = cv2.resize(im, new_size, interpolation=cv2.INTER_AREA)

        im_height, im_width = im.shape[:2]
        difference_h = int((width - im_width) // 2)
        difference_v = int((height - im_height) // 2)

        cache_signature = (width, height, im_width, im_height)
        should_refresh_blur = (
            refresh_blur
            or blur_cache is None
            or blur_cache.get('signature') != cache_signature
        )

        if should_refresh_blur:
            # Recompute the blurred background only when geometry changes or every n frames.
            blurred_image = cv2.GaussianBlur(im, (51, 51), 0)
            blur_cache = {
                'signature': cache_signature,
                'blurred_image': blurred_image,
                'difference_h': difference_h,
                'difference_v': difference_v,
            }
        else:
            blurred_image = blur_cache['blurred_image']
            difference_h = blur_cache['difference_h']
            difference_v = blur_cache['difference_v']

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
        
        return (combined_image, blur_cache) if return_cache else combined_image

    @staticmethod
    def extract_blurred_region(image, screen_size, region, blur_kernel_size=51):
        """
        Stretch the source image to the screen size, then crop and blur one region.

        `region` uses Kivy coordinates: (x, y, width, height) with y starting at the bottom.
        """
        if image is None:
            return None

        screen_width = max(1, int(screen_size[0]))
        screen_height = max(1, int(screen_size[1]))
        x, y, width, height = [int(v) for v in region]
        target_width = max(1, width)
        target_height = max(1, height)

        stretched = cv2.resize(image, (screen_width, screen_height), interpolation=cv2.INTER_LINEAR)

        left = max(0, min(screen_width, x))
        right = max(left + 1, min(screen_width, x + width))
        top = max(0, min(screen_height, screen_height - (y + height)))
        bottom = max(top + 1, min(screen_height, screen_height - y))

        region_image = stretched[top:bottom, left:right]
        if region_image.size == 0:
            return None

        if region_image.shape[1] != target_width or region_image.shape[0] != target_height:
            region_image = cv2.resize(region_image, (target_width, target_height), interpolation=cv2.INTER_LINEAR)

        kernel_size = FileUtils._odd_kernel_size(min(region_image.shape[:2]), preferred=blur_kernel_size)
        if kernel_size > 1:
            region_image = cv2.GaussianBlur(region_image, (kernel_size, kernel_size), 0)

        return region_image
