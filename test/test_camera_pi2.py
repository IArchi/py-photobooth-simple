import sys
import cv2

sys.path.append('..')
from libs.device_utils import Picamera2Camera

# # Connect to camera
camera = Picamera2Camera(port=0)
while True:
    im = camera.get_preview()
    if im is None: continue
    camera.cv2_imshow(im)
    if cv2.waitKey(1) > 0: break

# Trigger capture
camera.capture('test.jpg')
cv2.destroyAllWindows()
