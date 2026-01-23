import sys
import cv2

sys.path.append('..')
from libs.file_utils import FileUtils
from libs.device_utils import DeviceUtils

def _merge_transparency(bg_image, fg_image, alpha_overlay=0.5):
    fg_image = FileUtils.resize_and_crop(fg_image, bg_image.shape)
    return cv2.addWeighted(bg_image, 1 - alpha_overlay, fg_image, alpha_overlay, 0)

# Connect to cameras
devices = DeviceUtils()
if devices._preview == devices._capture:
    print('Your system is not hybrid (DSLR + Webcam or DSLR + piCamera).')
    print('Zoom to set in configuration:')
    print('CALIBRATION = None')
else:
    current_zoom = 1.0
    current_x_offset = 0
    current_y_offset = 0
    while True:
        # Read capture image
        capture_im = devices._capture.get_preview()
        if capture_im is None: continue
        capture_im = cv2.flip(capture_im, 0)

        # Read preview image
        preview_im = devices._preview.get_preview()
        if preview_im is None: continue
        preview_im = cv2.flip(preview_im, 0)

        if current_zoom < 1.0:
            # Zoom should apply on capture image
            capture_im = FileUtils.zoom(capture_im, (1.0/current_zoom, current_x_offset, current_y_offset))
            im = _merge_transparency(preview_im, capture_im)
        else:
            # Zoom should apply on preview image
            preview_im = FileUtils.zoom(preview_im, (current_zoom, current_x_offset, current_y_offset))
            im = _merge_transparency(capture_im, preview_im)

        # Display info
        im = cv2.putText(im, 'Zoom (Keys: + or -): {}'.format(current_zoom), (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        im = cv2.putText(im, 'Offset X (Keys: x or c): {}'.format(current_x_offset), (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        im = cv2.putText(im, 'Offset Y (Keys: y or u): {}'.format(current_y_offset), (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        im = cv2.putText(im, 'Reset (Key: r)', (10, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
        im = cv2.putText(im, 'Exit (Key: q)', (10, 250), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)

        # Display images
        cv2.imshow('Calibration', im)

        # Controls
        key = cv2.waitKey(1)
        if key == ord('q') or key == 27: break
        elif key == ord('r'): current_zoom = 1.0
        elif key == ord('+'): current_zoom += .1
        elif key == ord('-'): current_zoom -= .1
        elif key == ord('x'): current_x_offset += 5
        elif key == ord('c'): current_x_offset -= 5
        elif key == ord('y'): current_y_offset += 5
        elif key == ord('u'): current_y_offset -= 5
        current_zoom = round(max(0.1, current_zoom), 2)

        if current_zoom == 1.0:
            current_x_offset = 0
            current_y_offset = 0

    cv2.destroyAllWindows()

    print('Zoom to set in configuration:')
    print('CALIBRATION = {}'.format((current_zoom, current_x_offset, current_y_offset)))
