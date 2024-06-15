import sys
import cv2

sys.path.append('..')
from libs.device_utils import Cv2Camera

# Connect to camera
camera = Cv2Camera()
while True:
    im = camera.get_preview()
    if im is None: continue
    print('size', im.shape)

    camera.cv2_imshow(im)
    if cv2.waitKey(1) > 0: break
cv2.destroyAllWindows()
