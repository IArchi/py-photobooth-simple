import sys
import cv2
import numpy as np

sys.path.append('..')
from libs.device_utils import DeviceUtils

# Connect to camera
devices = DeviceUtils()
gphoto2_camera = devices.get_gphoto2_proxy()

if gphoto2_camera:
    while True:
        buf = gphoto2_camera.get_preview()
        buf = np.frombuffer(buf, np.uint8)
        im = cv2.imdecode(buf, cv2.IMREAD_ANYCOLOR)
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        size, buf = im.shape, im.tostring()
        image_array = np.frombuffer(buf, dtype=np.uint8)
        im = image_array.reshape((size[1], size[0], 3))
        im = cv2.flip(im, 0)
        #im = cv2.flip(im, 1)
        cv2.imshow('Gphoto2 camera', im)
        if cv2.waitKey(1) > 0: break
    cv2.destroyAllWindows()
else:
    print('No gphoto2 camera found')
