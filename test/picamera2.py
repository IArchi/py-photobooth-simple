import sys
import cv2
import numpy as np

sys.path.append('..')
from libs.device_utils import DeviceUtils

# Connect to camera
devices = DeviceUtils()
pi2_camera = devices.get_picamera2_proxy()

from picamera2 import Picamera2

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
picam2.start()

while True:
    im = picam2.capture_array()
    cv2.imshow("PiCamera2", im)
    cv2.waitKey(0)

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