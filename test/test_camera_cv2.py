import sys
import cv2
import numpy as np

sys.path.append('..')
from libs.device_utils import Cv2Camera

# Connect to camera
cv2_camera = Cv2Camera()

# Display preview
while True:
    im = cv2_camera.get_preview()
    if im is None: continue
    print('size', im.shape)

    cv2_camera.cv2_imshow(im)
    if cv2.waitKey(1) > 0: break
cv2.destroyAllWindows()
