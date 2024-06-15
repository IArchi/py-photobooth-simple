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
    import gphoto2cffi as gp
except ImportError:
    gp = None

class CaptureDevice:
    _instance = None

    def get_preview(self, square=False):
        pass

    def capture(self, output_name, square=False, flash_fn=None):
        pass

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

    def print(self, file_path, copies=1, print_format=None):
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
        if flash_fn: flash_fn()
        ret, im_cv = self._instance.read()
        if flash_fn: flash_fn(stop=True)
        if not ret: return
        #im_cv = cv2.flip(im_cv, 0)
        if square: im_cv = self._crop_to_square(im_cv)
        cv2.imwrite(output_name, im_cv)

class Gphoto2Camera(CaptureDevice):
    def __init__(self):
        if gp:
            # List connected DSLR cameras
            if len(gp.list_cameras()):
                camera = gp.Camera()
                camera.get_preview()
                try:
                    camera.config['capturesettings']['liveviewaffocus'].set('Full-time-servo AF')
                except:
                    Logger.warning('Could not change liveview AF settings, please enable AF on lens')
                self._instance = camera
        if not self._instance: raise Exception('Cannot find any gPhoto2 camera or gPhoto2 is not installed.')

    def get_preview(self, square=False):
        buf = self._instance.get_preview()
        buf = np.frombuffer(buf, np.uint8)
        im = cv2.imdecode(buf, cv2.IMREAD_ANYCOLOR)
        #im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        im = cv2.rotate(im, cv2.ROTATE_180)
        if square: im = self._crop_to_square(im)
        return im

    def capture(self, output_name, square=False, flash_fn=None):
        # Use gphoto2
        #cmd = 'gphoto2 --capture-image-and-download --filename {filename} --set-config manualfocusdrive=6 --keep --force-overwrite'.format(filename=output_name)
        #Logger.info('Command is %s', cmd)
        #return [subprocess.Popen(['gphoto2', '--auto-detect']), subprocess.Popen(shlex.split(cmd))]

        # Set settings
        try:
            self._instance.config['capturesettings']['imagequality'].set('JPEG Fine')
        except:
            Logger.warning('Failed to change image quality.')
        try:
            self._instance.config['actions']['viewfinder'].set(False)
        except:
            Logger.warning('Failed to disable liveview.')

        # Capture and copy file from SD card to local directory
        if flash_fn: flash_fn()
        capture_img = self._instance.capture(to_camera_storage=True)
        if flash_fn: flash_fn(stop=True)
        Logger.info('Camera file path: {}'.format(capture_img))

        if square:
            tmp_file, tmp_filename = tempfile.mkstemp()
            capture_img.save(tmp_filename)
            im_cv = cv2.imread(tmp_filename)
            os.remove(tmp_filename)
            im_cv = self._crop_to_square(im_cv)
            cv2.imwrite(output_name, im_cv)
        else:
            capture_img.save(output_name)

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
        if flash_fn: flash_fn()
        im = self._instance.capture_array()
        if flash_fn: flash_fn(stop=True)
        im = cv2.rotate(im, cv2.ROTATE_180)
        if square: im = self._crop_to_square(im)
        cv2.imwrite(output_name, im)
        self._instance.switch_mode(self._preview_config)

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
                Logger.info('Connected to printer \'%s\'', name)
            elif name.lower() == 'default':
                Logger.warning('No printer configured in CUPS (see http://localhost:631)')
            else:
                Logger.warning('No printer named \'%s\' in CUPS (see http://localhost:631)', name)
        if not self._instance: raise Exception('Cannot find any CUPS printer or cups is not installed.')

    def print(self, file_path, copies=1, print_format=None):
        options = {'orientation-requested':'6', 'copies':str(copies)}
        if print_format: options['media'] = print_format
        return self._instance.printFile(self._name, file_path, ' ', options)

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

    def get_preview(self, square=False):
        return self._preview.get_preview(square)

    def capture(self, output_name, square=False, flash_fn=None):
        return self._capture.capture(output_name, square, flash_fn)

    def has_printer(self):
        return self._printer is not None

    def print(self, file_path, copies=1, print_format=None):
        if not self._printer: return
        self._printer.print(file_path, copies, print_format)

    def get_print_status(self, task_id):
        self._printer.get_print_status(task_id)
