import io
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
    from picamera2.encoders import MJPEGEncoder
    from picamera2.outputs import FileOutput
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

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            nparr = np.frombuffer(buf, np.uint8)
            self.frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            self.condition.notify_all()

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

        picam2 = Picamera2(camera_num=port)
        video_config = picam2.create_video_configuration(main={"size": (1920, 1080)})
        picam2.configure(video_config)
        
        return picam2

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
            output = StreamingOutput()
            self._rpi_cam_proxy.start_recording(MJPEGEncoder(), FileOutput(output))
            self._rpi_cam_proxy.streaming_output = output

    def stop_preview(self):
        if self._rpi_cam_proxy:
            self._rpi_cam_proxy.stop_recording()
            self._rpi_cam_proxy.streaming_output = None
        elif self._gp_cam_proxy:
            self._gp_cam_proxy.exit()

    def get_preview(self, square=False):
        if self._rpi_cam_proxy:
            with self._rpi_cam_proxy.streaming_output.condition:
                self._rpi_cam_proxy.streaming_output.condition.wait()
                im = self._rpi_cam_proxy.streaming_output.frame
                if square: im = self._crop_to_square(im)
                return im.shape, im.tostring()
        elif self._cv_cam_proxy:
            ret, buf = self._cv_cam_proxy.read()
            if not ret: return None, None
            im = cv2.flip(buf, 0)
            im = cv2.flip(im, 1)
            if square: im = self._crop_to_square(im)
            return im.shape, im.tostring()
        elif self._gp_cam_proxy:
            buf = self._gp_cam_proxy.get_preview()
            buf = np.frombuffer(buf, np.uint8)
            im = cv2.imdecode(buf, cv2.IMREAD_ANYCOLOR)
            im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
            if square: im = self._crop_to_square(im)
            return im.shape, im.tostring()
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
            request = self._rpi_cam_proxy.capture_request()
            buf = request.make_array('main')
            request.release()
            im_cv = cv2.cvtColor(buf, cv2.COLOR_RGBA2BGR)
            if square: im_cv = self._crop_to_square(im_cv)
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
