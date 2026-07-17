import os
import subprocess
import threading
import time
import traceback
import numpy as np
from kivy.logger import Logger

from libs.file_utils import FileUtils

try:
    import cups
except ImportError:
    cups = None

try:
    from picamera2 import Picamera2
    from libcamera import controls, Transform
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

    def get_preview_fps(self):
        """Recommended FPS for preview refresh (30 by default)."""
        return 30

    def get_preview(self, aspect_ratio=None):
        pass

    def capture(self, output_name, aspect_ratio=None, flash_fn=None):
        pass

    def has_physical_flash(self):
        return False

    def close(self):
        pass

    def _crop_to_aspect_ratio(self, image, aspect_ratio):
        """
        Crop image to match the target aspect ratio (width/height).
        
        Args:
            image: Input image
            aspect_ratio: Target aspect ratio (width/height). 
                         1.0 for square, >1.0 for landscape, <1.0 for portrait
        
        Returns:
            Cropped image
        """
        if aspect_ratio is None:
            return image
            
        height, width, _ = image.shape
        current_ratio = width / height
        
        if abs(current_ratio - aspect_ratio) < 0.01:
            # Already at target ratio
            return image
        
        if current_ratio > aspect_ratio:
            # Current image is wider, crop width
            new_width = int(height * aspect_ratio)
            left = (width - new_width) // 2
            return image[:, left:left + new_width]
        else:
            # Current image is taller, crop height
            new_height = int(width / aspect_ratio)
            top = (height - new_height) // 2
            return image[top:top + new_height, :]

    def cv2_imshow(self, im, size=None):
        if size: im = im.reshape((size[1], size[0], 3))
        im = cv2.flip(im, 0)
        cv2.imshow('Camera', im)

class PrintDevice:
    _instance = None

    def print(self, file_path, print_params={}):
        pass

    def get_print_status(self, task_id):
        pass

class Cv2Camera(CaptureDevice):
    def __init__(self, port=-1):
        self._preview_lock = threading.Lock()
        self._camera_lock = threading.Lock()
        self._preview_frame = None
        self._preview_thread = None
        self._preview_stop = False
        self._preview_fps = 30
        if cv2:
            if port > -1:
                camera = cv2.VideoCapture(port)
                if camera.isOpened():
                    camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                    self._instance = camera
            else:
                for i in range(3):  # Test 3 first ports
                    camera = cv2.VideoCapture(i)
                    if camera.isOpened():
                        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
                        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
                        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
                        self._instance = camera
                        break
                    camera.release()
        if not self._instance: raise Exception('Cannot find any CV2 camera or CV2 is not installed.')

    def _preview_loop(self):
        """Read webcam frames continuously so Kivy never waits on camera I/O."""
        while not self._preview_stop:
            try:
                with self._camera_lock:
                    ret, buf = self._instance.read()
                if ret:
                    im = cv2.flip(buf, 0)
                    im = cv2.flip(im, 1)
                    with self._preview_lock:
                        self._preview_frame = im
                time.sleep(1.0 / self._preview_fps)
            except Exception as e:
                Logger.debug('Cv2Camera preview thread: %s', e)

    def _start_preview_thread(self):
        if self._preview_thread is not None and self._preview_thread.is_alive():
            return
        self._preview_stop = False
        self._preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
        self._preview_thread.start()

    def get_preview(self, aspect_ratio=None, zoom=None):
        self._start_preview_thread()
        with self._preview_lock:
            im = self._preview_frame.copy() if self._preview_frame is not None else None
        if im is None: return None
        im = self._crop_to_aspect_ratio(im, aspect_ratio)
        if zoom and zoom[0] > 1.0: im = FileUtils.zoom(im, zoom)
        return im

    def capture(self, output_name, aspect_ratio=None, zoom=None, flash_fn=None):
        if flash_fn and not self.has_physical_flash(): flash_fn()
        with self._camera_lock: ret, im = self._instance.read()
        if flash_fn and not self.has_physical_flash(): flash_fn(stop=True)
        if not ret:
            raise IOError('OpenCV camera capture failed')
        #im = cv2.flip(im, 0)
        im = self._crop_to_aspect_ratio(im, aspect_ratio)
        if zoom and zoom[0] < 1.0: im = FileUtils.zoom(im, zoom)

        # Dump to file
        FileUtils.write_image(output_name, im)

        # Create small preview in background thread (non-blocking)
        threading.Thread(target=self._create_small_async, args=(im.copy(), output_name), daemon=True).start()
    
    def _create_small_async(self, image, output_name):
        """Create small preview image asynchronously to avoid blocking capture."""
        try:
            resized_im = FileUtils.resize(image)
            FileUtils.write_image(FileUtils.get_small_path(output_name), resized_im)
        except Exception as e:
            Logger.error(f'Error creating small preview: {e}')

    def close(self):
        self._preview_stop = True
        if self._preview_thread is not None and self._preview_thread.is_alive():
            self._preview_thread.join(timeout=1)
        if self._instance is not None:
            self._instance.release()
            self._instance = None

class Gphoto2Camera(CaptureDevice):
    def __init__(self, dslr_liveview_params=None, dslr_capture_params=None):
        if gp:
            # List connected DSLR cameras
            if gp.cameraList().count():
                self._instance = gp.camera()

                self.dslr_liveview_params = dslr_liveview_params or {}
                self.dslr_capture_params = dslr_capture_params or {}
                self._preview_lock = threading.Lock()
                self._camera_lock = threading.Lock()
                self._preview_frame = None
                self._preview_frame_back = None
                self._preview_thread = None
                self._preview_stop = False
                self._preview_fps = 15  # DSLR preview limited by USB throughput
                # Reduced JPEG decode (1/2 resolution) for smoother preview (OpenCV 4+)
                self._imread_preview = getattr(cv2, 'IMREAD_REDUCED_COLOR_2', cv2.IMREAD_COLOR)

                try:
                    self._set_parameters(self.dslr_liveview_params)
                except Exception:
                    Logger.info('Could not set default DSLR settings, maybe unsupported camera model.')

        if not self._instance: raise Exception('Cannot find any gPhoto2 camera or gPhoto2 is not installed.')

    def _get_param(self, params, key):
        """Returns the value if defined and non-empty, otherwise None."""
        v = params.get(key) or params.get(key.upper())
        if v is None or (isinstance(v, str) and v.strip() == ''): return None
        return v

    def _set_parameters(self, params):
        """
        Applies DSLR parameters (config.ini key -> value dict) according to manufacturer.
        If a parameter is missing or None, it is not changed.
        """
        if not params: return

        config = self._instance.get_config()
        manufacturer = config.get_path('/main/status/manufacturer').get_value()

        if manufacturer == 'Canon Inc.':
            # From https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/cameras/canon-eos2000d.txt
            current_mode = config.get_path('/main/capturesettings/autoexposuremode').get_value()
            if (v := self._get_param(params, 'SHUTTERSPEED')) and current_mode in ['Manual', 'TV']:
                config.get_path('/main/capturesettings/shutterspeed').set_value(v)
            if (v := self._get_param(params, 'APERTURE')) and current_mode in ['Manual', 'AV']:
                config.get_path('/main/capturesettings/aperture').set_value(v)
            if v := self._get_param(params, 'FOCUSMODE'):
                config.get_path('/main/capturesettings/focusmode').set_value(v)
            if v := self._get_param(params, 'ISO'):
                config.get_path('/main/imgsettings/iso').set_value(v)

        elif manufacturer == 'Nikon Corporation':
            # From https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/cameras/nikon-z6.txt
            current_mode = config.get_path('/main/capturesettings/expprogram').get_value()
            if (v := self._get_param(params, 'SHUTTERSPEED')) and current_mode in ['M', 'S']:
                config.get_path('/main/capturesettings/shutterspeed').set_value(v)
            if (v := self._get_param(params, 'APERTURE')) and current_mode in ['M', 'A']:
                config.get_path('/main/capturesettings/f-number').set_value(v)
            if v := self._get_param(params, 'FOCUSMODE'):
                config.get_path('/main/capturesettings/focusmode').set_value(v)
            if v := self._get_param(params, 'ISO'):
                config.get_path('/main/imgsettings/iso').set_value(v)

        elif manufacturer == 'Sony Corporation':
            # From https://github.com/gphoto/libgphoto2/blob/master/camlibs/ptp2/cameras/sony-a7c.txt
            current_mode = config.get_path('/main/capturesettings/expprogram').get_value()
            if (v := self._get_param(params, 'SHUTTERSPEED')) and current_mode in ['M', 'S']:
                config.get_path('/main/capturesettings/shutterspeed').set_value(v)
            if (v := self._get_param(params, 'APERTURE')) and current_mode in ['M', 'A']:
                config.get_path('/main/capturesettings/f-number').set_value('f/{v}')
            if v := self._get_param(params, 'FOCUSMODE'):
                config.get_path('/main/capturesettings/focusmode').set_value(v)
            if v := self._get_param(params, 'ISO'):
                config.get_path('/main/imgsettings/iso').set_value(v)

        else:
            Logger.info('Unsupported camera model: %s', manufacturer)

        self._instance.commit_config(config)

    def _preview_loop(self):
        """Dedicated thread: continuous capture + decode so as not to block the UI."""
        while not self._preview_stop:
            try:
                with self._camera_lock:
                    cfile = self._instance.capture_preview()
                buf = np.frombuffer(cfile.get_data(auto_clean=False), dtype=np.uint8)
                im = cv2.imdecode(buf, self._imread_preview)
                if im is not None:
                    im = cv2.rotate(im, cv2.ROTATE_180)
                    with self._preview_lock:
                        self._preview_frame, self._preview_frame_back = im, self._preview_frame
                time.sleep(1.0 / self._preview_fps)
            except Exception as e:
                Logger.debug('Gphoto2Camera preview thread: %s', e)

    def _start_preview_thread(self):
        if self._preview_thread is not None and self._preview_thread.is_alive():
            return
        self._preview_stop = False
        self._preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
        self._preview_thread.start()

    def has_physical_flash(self):
        return True

    def get_preview_fps(self):
        """Recommended FPS for preview (DSLR limited by USB throughput)."""
        return self._preview_fps

    def get_preview(self, aspect_ratio=None, zoom=None):
        self._start_preview_thread()
        with self._preview_lock:
            im = (self._preview_frame.copy() if self._preview_frame is not None else None)
        if im is None:
            return None
        im = self._crop_to_aspect_ratio(im, aspect_ratio)
        if zoom and zoom[0] > 1.0:
            im = FileUtils.zoom(im, zoom)
        return im

    def capture(self, output_name, aspect_ratio=None, zoom=None, flash_fn=None):
        with self._camera_lock:
            # Apply capture parameters (config.ini [DSLR_Capture]) right before capture
            try:
                self._set_parameters(self.dslr_capture_params or {})
            except Exception as e:
                Logger.debug('Gphoto2Camera: could not apply capture params: %s', e)

            # Capture photo
            if flash_fn and not self.has_physical_flash(): flash_fn()
            cfile = self._instance.capture_image()
            if flash_fn and not self.has_physical_flash(): flash_fn(stop=True)

            # Set DSLR back to liveview before the preview thread can resume.
            try:
                self._set_parameters(self.dslr_liveview_params)
            except Exception as e:
                Logger.debug('Gphoto2Camera: could not apply liveview params: %s', e)

        # Rotate and crop if necessary
        buf = np.frombuffer(cfile.get_data(), dtype=np.uint8)
        im = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if im is None:
            raise IOError('gPhoto2 returned an unreadable image buffer')
        #im = cv2.rotate(im, cv2.ROTATE_180)
        im = self._crop_to_aspect_ratio(im, aspect_ratio)
        if zoom and zoom[0] < 1.0: im = FileUtils.zoom(im, zoom)

        # Dump to file
        FileUtils.write_image(output_name, im)

        # Create small preview in background thread (non-blocking)
        threading.Thread(target=self._create_small_async, args=(im.copy(), output_name), daemon=True).start()


    def _create_small_async(self, image, output_name):
        """Create small preview image asynchronously to avoid blocking capture."""
        try:
            resized_im = FileUtils.resize(image)
            FileUtils.write_image(FileUtils.get_small_path(output_name), resized_im)
        except Exception as e:
            Logger.error(f'Error creating small preview: {e}')

    def close(self):
        self._preview_stop = True
        if self._preview_thread is not None and self._preview_thread.is_alive():
            self._preview_thread.join(timeout=1)
        if self._instance is not None:
            try:
                self._instance.close()
            except Exception as e:
                Logger.warning('Gphoto2Camera: could not close camera cleanly: %s', e)
            self._instance = None

class Picamera2Camera(CaptureDevice):
    def __init__(self, port=0):
        self._preview_lock = threading.Lock()
        self._camera_lock = threading.Lock()
        self._preview_frame = None
        self._preview_thread = None
        self._preview_stop = False
        self._preview_fps = 60
        self._capturing = False
        if Picamera2:
            try:
                self._instance = Picamera2(camera_num=port)
                self._preview_config = self._instance.create_preview_configuration(
                    main={'format': 'RGB888', 'size': (1280, 720)},
                    transform=Transform(hflip=1, vflip=1),
                    controls={'FrameRate': 60},
                )
                self._still_config = self._instance.create_still_configuration(main={"size": (2304, 1296), "format": "RGB888"}, buffer_count=2, controls={'FrameRate': 30})
                self._instance.configure(self._preview_config)
                self._instance.set_controls({'AfMode': controls.AfModeEnum.Continuous, 'AfSpeed': controls.AfSpeedEnum.Fast})
                self._instance.start()
            except Exception as e:
                Logger.error('Picamera2Camera: initialization failed: %s', e)
                Logger.error(traceback.format_exc())
                self.close()
        if not self._instance: raise Exception('Cannot find any Picamera2 or picamera2 is not installed.')

    def _preview_loop(self):
        """Read PiCamera frames continuously so Kivy never waits on camera I/O."""
        while not self._preview_stop:
            try:
                if self._capturing:
                    time.sleep(1.0 / self._preview_fps)
                    continue
                with self._camera_lock:
                    im = self._instance.capture_array()
                with self._preview_lock:
                    self._preview_frame = im
                time.sleep(1.0 / self._preview_fps)
            except Exception as e:
                Logger.debug('Picamera2Camera preview thread: %s', e)

    def _start_preview_thread(self):
        if self._preview_thread is not None and self._preview_thread.is_alive():
            return
        self._preview_stop = False
        self._preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
        self._preview_thread.start()

    def get_preview_fps(self):
        return self._preview_fps

    def get_preview(self, aspect_ratio=None, zoom=None):
        self._start_preview_thread()
        with self._preview_lock:
            im = self._preview_frame
        if im is None: return None
        im = self._crop_to_aspect_ratio(im, aspect_ratio)
        if zoom and zoom[0] > 1.0: im = FileUtils.zoom(im, zoom)
        return im

    def capture(self, output_name, aspect_ratio=None, zoom=None, flash_fn=None):
        self._capturing = True
        try:
            with self._camera_lock:
                self._instance.switch_mode(self._still_config)
                if flash_fn and not self.has_physical_flash(): flash_fn()
                im = self._instance.capture_array()
                if flash_fn and not self.has_physical_flash(): flash_fn(stop=True)
                #im = cv2.rotate(im, cv2.ROTATE_180)
                im = self._crop_to_aspect_ratio(im, aspect_ratio)
                self._instance.switch_mode(self._preview_config)
        finally:
            self._capturing = False
        if zoom and zoom[0] < 1.0: im = FileUtils.zoom(im, zoom)

        # Dump to file
        FileUtils.write_image(output_name, im)

        # Create small preview in background thread (non-blocking)
        threading.Thread(target=self._create_small_async, args=(im.copy(), output_name), daemon=True).start()
    
    def _create_small_async(self, image, output_name):
        """Create small preview image asynchronously to avoid blocking capture."""
        try:
            resized_im = FileUtils.resize(image)
            FileUtils.write_image(FileUtils.get_small_path(output_name), resized_im)
        except Exception as e:
            Logger.error(f'Error creating small preview: {e}')

    def close(self):
        self._preview_stop = True
        if self._preview_thread is not None and self._preview_thread.is_alive():
            self._preview_thread.join(timeout=1)
        if self._instance is not None:
            try:
                self._instance.stop()
            except Exception:
                pass
            try:
                self._instance.close()
            except Exception:
                pass
            self._instance = None

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
                self._name = printer_found
                self._instance = cups_conn
                Logger.info('CupsPrinter: Connected to printer \'%s\'', printer_found)
            elif not name or name.lower() == 'default':
                Logger.warning('CupsPrinter: No printer configured in CUPS (see http://localhost:631)')
            else:
                Logger.warning('CupsPrinter: No printer named \'%s\' in CUPS (see http://localhost:631)', name)
        if not self._instance: raise Exception('Cannot find any CUPS printer or cups is not installed.')

    def print(self, file_path, print_params={}):
        if not self.is_available():
            raise RuntimeError(f"Printer '{self._name}' is not available")
        return self._instance.printFile(self._name, os.path.abspath(file_path), os.path.basename(file_path), print_params)

    def get_print_status(self, task_id):
        status = self._instance.getJobAttributes(task_id)['job-state']
        return 'pending' if status < 6 else 'done'

    def is_available(self):
        if self._instance is None or not self._name:
            return False

        try:
            printers = self._instance.getPrinters()
            printer = printers.get(self._name)
            if not printer:
                return False

            if printer.get('printer-is-accepting-jobs') is False:
                return False

            # CUPS states: 3=idle, 4=printing, 5=stopped
            return printer.get('printer-state') != 5
        except Exception as e:
            Logger.warning('CupsPrinter: availability check failed for %s: %s', self._name, e)
            return False

class DeviceUtils:
    _preview = None
    _capture = None
    _printer = None

    def __init__(self, printer_name=None, picamera2_port=0, cv2_port=-1, zoom=None,
                 dslr_liveview_params=None, dslr_capture_params=None):
        self._zoom = zoom

        try:
            self._printer = CupsPrinter(printer_name)
        except Exception as e:
            Logger.warning('DeviceUtils: printer initialization failed: %s', e)
            self._printer = None

        # Try to load cameras
        try:
            pi2_camera = Picamera2Camera(picamera2_port)
        except Exception as e:
            Logger.warning('DeviceUtils: Picamera2 unavailable: %s', e)
            pi2_camera = None
        try:
            g2_camera = Gphoto2Camera(dslr_liveview_params=dslr_liveview_params,
                                      dslr_capture_params=dslr_capture_params)
        except Exception as e:
            Logger.warning('DeviceUtils: gPhoto2 unavailable: %s', e)
            g2_camera = None
        try:
            cv2_camera = Cv2Camera(cv2_port)
        except Exception as e:
            Logger.warning('DeviceUtils: OpenCV camera unavailable: %s', e)
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
        elif g2_camera:
            Logger.info('Switch to gPhoto2 camera')
            self._preview = g2_camera
            self._capture = g2_camera
        elif cv2_camera:
            Logger.info('Switch to CV2 camera')
            self._preview = cv2_camera
            self._capture = cv2_camera
        else:
            Logger.info('Cannot find any camera nor DSLR')
            raise Exception('This app requires at least a piCamera, a DSLR or a webcam to work.')

    def has_physical_flash(self):
        return self._capture.has_physical_flash()

    def get_preview_fps(self):
        return self._preview.get_preview_fps()

    def get_preview(self, aspect_ratio=None):
        return self._preview.get_preview(aspect_ratio=aspect_ratio, zoom=self._zoom)

    def capture(self, output_name, aspect_ratio=None, flash_fn=None):
        return self._capture.capture(output_name, aspect_ratio, self._zoom, flash_fn)

    def has_printer(self):
        if self._printer is None:
            return False
        return self._printer.is_available()

    def print(self, file_path, print_params={}):
        if not self._printer: return
        self._printer.print(file_path, print_params)

    def get_print_status(self, task_id):
        if not self._printer: return 'done'
        return self._printer.get_print_status(task_id)

    def close(self):
        for device in (self._preview, self._capture):
            if device is None:
                continue
            try:
                device.close()
            except Exception as e:
                Logger.warning('DeviceUtils: could not close device cleanly: %s', e)
