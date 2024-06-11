import sys

sys.path.append('..')
from libs.device_utils import Picamera2Camera

# The following code works with Camera module v3
import cv2
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
picam2.set_controls({"AfMode": controls.AfModeEnum.Continuous,"AfSpeed": controls.AfSpeedEnum.Fast})
start_time = time.time()
job = picam2.autofocus_cycle(wait=False)

for i in range(0, 100):
    if job.get_result():
        print(f'Autofocused: {time.time() - start_time}s')
        picam2.switch_mode_and_capture_file(still_config, 'test.jpg')
        picam2.stop()
        break
    time.sleep(0.1)



# # Connect to camera
camera = Picamera2Camera(port=0)
camera.focus()
while True:
    camera.get_preview()
    im = camera.get_preview()
    if im is None: continue
    print('size', im.shape)

    camera.cv2_imshow(im)
    if cv2.waitKey(1) > 0: break
cv2.destroyAllWindows()
