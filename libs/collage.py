import cv2
import numpy as np
import tempfile
from kivy.logger import Logger

class Collage:
    def __init__(self, count=1, print_params={}, squared=False):
        Logger.info('Collage: __init__()')
        self._count = count
        self._print_params = print_params
        self._squared = squared

    def get_photos_required(self):
        Logger.info('Collage: get_photos_required()')
        return self._count

    def is_squared(self):
        return self._squared

    def get_print_params(self):
        Logger.info('Collage: get_print_params()')
        return self._print_params

    def get_preview(self, logo_path=None):
        return

    def assemble(self, output_path='collage.jpg', image_paths=[], logo_path=None):
        return

    def _resize(self, output_path, image, max_height=1080, max_width=1920):
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

        cv2.imwrite(output_path, resized_image)

    def _create_dummy_photo(self, filename, squared=False):
        height, width = (1080, 1920) if not squared else (1080, 1080)
        b, g, r = 0x75, 0x75, 0x75
        image = np.zeros((height, width, 3), np.uint8)
        image[:, :, 0] = b
        image[:, :, 1] = g
        image[:, :, 2] = r
        cv2.imwrite(filename, image)

class StripCollage(Collage):
    def __init__(self, count=3):
        super(StripCollage, self).__init__(count=count, print_params={'PageSize':'dnp6x8', 'Cutter':'2Inch'}, squared=False)

    def get_preview(self, logo_path=None):
        Logger.info('StripCollage: get_preview()')
        photos = [tempfile.mkstemp(suffix='.jpg') for i in range(0, 3)]
        photos = [p[1] for p in photos]
        for p in photos: self._create_dummy_photo(p)
        _, tmp_output = tempfile.mkstemp(suffix='.jpg')
        self.assemble((tmp_output, None), photos, logo_path)
        return tmp_output

    def assemble(self, output_path='collage.jpg', image_paths=[], logo_path=None):
        Logger.info('StripCollage: assemble({})'.format(output_path))

        # Define the size of the output image
        output_width, output_height = 1240, 3688 # Pixels*DPI/25.4 (25.4mm = 1 inch)

        # Calculate the size and position to paste the input image
        border_size = int(output_width * 0.05)
        image_size = output_width - 2 * border_size

        # Read all photos
        images = [cv2.imread(photo) for photo in image_paths]

        # Resize images keeping ratio
        resized_images = [cv2.resize(img, (image_size, int(img.shape[0] * image_size / img.shape[1]))) for img in images]

        # Stack images with margins
        images_with_margin = []
        for i in range(len(resized_images)):
            images_with_margin.append(cv2.copyMakeBorder(resized_images[i], border_size, 0, border_size, border_size, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
        strip_image = cv2.vconcat(images_with_margin)

        # Compute free spaces
        available_height = output_height - strip_image.shape[0]

        # Create border to fill output's height
        strip_image = cv2.copyMakeBorder(strip_image, 0, available_height, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))

        if logo_path:
            # Load logo with alpha channel
            logo_image = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)

            # Check if the logo image has an alpha channel
            if logo_image.shape[2] == 4:
                alpha_channel = logo_image[:, :, 3]
            else:
                # Create an alpha channel filled with 255 (fully opaque)
                alpha_channel = np.ones((logo_image.shape[0], logo_image.shape[1]), dtype=logo_image.dtype) * 255

            # Resize logo to fit the available height and width
            logo_aspect_ratio = logo_image.shape[1] / logo_image.shape[0]
            logo_width = min(int(logo_aspect_ratio * available_height), output_width)
            logo_height = int(logo_width / logo_aspect_ratio)

            resized_logo = cv2.resize(logo_image, (logo_width, logo_height))
            resized_alpha = cv2.resize(alpha_channel, (logo_width, logo_height))

            # Calculate the position to paste the logo
            logo_start_x = (output_width - logo_width) // 2
            logo_start_y = output_height - available_height + (available_height - logo_height) // 2  # Center vertically in the available space

            # Blend the logo onto the collage
            for c in range(0, 3):
                strip_image[logo_start_y:logo_start_y+logo_height, logo_start_x:logo_start_x+logo_width, c] = \
                    resized_logo[:, :, c] * (resized_alpha / 255.0) + \
                    strip_image[logo_start_y:logo_start_y+logo_height, logo_start_x:logo_start_x+logo_width, c] * (1.0 - resized_alpha / 255.0)

        if type(output_path) is str:
            print('hconcat')
            # Duplicate for print
            strip_image = cv2.hconcat([strip_image, strip_image])

            # Write to file
            cv2.imwrite(output_path, strip_image)
        elif type(output_path) is tuple and len(output_path) == 2:
            # First element is for preview only
            self._resize(output_path[0], strip_image)

            # Second element is for printing
            if output_path[1]:
                # Duplicate for print
                strip_image = cv2.hconcat([strip_image, strip_image])

                # Write to file
                cv2.imwrite(output_path[1], strip_image)
        else:
            raise Exception('Unhandled output_path. Must be a string or a tuple(2) for small and large files.')

class PolaroidCollage(Collage):
    def __init__(self, count=1):
        super(PolaroidCollage, self).__init__(count=count, print_params={'PageSize':'dnp6x8', 'Cutter':'Normal'}, squared=True)

    def get_preview(self, logo_path=None):
        Logger.info('PolaroidCollage: get_preview()')
        _, tmp_input = tempfile.mkstemp(suffix='.jpg')
        self._create_dummy_photo(tmp_input, squared=True)
        _, tmp_output = tempfile.mkstemp(suffix='.jpg')
        self.assemble((tmp_output, None), [tmp_input], logo_path)
        return tmp_output

    def assemble(self, output_path='collage.jpg', image_paths=[], logo_path=None):
        if len(image_paths) != self._count: raise Exception('Not enough photos to assemble. Expected {}.'.format(self._count))

        # Load the input image
        input_image = cv2.imread(image_paths[0])

        # Define the size of the output image
        output_width, output_height = 2480, 3688 # 156.13 x 104.99 mm at 600 dpi  => Pixels*DPI/25.4 (25.4mm = 1 inch)

        # Create a new image with white background
        polaroid_image = np.ones((output_height, output_width, 3), dtype=np.uint8) * 255

        # Calculate the size and position to paste the input image
        border_size = int(output_width * 0.05)
        image_size = output_width - 2 * border_size

        # Resize the input image to fit within the borders
        input_image = cv2.resize(input_image, (image_size, image_size))

        # Calculate the position to paste the input image
        start_y = border_size
        start_x = border_size

        # Paste the input image onto the polaroid image
        polaroid_image[start_y:start_y+image_size, start_x:start_x+image_size] = input_image

        # Calculate available height for the logo including the bottom border
        available_height = output_height - (start_y + image_size + 2 * border_size)

        if logo_path:
            # Load logo with alpha channel
            logo_image = cv2.imread(logo_path, cv2.IMREAD_UNCHANGED)

            # Check if the logo image has an alpha channel
            if logo_image.shape[2] == 4:
                alpha_channel = logo_image[:, :, 3]
            else:
                # Create an alpha channel filled with 255 (fully opaque)
                alpha_channel = np.ones((logo_image.shape[0], logo_image.shape[1]), dtype=logo_image.dtype) * 255

            # Resize logo to fit the available height
            logo_height = available_height
            logo_width = int(logo_image.shape[1] * (logo_height / logo_image.shape[0]))
            resized_logo = cv2.resize(logo_image, (logo_width, logo_height))
            resized_alpha = cv2.resize(alpha_channel, (logo_width, logo_height))

            # Calculate the position to paste the logo
            logo_start_x = (output_width - logo_width) // 2
            logo_start_y = start_y + image_size + border_size

            # Blend the logo onto the polaroid image
            for c in range(0, 3):
                polaroid_image[logo_start_y:logo_start_y+logo_height, logo_start_x:logo_start_x+logo_width, c] = \
                    resized_logo[:, :, c] * (resized_alpha / 255.0) + \
                    polaroid_image[logo_start_y:logo_start_y+logo_height, logo_start_x:logo_start_x+logo_width, c] * (1.0 - resized_alpha / 255.0)

        if type(output_path) is str:
            # Write to file
            cv2.imwrite(output_path, polaroid_image)
        elif type(output_path) is tuple and len(output_path) == 2:
            # First element is for preview only
            self._resize(output_path[0], polaroid_image)

            # Second element is for printing
            if output_path[1]: cv2.imwrite(output_path[1], polaroid_image)
        else:
            raise Exception('Unhandled output_path. Must be a string or a tuple(2) for small and large files.')

class CollageManager:
    STRIP = StripCollage(count=3)
    POLAROID = PolaroidCollage(count=1)
