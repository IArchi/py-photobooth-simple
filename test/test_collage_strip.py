import cv2
import sys

sys.path.append('..')
from libs.collage import *

# Example usage
strip = StripCollage(overlay='../overlays/strip.png')
preview_path = strip.get_preview()
im = cv2.imread(preview_path)
cv2.imshow('Preview', im)
cv2.waitKey(0)
