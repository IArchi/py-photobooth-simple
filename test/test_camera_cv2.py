import sys
import time
import cv2

sys.path.append('..')
from libs.device_utils import Cv2Camera

# Connect to camera
camera = Cv2Camera()
last_frame_at = None
fps = None
while True:
    im = camera.get_preview()
    if im is None:
        continue

    now = time.perf_counter()
    if last_frame_at is not None:
        instant_fps = 1.0 / max(now - last_frame_at, 1e-6)
        fps = instant_fps if fps is None else (fps * 0.9 + instant_fps * 0.1)
    last_frame_at = now

    height, width = im.shape[:2]
    overlay = f'{width}x{height} | {fps:.1f} FPS' if fps is not None else f'{width}x{height} | measuring FPS'
    display = cv2.flip(im, 0)
    cv2.putText(display, overlay, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.imshow('Camera', display)
    if cv2.waitKey(1) > 0: break

# Trigger capture
camera.capture('test.jpg')
camera.close()
cv2.destroyAllWindows()
