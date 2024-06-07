import sys

sys.path.append('..')
from libs.device_utils import DeviceUtils

import io
import cv2
import numpy as np
from threading import Condition
from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            nparr = np.frombuffer(buf, np.uint8)
            self.frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            self.condition.notify_all()

# Start reccording MJPEG
picam2 = Picamera2()
video_config = picam2.create_video_configuration(main={"size": (1920, 1080)})
picam2.configure(video_config)
output = StreamingOutput()
picam2.start_recording(MJPEGEncoder(), FileOutput(output))

# Read frames and trigger a capture every 30 frames
i = 0
while True:
    with output.condition:
        output.condition.wait()
        frame = output.frame
        print('MJPEG', frame.shape)

        if i % 30 == 0:
            print('Capture')
            request = picam2.capture_request()
            buf = request.make_array('main')
            request.release()
            capture = cv2.cvtColor(buf, cv2.COLOR_RGBA2BGR)
            print('Capture:', capture.shape)
        i += 1


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
