import sys

sys.path.append('..')
from libs.device_utils import DeviceUtils

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
# devices = DeviceUtils()
# pi2_camera = devices.get_picamera2_proxy()

# if pi2_camera:
#     while True:
#         size, buf = devices.get_preview()
#         if buf is None: continue
#         image_array = np.fromstring(buf, dtype=np.uint8)
#         im = image_array.reshape((size[1], size[0], 3))
#         cv2.imshow('PiCamera2', im)
#         if cv2.waitKey(1) > 0: break
#     cv2.destroyAllWindows()
# else:
#     print('Cannot find any picamera2 camera')

#https://github.com/sightmachine/SimpleCV2/blob/21f5199d29c6b377073aa8834b6b0ebefca8ec75/SimpleCV/ImageClass.py#L998
#https://github.com/sightmachine/SimpleCV2/blob/master/SimpleCV/Camera.py#L1425
