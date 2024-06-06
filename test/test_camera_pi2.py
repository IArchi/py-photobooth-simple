import sys
import cv2
import numpy as np

sys.path.append('..')
from libs.device_utils import DeviceUtils

from picamera2 import Picamera2

picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": 'XRGB8888', "size": (640, 480)}))
picam2.start()

while True:
    im = picam2.capture_array()
    cv2.imshow("PiCamera2", im)
    cv2.waitKey(0)


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
