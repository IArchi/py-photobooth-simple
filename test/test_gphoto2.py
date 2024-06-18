import sys
sys.path.append('..')
import cv2
import numpy as np
import libs.gphoto2 as gp

if gp.cameraList().count():
    _instance = gp.camera()
    _instance.capture_preview() # Apparently first call always fails

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
    config.get_path('/main/actions/autofocusdrive').set_value(1) # Autofocus (If it does not work, use main.actions.eosremoterelease)
    config.get_path('/main/capturesettings/focusmode').set_value('Manual')
    config.get_path('/main/capturesettings/focusmode').set_value('One Shot')
    config.get_path('/main/capturesettings/aperture').set_value('8')
    #config.get_path('/main/capturesettings/shutterspeed').set_value('1/160')
    config.get_path('/main/imgsettings/iso').set_value('400')

    # Display preview
    while True:
        # Capture
        cfile = _instance.capture_preview()
        if cfile is None: continue
        buf = cfile.get_data(auto_clean=True) # Must clean to avoid memory leak or call cfile.clean() once finished

        # Convert to CV2
        buf = np.frombuffer(buf, np.uint8)
        print(len(buf))
        im = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        print(im, im.shape)

        # Display
        cv2.imshow('Camera', im)
        if cv2.waitKey(1) > 0: break

    # Trigger capture
    _instance.capture_image('./capture.jpg')

    # Release camera
    _instance.close()
