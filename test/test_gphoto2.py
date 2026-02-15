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
        match manufacturer:
            case 'Canon Inc.':
                # From https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/cameras/canon-eos2000d.txt
                current_mode = config.get_path('/main/capturesettings/autoexposuremode').get_value()
                if current_mode in ['Manual', 'TV']:
                    config.get_path('/main/capturesettings/shutterspeed').set_value('1/125')
                if current_mode in ['Manual', 'AV']:
                    config.get_path('/main/capturesettings/aperture').set_value('13')
                    config.get_path('/main/capturesettings/focusmode').set_value('One Shot')
                    config.get_path('/main/imgsettings/iso').set_value('100')
                break

            case 'Nikon Corporation':
                # From https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/cameras/nikon-z6.txt
                current_mode = config.get_path('/main/capturesettings/expprogram').get_value()
                if current_mode in ['M', 'S']:
                    config.get_path('/main/capturesettings/shutterspeed').set_value('1/125')
                if current_mode in ['M', 'A']:
                    config.get_path('/main/capturesettings/f-number').set_value('f/13')
                config.get_path('/main/capturesettings/focusmode').set_value('AF-S')
                config.get_path('/main/imgsettings/iso').set_value('100')
                break

            case 'Sony Corporation':
                # From https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/cameras/sony-a7c.txt
                current_mode = config.get_path('/main/capturesettings/expprogram').get_value()
                if current_mode in ['M', 'S']:
                    config.get_path('/main/capturesettings/shutterspeed').set_value('1/125')
                if current_mode in ['M', 'A']:
                    config.get_path('/main/capturesettings/f-number').set_value('f/13')
                config.get_path('/main/capturesettings/focusmode').set_value('AF-A')
                config.get_path('/main/imgsettings/iso').set_value('100')
                break

            case _:
                Logger.info('Unsupported camera model: %s', manufacturer)
                return

        # Commit changes
        _instance.commit_config(config)

        # Trigger capture to focus
        _instance.capture_image()

        # Display preview
        PREVIEW_TO_FILE = False
        _, tmp_output = tempfile.mkstemp(suffix='.jpg')
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

            # Display
            cv2.imshow('Camera', im)
            if cv2.waitKey(1) > 0: break

        # Trigger capture (Can also be captured as a bytes array)
        _instance.capture_image('./capture.jpg')
    
    catch Exception as e:
        print(e)

    # Release camera
    _instance.close()
