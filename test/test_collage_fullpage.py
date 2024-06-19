import sys
import cv2

sys.path.append('..')
from libs.collage import CollageManager

# Example usage
no_logo = CollageManager.FULLPAGE.get_preview()
logo = CollageManager.FULLPAGE.get_preview('../logo.png')

# Display
image_no_logo = cv2.imread(no_logo)
image_logo = cv2.imread(logo)
cv2.imshow('No logo', image_no_logo)
cv2.imshow('Logo', image_logo)
cv2.waitKey(0)