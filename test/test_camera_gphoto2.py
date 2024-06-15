import sys
import cv2
import numpy as np

sys.path.append('..')
from libs.device_utils import Gphoto2Camera

# Connect to camera
camera = Gphoto2Camera()
camera.capture('truc.jpg')
while True:
    im = camera.get_preview()
    if im is None: continue
    print('size', im.shape)

    camera.cv2_imshow(im)
    if cv2.waitKey(1) > 0: break
cv2.destroyAllWindows()
