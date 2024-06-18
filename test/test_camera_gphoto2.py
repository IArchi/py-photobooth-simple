import sys
import cv2

sys.path.append('..')
from libs.device_utils import Gphoto2Camera

# Connect to camera
camera = Gphoto2Camera()
while False:
    im = camera.get_preview()
    if im is None: continue
    camera.cv2_imshow(im)
    if cv2.waitKey(1) > 0: break

# Trigger capture
camera.capture('test.jpg')
im = cv2.imread('test.jpg')
cv2.imshow('camera', im)
cv2.destroyAllWindows()
