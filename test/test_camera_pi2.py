import sys

sys.path.append('..')
from libs.device_utils import Picamera2Camera

import cv2
import time
from picamera2 import Picamera2
from libcamera import controls

picam2 = Picamera2()

preview_config = picam2.create_preview_configuration(main={'format': 'RGB888', 'size': (2304, 1296)})
still_config = picam2.create_still_configuration(main={"size": (2304, 1296), "format": "RGB888"})
picam2.configure(preview_config)
picam2.start()
print('Started')
picam2.set_controls({"AfMode": controls.AfModeEnum.Auto,"AfSpeed": controls.AfSpeedEnum.Fast})
job = picam2.autofocus_cycle(wait=False)

#cv2.startWindowThread()
#cv2.namedWindow('Camera', flags=cv2.WINDOW_GUI_NORMAL)
frame_count = 0
start_time = time.time()
while True:
    im = picam2.capture_array()
    im = cv2.rotate(im, cv2.ROTATE_180)
    #cv2.imshow("Camera", im)
    if frame_count % 100 == 0 and job.get_result():
        print('Capture !')
        picam2.switch_mode_and_capture_file(still_config, 'test_{}.jpg'.format(frame_count))
    frame_count += 1
    elapsed_time = time.time() - start_time

    if elapsed_time >= 1:
        # Calculate FPS
        fps = frame_count / elapsed_time

        # Print FPS
        print("FPS:", fps)

        # Reset frame count and start time
        frame_count = 0
        start_time = time.time()

picam2.stop()


# The following code works with Camera module v3
import time
from picamera2 import Picamera2
from libcamera import controls

picam2 = Picamera2()

preview_config = picam2.create_preview_configuration(main={'format': 'RGB888', 'size': (1920, 1080)}, controls={'FrameRate': 30})
still_config = picam2.create_still_configuration(main={"size": (1920, 1080), "format": "RGB888"}, buffer_count=1, controls={'FrameRate': 30})
picam2.configure(preview_config)

def print_af_state(request):
    md = request.get_metadata()
    print(("Idle", "Scanning", "Success", "Fail")[md['AfState']], md.get('LensPosition'))

picam2.pre_callback = print_af_state
picam2.start()
print('Started')
picam2.set_controls({"AfMode": controls.AfModeEnum.Auto,"AfSpeed": controls.AfSpeedEnum.Fast})
start_time = time.time()
job = picam2.autofocus_cycle(wait=False)

for i in range(0, 100):
    if job.get_result(): break
    time.sleep(0.1)
print(f'Autofocused: {time.time() - start_time}s')
picam2.switch_mode_and_capture_file(still_config, 'test.jpg')
picam2.stop()


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
