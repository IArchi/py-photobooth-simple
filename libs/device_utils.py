import os
import tempfile
import numpy as np
from kivy.logger import Logger
from threading import Condition

try:
    import cups
except ImportError:
    cups = None

try:
    from picamera2 import Picamera2
    from libcamera import controls
except ImportError:
    Picamera2 = None

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None

try:
    import libs.gphoto2 as gp
except:
    gp = None

class CaptureDevice:
    _instance = None

    def get_preview(self, square=False):
        pass

    def capture(self, output_name, square=False, flash_fn=None):
        pass

    def has_physical_flash(self):
        return False

    def _crop_to_square(self, image):
        height, width, _ = image.shape

        # Determine the size of the square
        size = min(width, height)

        # Calculate the coordinates for the crop
        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size

        # Crop the image
        return image[top:bottom, left:right]

    def _resize(self, output_path, image, max_height=1080, max_width=1920):
        # Get original dimensions
        height, width = image.shape[:2]

        # Calculate aspect ratio
        aspect_ratio = width / height

        # Determine new dimensions based on the aspect ratio
        if width > max_width or height > max_height:
            if (max_width / width) < (max_height / height):
                new_width = max_width
                new_height = int(new_width / aspect_ratio)
            else:
                new_height = max_height
                new_width = int(new_height * aspect_ratio)

            resized_image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        else:
            # If image is within the maximum dimensions, return the original image
            resized_image = image

        cv2.imwrite(output_path, resized_image)

    def _get_original_path(self, path):
        filename = os.path.basename(path)
        name, ext = os.path.splitext(filename)
        return f"{name}_original{ext}"

    def cv2_imshow(self, im, size=None):
        if size: im = im.reshape((size[1], size[0], 3))
        im = cv2.flip(im, 0)
        cv2.imshow('Camera', im)

    def zoom(self, im, zoom=1.0):
        h, w, _ = [ zoom * i for i in im.shape ]
        cx, cy = w/2, h/2
        im = cv2.resize(im, (0, 0), fx=zoom, fy=zoom)
        return im[ int(round(cy - h/zoom * .5)) : int(round(cy + h/zoom * .5)), int(round(cx - w/zoom * .5)) : int(round(cx + w/zoom * .5)), : ]

class PrintDevice:
    _instance = None

    def print(self, file_path, print_params={}):
        pass

    def get_print_status(self, task_id):
        pass

class Cv2Camera(CaptureDevice):
    def __init__(self, port=-1):
        if cv2:
            if port > -1:
                camera = cv2.VideoCapture(port)
                if camera.isOpened(): self._instance = camera
            else:
                for i in range(3):  # Test 3 first ports
                    camera = cv2.VideoCapture(i)
                    if camera.isOpened():
                        self._instance = camera
                        break
        if not self._instance: raise Exception('Cannot find any CV2 camera or CV2 is not installed.')

    def get_preview(self, square=False):
        ret, buf = self._instance.read()
        if not ret: return None
        im = cv2.flip(buf, 0)
        im = cv2.flip(im, 1)
        if square: im = self._crop_to_square(im)
        return im

    def capture(self, output_name, square=False, flash_fn=None):
        if flash_fn and not self.has_physical_flash(): flash_fn()
        ret, im_cv = self._instance.read()
        if flash_fn and not self.has_physical_flash(): lash_fn(stop=True)
        if not ret: return
        #im_cv = cv2.flip(im_cv, 0)
        if square: im_cv = self._crop_to_square(im_cv)

        # Dump to file
        cv2.imwrite(self._get_original_path(output_name), im)

        # Resize for display
        self._resize(output_name, im)

class Gphoto2Camera(CaptureDevice):
    def __init__(self):
        if gp:
            # List connected DSLR cameras
            if gp.cameraList().count():
                self._instance = gp.camera()

                _, self._preview = tempfile.mkstemp(suffix='.jpg')

                # Set default settings (For EOS 2000D: https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/cameras/canon-eos2000d.txt)
                config = self._instance.get_config()

                # Update some
                current_mode = config.get_path('/main/capturesettings/autoexposuremode').get_value()
                if current_mode in ['Manual', 'TV']:
                    config.get_path('/main/capturesettings/shutterspeed').set_value('1/125')
                if current_mode in ['Manual', 'AV']:
                    config.get_path('/main/capturesettings/aperture').set_value('13')
                config.get_path('/main/capturesettings/focusmode').set_value('One Shot')
                config.get_path('/main/imgsettings/iso').set_value('100')

                # Commit changes
                self._instance.commit_config(config)

        if not self._instance: raise Exception('Cannot find any gPhoto2 camera or gPhoto2 is not installed.')

    def has_physical_flash(self):
        return True

    def get_preview(self, square=False):
        self._instance.capture_preview(self._preview)
        im = cv2.imread(self._preview)
        im = cv2.rotate(im, cv2.ROTATE_180)
        if square: im = self._crop_to_square(im)
        return im

    def capture(self, output_name, square=False, flash_fn=None):
        # Capture photo
        if flash_fn and not self.has_physical_flash(): flash_fn()
        self._instance.capture_image(self._preview)
        if flash_fn and not self.has_physical_flash(): flash_fn(stop=True)

        # Rotate and crop if necessary
        im = cv2.imread(self._preview)
        im = cv2.rotate(im, cv2.ROTATE_180)
        if square: im = self._crop_to_square(im)

        # Dump to file
        cv2.imwrite(self._get_original_path(output_name), im)

        # Resize for display
        self._resize(output_name, im)

class Picamera2Camera(CaptureDevice):
    def __init__(self, port=0):
        if Picamera2:
            self._instance = Picamera2(camera_num=port)

            self._preview_config = self._instance.create_preview_configuration(main={'format': 'RGB888', 'size': (1920, 1080)}, controls={'FrameRate': 30})
            self._still_config = self._instance.create_still_configuration(main={"size": (1920, 1080), "format": "RGB888"}, buffer_count=2, controls={'FrameRate': 30})
            self._instance.configure(self._preview_config)
            self._instance.set_controls({'AfMode': controls.AfModeEnum.Continuous, 'AfSpeed': controls.AfSpeedEnum.Fast})
            self._instance.start()
        if not self._instance: raise Exception('Cannot find any Picamera2 or picamera2 is not installed.')

    def get_preview(self, square=False):
        im = self._instance.capture_array()
        #im = cv2.rotate(im, cv2.ROTATE_180)
        if square: im = self._crop_to_square(im)
        return im

    def capture(self, output_name, square=False, flash_fn=None):
        self._instance.switch_mode(self._still_config)
        if flash_fn and not self.has_physical_flash(): flash_fn()
        im = self._instance.capture_array()
        if flash_fn and not self.has_physical_flash(): flash_fn(stop=True)
        im = cv2.rotate(im, cv2.ROTATE_180)
        if square: im = self._crop_to_square(im)
        cv2.imwrite(self._get_original_path(output_name), im)
        self._instance.switch_mode(self._preview_config)

        # Resize for display
        self._resize(output_name, im)

class CupsPrinter(PrintDevice):
    _name = None

    def __init__(self, name=None):
        if cups:
            # Try to detect connected printer
            printer_found = False
            cups_conn = cups.Connection()
            if not name or name.lower() == 'default':
                printer_found = cups_conn.getDefault()
                if not printer_found and cups_conn.getPrinters(): printer_found = list(cups_conn.getPrinters().keys())[0]
            elif name in cups_conn.getPrinters():
                printer_found = name

            # Cannot find any printer
            if printer_found:
                self._name = name
                self._instance = cups_conn
                Logger.info('CupsPrinter: Connected to printer \'%s\'', name)
            elif name.lower() == 'default':
                Logger.warning('CupsPrinter: No printer configured in CUPS (see http://localhost:631)')
            else:
                Logger.warning('CupsPrinter: No printer named \'%s\' in CUPS (see http://localhost:631)', name)
        if not self._instance: raise Exception('Cannot find any CUPS printer or cups is not installed.')

    def print(self, file_path, print_params={}):
        return self._instance.printFile(self._name, file_path, ' ', print_params)

    def get_print_status(self, task_id):
        status = self._instance.getJobAttributes(task_id)['job-state']
        return 'pending' if status < 6 else 'done'

class DeviceUtils:
    _preview = None
    _capture = None
    _printer = None

    def __init__(self, printer_name=None, picamera2_port=0, cv2_port=-1):
        try:
            self._printer = CupsPrinter(printer_name)
        except:
            self._printer = None

        # Try to load cameras
        try:
            pi2_camera = Picamera2Camera(picamera2_port)
        except:
            pi2_camera = None
        try:
            g2_camera = Gphoto2Camera()
        except:
            g2_camera = None
        try:
            cv2_camera = Cv2Camera(cv2_port)
        except:
            cv2_camera = None

        # Switch to the best option
        if pi2_camera and g2_camera:
            Logger.info('Switch to hybrid camera (Picamera + gPhoto2)')
            self._preview = pi2_camera
            self._capture = g2_camera
        elif cv2_camera and g2_camera:
            Logger.info('Switch to hybrid camera (OpenCV + gPhoto2)')
            self._preview = cv2_camera
            self._capture = g2_camera
        elif pi2_camera:
            Logger.info('Switch to Picamera camera')
            self._preview = pi2_camera
            self._capture = pi2_camera
        elif cv2_camera:
            Logger.info('Switch to CV2 camera')
            self._preview = cv2_camera
            self._capture = cv2_camera
        elif g2_camera:
            Logger.info('Switch to gPhoto2 camera')
            self._preview = g2_camera
            self._capture = g2_camera
        else:
            Logger.info('Cannot find any camera nor DSLR')
            raise Exception('This app requires at lease a piCamera, a DSLR or a webcam to work.')

    def has_physical_flash(self):
        return self._capture.has_physical_flash()

    def get_preview(self, square=False):
        return self._preview.get_preview(square)

    def capture(self, output_name, square=False, flash_fn=None):
        return self._capture.capture(output_name, square, flash_fn)

    def has_printer(self):
        return self._printer is not None

    def print(self, file_path, print_params={}):
        if not self._printer: return
        self._printer.print(file_path, print_params)

    def get_print_status(self, task_id):
        if not self._printer: return 'done'
        return self._printer.get_print_status(task_id)
