import sys
import cv2
import numpy as np

sys.path.append('..')
from libs.device_utils import DeviceUtils

# Connect to camera
devices = DeviceUtils()
cv2_camera = devices.get_cv2_proxy()

if cv2_camera:
    while True:
        size, buf = devices.get_preview()
        if buf is None: continue
        image_array = np.frombuffer(buf, dtype=np.uint8)
        im = image_array.reshape((size[1], size[0], 3))
        im = cv2.flip(im, 0)
        #im = cv2.flip(im, 1)
        cv2.imshow('CV2 camera', im)
        if cv2.waitKey(1) > 0: break
    cv2.destroyAllWindows()
else:
    print('No CV2 camera found')