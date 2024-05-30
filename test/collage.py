import cv2
import sys
import numpy as np
from PIL import Image
from PIL import ImageOps

sys.path.append('..')
from libs.collage import CollageManager


def create_dummy(filename):
    height, width = 6944, 9152
    b, g, r = 0x75, 0x75, 0x75#0x3E, 0x88, 0xE5  # orange
    image = np.zeros((height, width, 3), np.uint8)
    image[:, :, 0] = b
    image[:, :, 1] = g
    image[:, :, 2] = r
    cv2.imwrite(filename, image)

# Create 3 dummies
photos = []
for i in range(0, 4):
    filename = 'dummy_{}.jpg'.format(i)
    create_dummy(filename)
    photos.append(filename)

logo_slim = '../logo_slim.png'
logo_thick = '../logo_thick.png'

# Process collage
CollageManager.PORTRAIT_8x3.assemble(output_name='portrait_8x3.jpg', photos=photos[:3], logo=logo_thick)
CollageManager.PORTRAIT_8x6.assemble(output_name='portrait_8x6.jpg', photos=photos[:2], logo=logo_slim)

CollageManager.LANDSCAPE_6x8.assemble(output_name='landscape_6x8.jpg', photos=photos[:1], logo=logo_slim)
CollageManager.LANDSCAPE_6x8_2COLS.assemble(output_name='landscape_6x8_2cols.jpg', photos=photos[:3], logo=logo_thick)
