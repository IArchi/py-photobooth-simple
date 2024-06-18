import sys
sys.path.append('..')
import cv2
import tempfile
import numpy as np
import libs.gphoto2 as gp

if gp.cameraList().count():
    _instance = gp.camera()

    # Print summary
    #print(_instance.summary())

    # Retrieve settings (For EOS 2000D: https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/cameras/canon-eos2000d.txt)
    config = _instance.get_config()

    # Print avilable settings
    #print('Available parameters:')
    #print("\n".join(config.list_paths()))

    # Print some
    print('/main/capturesettings/shutterspeed', config.get_path('/main/capturesettings/shutterspeed').get_value())
    print('/main/imgsettings/iso', config.get_path('/main/imgsettings/iso').get_value())

    # Update some
    #config.get_path('/main/actions/viewfinder').set_value(1) # Autofocus (If it does not work, use main.actions.eosremoterelease)
    config.get_path('/main/capturesettings/focusmode').set_value('Manual')
    config.get_path('/main/capturesettings/focusmode').set_value('One Shot')
    config.get_path('/main/capturesettings/aperture').set_value('8')
    #config.get_path('/main/capturesettings/shutterspeed').set_value('1/160')
    config.get_path('/main/imgsettings/iso').set_value('400')

    # Commit changes
    _instance.commit_config(config)

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
