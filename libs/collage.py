import cv2
import numpy as np
import tempfile
from kivy.logger import Logger

class Collage:
    def __init__(self, count=1, print_format=None, squared=False):
        Logger.info('Collage: __init__()')
        self._count = count
        self._print_format = print_format
        self._squared = squared

    def get_photos_required(self):
        Logger.info('Collage: get_photos_required()')
        return self._count

    def is_squared(self):
        return self._squared

    def get_print_format(self):
        Logger.info('Collage: get_print_format()')
        return self._print_format

    def get_preview(self, logo_path=None):
        return

    def assemble(self, output_path='collage.jpg', image_paths=[], logo_path=None):
        return
    
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
        super(StripCollage, self).__init__(count=count, print_format='Custom.3x8in', squared=False)

    def get_preview(self, logo_path=None):
        Logger.info('StripCollage: get_preview()')
        photos = [tempfile.mkstemp(suffix='.jpg') for i in range(0, 3)]
        photos = [p[1] for p in photos]
        print(photos)
        for p in photos: self._create_dummy_photo(p)
        tmp_file, tmp_output = tempfile.mkstemp(suffix='.jpg')
        self.assemble(tmp_output, photos, logo_path)
        return tmp_output

    def assemble(self, output_path='collage.jpg', image_paths=[], logo_path=None):
        Logger.info('StripCollage: assemble({})'.format(output_path))

        # Define the size of the output image
        output_width, output_height = 3000, 8000

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
        result = cv2.vconcat(images_with_margin)

        # Compute free spaces
        available_height = output_height - result.shape[0]
        
        # Create border to fill output's height
        result = cv2.copyMakeBorder(result, 0, available_height, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))

        # Load logo
        if logo_path:
            logo_image = cv2.imread(logo_path)

            # Resize logo to fit the available height and width
            logo_aspect_ratio = logo_image.shape[1] / logo_image.shape[0]
            logo_width = min(int(logo_aspect_ratio * available_height), output_width)
            logo_height = int(logo_width / logo_aspect_ratio)
            
            resized_logo = cv2.resize(logo_image, (logo_width, logo_height))
        
            # Calculate the position to paste the logo
            logo_start_x = (output_width - logo_width) // 2
            logo_start_y = output_height - available_height + (available_height - logo_height) // 2  # Center vertically in the available space
            
            # Paste the logo onto the collage
            result[logo_start_y:logo_start_y+logo_height, logo_start_x:logo_start_x+logo_width] = resized_logo

        # Save the collage
        cv2.imwrite(output_path, result)

class PolaroidCollage(Collage):
    def __init__(self, count=1):
        super(PolaroidCollage, self).__init__(count=count, print_format='Custom.6x8in', squared=True)

    def get_preview(self, logo_path=None):
        Logger.info('PolaroidCollage: get_preview()')
        tmp_file, tmp_input = tempfile.mkstemp(suffix='.jpg')
        self._create_dummy_photo(tmp_input, squared=True)
        tmp_file, tmp_output = tempfile.mkstemp(suffix='.jpg')
        self.assemble(tmp_output, [tmp_input], logo_path)
        return tmp_output

    def assemble(self, output_path='collage.jpg', image_paths=[], logo_path=None):
        if len(image_paths) != self._count: raise Exception('Not enough photos to assemble. Expected {}.'.format(self._count))

        # Load the input image
        input_image = cv2.imread(image_paths[0])
        
        # Define the size of the output image
        output_width, output_height = 6000, 8000
        
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
            logo_image = cv2.imread(logo_path)

            # Resize logo to fit the available height
            logo_height = available_height
            logo_width = int(logo_image.shape[1] * (logo_height / logo_image.shape[0]))
            resized_logo = cv2.resize(logo_image, (logo_width, logo_height))
        
            # Calculate the position to paste the logo
            logo_start_x = (output_width - logo_width) // 2
            logo_start_y = start_y + image_size + border_size
            
            # Paste the logo onto the polaroid image
            polaroid_image[logo_start_y:logo_start_y+logo_height, logo_start_x:logo_start_x+logo_width] = resized_logo
        
        # Write to file
        cv2.imwrite(output_path, polaroid_image)

class CollageManager:
    STRIP = StripCollage(count=3)
    POLAROID = PolaroidCollage(count=1)
