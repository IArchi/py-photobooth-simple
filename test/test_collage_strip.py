import cv2
import sys

sys.path.append('..')
from libs.collage import CollageManager

# Example usage
preview_path = CollageManager.STRIP.get_preview()
im = cv2.imread(preview_path)
cv2.imshow('Preview', im)
cv2.waitKey(0)
