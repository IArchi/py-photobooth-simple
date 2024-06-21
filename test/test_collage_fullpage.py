import sys
import cv2

sys.path.append('..')
from libs.collage import CollageManager

# Example usage
preview_path = CollageManager.FULLPAGE.get_preview()
im = cv2.imread(preview_path)
cv2.imshow('Preview', im)
cv2.waitKey(0)
