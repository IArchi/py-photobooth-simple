import io
import os
import shlex
import tempfile
import subprocess
import numpy as np
from PIL import Image
from kivy.logger import Logger

try:
    import cups
except ImportError:
    cups = None

try:
    from picamera2 import Picamera2
    from libcamera import Transform, controls
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

class DeviceUtils:

    def __init__(self, printer_name=None, picamera2_port=None, gphoto2_port=None, cv2_port=None):
        # Try to load cameras
        self._printer_proxy, self._printer_name = self.get_printer_proxy(printer_name)
        self._rpi_cam_proxy = self.get_picamera2_proxy(picamera2_port)
        self._gp_cam_proxy = self.get_gphoto2_proxy(gphoto2_port)
        self._cv_cam_proxy = self.get_cv2_proxy(cv2_port)

        # Switch to the best option
        if self._rpi_cam_proxy and self._gp_cam_proxy:
            Logger.info('Switch to hybrid camera (Picamera + gPhoto2)')
        elif self._cv_cam_proxy and self._gp_cam_proxy:
            Logger.info('Switch to hybrid camera (OpenCV + gPhoto2)')
        elif self._rpi_cam_proxy:
            Logger.info('Switch to Picamera camera')
        elif self._cv_cam_proxy:
            Logger.info('Switch to CV2 camera')
        elif self._gp_cam_proxy:
            Logger.info('Switch to gPhoto2 camera')
        else:
            Logger.info('Cannot find any camera nor DSLR')
            raise Exception('This app requires at lease a piCamera, a DSLR or a webcam to work.')

    def get_printer_proxy(self, name=None):
        """
        Return printer proxy if a CUPS compatible printer is found
        else return None.
        :param port: look on given port number
        :type port: str
        """
        if not cups:
            Logger.warning('No printer found (pycups or pycups-notify not installed)')
            return  None, None

        # Try to detect connected printer
        printer_found = False
        cups_conn = cups.Connection()
        if not name or name.lower() == 'default':
            printer_found = cups_conn.getDefault()
            if not printer_found and cups_conn.getPrinters(): printer_found = list(cups_conn.getPrinters().keys())[0]
        elif name in cups_conn.getPrinters():
            printer_found = name

        # Cannot find any printer
        if not printer_found:
            if name.lower() == 'default':
                Logger.warning('No printer configured in CUPS (see http://localhost:631)')
            else:
                Logger.warning('No printer named \'%s\' in CUPS (see http://localhost:631)', name)
            return None, None

        Logger.info('Connected to printer \'%s\'', name)
        return cups_conn, name

    def get_picamera2_proxy(self, port=None):
        """
        Return camera proxy if a Raspberry Pi compatible camera is found
        else return None.
        :param port: look on given port number
        :type port: str
        """
        if not Picamera2: return None  # picamera is not installed
        try:
            process = subprocess.Popen(['vcgencmd', 'get_camera'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, _stderr = process.communicate()
            if stdout and u'detected=1' in stdout.decode('utf-8'):
                if port is not None: cam = Picamera2(camera_num=port)
                else: cam = Picamera2()

                # Enable auto exposure
                try:
                    cam.set_controls({'AeExposureMode': 1}) # Usually 0=normal exposure, 1=short, 2=long
                except RuntimeError as exc:
                    Logger.error(f"set_ae_exposure failed! {exc}")

                # Enable auto focus
                try:
                    cam.set_controls({'AfMode': controls.AfModeEnum.Continuous})
                except RuntimeError as exc:
                    Logger.critical(f"control not available on camera - autofocus not working properly {exc}")
                try:
                    cam.set_controls({'AfSpeed': controls.AfSpeedEnum.Fast})
                except RuntimeError as exc:
                    Logger.info(f"control not available on all cameras - can ignore {exc}")

                return cam
        except OSError:
            pass
        return None

    def get_cv2_proxy(self, port=None):
        """
        Return camera proxy if an OpenCV compatible camera is found
        else return None.
        :param port: look on given port number
        :type port: str
        """
        if not cv2: return None  # OpenCV is not installed

        if port is not None:
            if not isinstance(port, int): raise TypeError("Invalid OpenCV camera port '{}'".format(type(port)))
            camera = cv2.VideoCapture(port)
            if camera.isOpened(): return camera
        else:
            for i in range(3):  # Test 3 first ports
                camera = cv2.VideoCapture(i)
                if camera.isOpened(): return camera

        return None

    def get_gphoto2_proxy(self, port=None):
        """
        Return camera proxy if a gPhoto2 compatible camera is found
        else return None.
        :param port: look on given port number
        :type port: str
        """
        if not gp: return None  # gphoto2cffi is not installed

        # List connected DSLR cameras
        if len(gp.list_cameras()):
            Logger.debug('Found at least one gPhoto2 camera')
            camera = gp.Camera()

            # Must run preview once before changing settings
            camera.get_preview()

            # Set settings
            try:
                camera.config['capturesettings']['liveviewaffocus'].set('Full-time-servo AF')
            except:
                Logger.warning('Could not change liveview AF settings, please enable AF on lens')

            return camera

        return None

    def start_preview(self, fps=30):
        if self._rpi_cam_proxy:
            self._rpi_cam_proxy.configure(self._rpi_cam_proxy.create_preview_configuration(main={'size': (1280, 960)}, controls={'FrameRate': fps}))
            self._rpi_cam_proxy.start()

    def stop_preview(self):
        if self._rpi_cam_proxy:
            self._rpi_cam_proxy.stop()
        elif self._gp_cam_proxy:
            self._gp_cam_proxy.exit()

    def get_preview(self, square=False):
        if self._rpi_cam_proxy:
            im = self._rpi_cam_proxy.capture_array()
            nparr = np.frombuffer(im, np.uint8)
            img_np = cv2.imdecode(nparr, cv2.IMREAD_ANYCOLOR)
            img_np = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
            if square: img_np = self._crop_to_square(img_np)
            return (img_np.shape[1], img_np.shape[0]), img_np.tostring()
            #return (1280, 960), im.tostring()
        elif self._cv_cam_proxy:
            ret, im = self._cv_cam_proxy.read()
            if not ret: return None, None
            im = cv2.flip(im, 0)
            im = cv2.flip(im, 1)
            if square: im = self._crop_to_square(im)
            return (im.shape[1], im.shape[0]), im.tostring()
        elif self._gp_cam_proxy:
            im = self._gp_cam_proxy.get_preview()
            nparr = np.frombuffer(im, np.uint8)
            img_np = cv2.imdecode(nparr, cv2.IMREAD_ANYCOLOR)
            img_np = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
            if square: img_np = self._crop_to_square(img_np)
            return (img_np.shape[1], img_np.shape[0]), img_np.tostring()
        return None, None

    def capture(self, output_name, square=False):
        Logger.info('DeviceUtils: capture({}, {}).'.format(output_name, square))
        tmp_file, tmp_filename = tempfile.mkstemp()
        if self._gp_cam_proxy:
            # Use gphoto2
            #cmd = 'gphoto2 --capture-image-and-download --filename {filename} --set-config manualfocusdrive=6 --keep --force-overwrite'.format(filename=output_name)
            #Logger.info('Command is %s', cmd)
            #return [subprocess.Popen(['gphoto2', '--auto-detect']), subprocess.Popen(shlex.split(cmd))]

            # Set settings
            try:
                self._gp_cam_proxy.config['capturesettings']['imagequality'].set('JPEG Fine')
            except:
                Logger.warning('Failed to change image quality.')
            try:
                self._gp_cam_proxy.config['actions']['viewfinder'].set(False)
            except:
                Logger.warning('Failed to disable liveview.')

            # Capture and copy file from SD card to local directory
            file_path = self._gp_cam_proxy.capture(to_camera_storage=True)
            Logger.info('Camera file path: {0}/{1}'.format(file_path.folder, file_path.name))
            camera_file = self._gp_cam_proxy.file_get(file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)

            if square:
                camera_file.save(tmp_filename)
                im_cv = cv2.imread(tmp_filename)
                im_cv = self._crop_to_square(im_cv)
                cv2.imwrite(output_name, im_cv)
            else:
                camera_file.save(output_name)

        # Fallback using the PiCamera
        elif self._rpi_cam_proxy:
            self._rpi_cam_proxy.start()
            self._rpi_cam_proxy.switch_mode_and_capture_file(self._rpi_cam_proxy.create_still_configuration(main={'size': (1280, 720)},lores={'size': (1280, 720)},encode='lores',buffer_count=3,display='lores',transform=Transform(hflip=True, vflip=False)), tmp_filename if square else output_name)
            self._rpi_cam_proxy.stop()

            if square:
                im_cv = cv2.imread(tmp_filename)
                im_cv = self._crop_to_square(im_cv)
                cv2.imwrite(output_name, im_cv)

        # Fallback using the Cv2 webcam
        elif self._cv_cam_proxy:
            ret, im_cv = self._cv_cam_proxy.read()
            if ret:
                #im_cv = cv2.flip(im_cv, 0)
                if square: im_cv = self._crop_to_square(im_cv)
                cv2.imwrite(output_name, im_cv)

        os.remove(tmp_filename)

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

    def has_printer(self):
        return self._printer_proxy is not None

    def print(self, file_path, copies=1, print_format=None):
        if not self._printer_proxy: return
        options = {'orientation-requested':'6', 'copies':str(copies)}
        if print_format: options['media'] = print_format
        return self._printer_proxy.printFile(self._printer_name, file_path, ' ', options)

    def get_print_status(self, task_id):
        if not self._printer_proxy: return None
        status = self._printer_proxy.getJobAttributes(task_id)['job-state']
        return 'pending' if status < 6 else 'done'
