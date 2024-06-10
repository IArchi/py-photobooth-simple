import sys

sys.path.append('..')
from libs.device_utils import Picamera2Camera

import cv2
from picamera2 import Picamera2, Preview

picam2 = Picamera2(verbose_console=0)
picam2.configure(picam2.create_preview_configuration(main={'format': 'RGB888', 'size': (1920, 1080)}))
picam2.start_preview(Preview.NULL)
picam2.start()
picam2.set_controls({"AfMode": 1 ,"AfTrigger": 0}) # Continuous autofocus

cv2.startWindowThread()
cv2.namedWindow('Camera', flags=cv2.WINDOW_GUI_NORMAL)
while True:
    im = picam2.capture_array()
    im = cv2.rotate(im, cv2.ROTATE_180)
    cv2.imshow("Camera", im)
    cv2.waitKey(1)

cv2.destroyAllWindows()


# # Connect to camera
camera = Picamera2Camera()
while True:
    camera.get_preview()
    im = camera.get_preview()
    if im is None: continue
    print('size', im.shape)

    camera.cv2_imshow(im)
    if cv2.waitKey(1) > 0: break
cv2.destroyAllWindows()

#https://github.com/sightmachine/SimpleCV2/blob/21f5199d29c6b377073aa8834b6b0ebefca8ec75/SimpleCV/ImageClass.py#L998
#https://github.com/sightmachine/SimpleCV2/blob/master/SimpleCV/Camera.py#L1425
