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

if gp.cameraList().count():
    _instance = gp.camera()

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
    print('/main/actions/eosremoterelease', config.get_path('/main/actions/eosremoterelease').get_value())

    # Update some
    current_mode = config.get_path('/main/capturesettings/autoexposuremode').get_value()
    if current_mode in ['Manual', 'TV']:
        config.get_path('/main/capturesettings/shutterspeed').set_value('1/125')
    if current_mode in ['Manual', 'AV']:
        config.get_path('/main/capturesettings/aperture').set_value('13')
    config.get_path('/main/capturesettings/focusmode').set_value('One Shot')
    config.get_path('/main/imgsettings/iso').set_value('100')

    # Commit changes
    _instance.commit_config(config)

    # Trigger capture to focus
    cfile = _instance.capture_image()


    with open('temp.jpg', 'wb') as file:
        file.write(cfile.get_data())
    im = cv2.imread('temp.jpg')
    cv2.imshow('Camera', im)


    # Display preview
    _, tmp_output = tempfile.mkstemp(suffix='.jpg')
    while True:
        # Capture
        _instance.capture_preview(tmp_output)

        # Convert to CV2
        im = cv2.imread(tmp_output)

        # Display
        cv2.imshow('Camera', im)
        if cv2.waitKey(1) > 0: break

    # Trigger capture
    _instance.capture_image('./capture.jpg')

    # Release camera
    _instance.close()
