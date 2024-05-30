import os
import cv2
import math
from kivy.logger import Logger

class Collage:
    # TODO : Use a better way to create layout. PSD with replace images ?
    def __init__(self, count=1, hw_ratio=8/6, two_cols=False, print_format=None, preview=None):
        Logger.info('Collage: __init__()')
        self._count = count
        self._hw_ratio = hw_ratio
        self._two_cols = two_cols
        self._print_format = print_format
        self._preview = preview

    def get_photos_required(self):
        Logger.info('Collage: get_photos_required()')
        return self._count

    def get_print_format(self):
        Logger.info('Collage: get_print_format()')
        return self._print_format

    def get_preview(self):
        Logger.info('Collage: get_preview()')
        return self._preview

    def assemble(self, output_name='collage.jpg', photos=[], logo=None):
        Logger.info('Collage: assemble({})'.format(output_name))
        if len(photos) != self._count: raise Exception('Invalid photos amount. Expected', self._count, 'got', len(photos))
        if self._two_cols:
            columns = [
                self._build_column(hw_ratio=self._hw_ratio*2, photos=photos[:2], logo=None),
                self._build_column(hw_ratio=self._hw_ratio*2, photos=photos[-1:], logo=logo)
            ]
            # Merge columns together
            max_height = max(col.shape[0] for col in columns)
            for i in range(len(columns)):
                if columns[i].shape[0] < max_height:
                    columns[i] = cv2.copyMakeBorder(columns[i], 0, max_height - columns[i].shape[0], 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            result = cv2.hconcat(columns)
        else:
            result = self._build_column(hw_ratio=self._hw_ratio, photos=photos, logo=logo)

        # Write to file
        cv2.imwrite(output_name, result)

    def _build_column(self, hw_ratio=8/3, photos=[], logo=None):
        Logger.info('Collage: _build_column()')
        # Read all photos
        images = [cv2.imread(photo) for photo in photos]

        # Resize images to make the widths match
        max_width = max(img.shape[1] for img in images)
        resized_images = [cv2.resize(img, (max_width, int(img.shape[0] * max_width / img.shape[1]))) for img in images]

        # Stack images with margins
        margin = int(max_width * 0.05)
        images_with_margin = []
        for i in range(len(resized_images)):
            images_with_margin.append(cv2.copyMakeBorder(resized_images[i], margin, 0, margin, margin, cv2.BORDER_CONSTANT, value=(255, 255, 255)))
        result = cv2.vconcat(images_with_margin)

        # Load logo
        if logo and os.path.exists(logo):
            logo = cv2.imread(logo)
            logo = cv2.resize(logo, (max_width, int(logo.shape[0] * max_width / logo.shape[1])))
            logo = cv2.copyMakeBorder(logo, margin, margin, margin, margin, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            required_height = result.shape[0] + logo.shape[0]
        else:
            required_height = result.shape[0]
        required_width = result.shape[1]

        # Compute size to match paper format
        output_width = int(required_height / hw_ratio)
        output_height = int(required_width * hw_ratio)
        if output_height < required_height + margin: # Includes last image bottom margin
            output_height = max(int(output_width * hw_ratio), required_height + margin)
            output_width = int(output_height / hw_ratio)
        else:
            output_width = max(int(output_height / hw_ratio), required_width)
            output_height = int(output_width * hw_ratio)

        # Compute free spaces
        free_space_height = output_height - result.shape[0]
        free_space_width = output_width - required_width

        if logo is not None:
            logo_top_margin = math.floor((free_space_height - logo.shape[0]) / 2) if free_space_height > 0 else 0
            logo_bottom_margin = (free_space_height - logo.shape[0] - logo_top_margin) if free_space_height > 0 else 0
            logo = cv2.copyMakeBorder(logo, logo_top_margin, logo_bottom_margin, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
            result = cv2.vconcat([result, logo])
            output_margin_bottom = 0
        else:
            output_margin_bottom = free_space_height

        # Add margins to match paper format
        output_margin_left = math.floor(free_space_width / 2)
        output_margin_right = free_space_width - output_margin_left
        result = cv2.copyMakeBorder(result, 0, output_margin_bottom, output_margin_left, output_margin_right, cv2.BORDER_CONSTANT, value=(255, 255, 255))

        return result

class CollageManager:
    PORTRAIT_8x3 = Collage(count=3, hw_ratio=8/3, print_format='Custom.3x8in', preview='./assets/layouts/PORTRAIT_8x3.jpg')
    PORTRAIT_8x6 = Collage(count=2, hw_ratio=8/6, print_format='Custom.6x8in', preview='./assets/layouts/PORTRAIT_8x6.jpg')
    LANDSCAPE_6x8 = Collage(count=1, hw_ratio=6/8, print_format='Custom.6x8in', preview='./assets/layouts/LANDSCAPE_6x8.jpg')
    LANDSCAPE_6x8_2COLS = Collage(count=3, hw_ratio=6/8, two_cols=True, print_format='Custom.6x8in', preview='./assets/layouts/LANDSCAPE_6x8_2COLS.jpg')
