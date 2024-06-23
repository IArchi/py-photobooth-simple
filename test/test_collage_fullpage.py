import sys
import cv2

sys.path.append('..')
from libs.collage import *

# Example usage
fullpage = FullpageCollage(overlay='../overlays/fullpage.png')
preview_path = fullpage.get_preview()
im = cv2.imread(preview_path)
cv2.imshow('Preview', im)
cv2.waitKey(0)
