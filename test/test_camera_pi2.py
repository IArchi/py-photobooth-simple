import sys
import cv2

sys.path.append('..')
from libs.device_utils import Picamera2Camera

# # Connect to camera
camera = Picamera2Camera(port=0)
camera.focus()
while True:
    im = camera.get_preview()
    if im is None:
        print('image is None')
        continue
    print('size', im.shape)

    camera.cv2_imshow(im)
    if cv2.waitKey(1) > 0: break
cv2.destroyAllWindows()
