import os
import sys
sys.path.append('..')
import cv2
import time
import signal
import tempfile
import numpy as np
import libs.gphoto2 as gp

_instance = None

def signal_handler(sig, frame):
    print("\nCtrl+C detected. Exiting gracefully...")
    if _instance: _instance.close()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

if not gp.cameraList().count():
    raise SystemExit('Cannot find any gPhoto2 camera.')

_instance = gp.camera()
tmp_output = None

try:
    # Print summary
    print(_instance.summary())

    # Retrieve settings (For EOS 2000D: https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/cameras/canon-eos2000d.txt)
    config = _instance.get_config()

    # Print avilable settings
    print('Available parameters:')
    print("\n".join(config.list_paths()))

    # Print some
    print('/main/capturesettings/shutterspeed', config.get_path('/main/capturesettings/shutterspeed').get_value())
    print('/main/imgsettings/iso', config.get_path('/main/imgsettings/iso').get_value())

    # Update some
    manufacturer = config.get_path('/main/status/manufacturer').get_value()
    if manufacturer == 'Canon Inc.':
        # From https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/cameras/canon-eos2000d.txt
        current_mode = config.get_path('/main/capturesettings/autoexposuremode').get_value()
        if current_mode in ['Manual', 'TV']:
            config.get_path('/main/capturesettings/shutterspeed').set_value('1/125')
        if current_mode in ['Manual', 'AV']:
            config.get_path('/main/capturesettings/aperture').set_value('13')
        config.get_path('/main/capturesettings/focusmode').set_value('One Shot')
        config.get_path('/main/imgsettings/iso').set_value('100')
    elif manufacturer == 'Nikon Corporation':
        # From https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/cameras/nikon-z6.txt
        current_mode = config.get_path('/main/capturesettings/expprogram').get_value()
        if current_mode in ['M', 'S']:
            config.get_path('/main/capturesettings/shutterspeed').set_value('1/125')
        if current_mode in ['M', 'A']:
            config.get_path('/main/capturesettings/f-number').set_value('f/13')
        config.get_path('/main/capturesettings/focusmode').set_value('AF-S')
        config.get_path('/main/imgsettings/iso').set_value('100')
    elif manufacturer == 'Sony Corporation':
        # From https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/cameras/sony-a7c.txt
        current_mode = config.get_path('/main/capturesettings/expprogram').get_value()
        if current_mode in ['M', 'S']:
            config.get_path('/main/capturesettings/shutterspeed').set_value('1/125')
        if current_mode in ['M', 'A']:
            config.get_path('/main/capturesettings/f-number').set_value('f/13')
        config.get_path('/main/capturesettings/focusmode').set_value('AF-A')
        config.get_path('/main/imgsettings/iso').set_value('100')
    else:
        print(f'Unsupported camera model: {manufacturer}')

    # Commit changes
    _instance.commit_config(config)

    # Trigger capture to focus
    _instance.capture_image()

    # Display preview
    PREVIEW_TO_FILE = False
    fd, tmp_output = tempfile.mkstemp(suffix='.jpg')
    os.close(fd)
    last_frame_at = None
    fps = None
    while True:
        if PREVIEW_TO_FILE:
            # Capture is saved into a local file
            _instance.capture_preview(tmp_output)
            im = cv2.imread(tmp_output)
        else:
            # Capture is directly read as bytes array
            cfile = _instance.capture_preview()
            buf = np.frombuffer(cfile.get_data(), dtype=np.uint8)
            im = cv2.imdecode(buf, cv2.IMREAD_COLOR)

        if im is None:
            continue

        now = time.perf_counter()
        if last_frame_at is not None:
            instant_fps = 1.0 / max(now - last_frame_at, 1e-6)
            fps = instant_fps if fps is None else (fps * 0.9 + instant_fps * 0.1)
        last_frame_at = now

        height, width = im.shape[:2]
        overlay = f'{width}x{height} | {fps:.1f} FPS' if fps is not None else f'{width}x{height} | measuring FPS'
        display = im.copy()
        cv2.putText(display, overlay, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2, cv2.LINE_AA)
        cv2.imshow('Camera', display)
        if cv2.waitKey(1) > 0:
            break

    # Trigger capture (Can also be captured as a bytes array)
    _instance.capture_image('./capture.jpg')

except Exception as e:
    print(e)

finally:
    if _instance:
        _instance.close()
    if tmp_output and os.path.exists(tmp_output):
        os.remove(tmp_output)
    cv2.destroyAllWindows()
