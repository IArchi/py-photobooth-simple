#!/usr/bin/python3

import os
import shutil
import sys
import signal
import threading
import time
import traceback
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIRECTORY = PROJECT_ROOT / 'logs'
LOG_DIRECTORY.mkdir(exist_ok=True)

from kivy.config import Config as KivyConfig
KivyConfig.set('kivy', 'log_enable', '1')
KivyConfig.set('kivy', 'log_dir', str(LOG_DIRECTORY))
KivyConfig.set('kivy', 'log_name', 'photobooth_%y-%m-%d_%_.txt')
KivyConfig.set('kivy', 'exit_on_escape', '0')

# os.environ['KIVY_NO_CONSOLELOG'] = '1'
from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.screenmanager import FadeTransition

from libs.config import Config
from libs.device_utils import DeviceUtils
from libs.file_utils import FileUtils
from libs.screens import ScreenMgr
from libs.ringled import RingLed
from libs.template_collage import load_templates
from libs.usb_transfer import UsbTransfer
from libs.web_server import WebServer

RINGLED = None

def signal_handler(sig, frame):
    print("\nCtrl+C detected. Exiting gracefully...")
    if RINGLED:
        RINGLED.clear()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

class PhotoboothApp(App):
    def __init__(self, **kwargs):
        global RINGLED
        Logger.info('PhotoboothApp: __init__().')
        super(PhotoboothApp, self).__init__(**kwargs)

        # Load configuration
        config = Config()
        self.FULLSCREEN = config.get_fullscreen()
        self.SHARE = config.get_share()
        self.WEB_PORT = config.get_web_port()
        self.FILTERS = config.get_filters()
        self.PREVIEW_BLUR_REFRESH_FRAMES = config.get_preview_blur_refresh_frames()
        self.BLUR_CAMERA = config.get_blur_camera()
        self.BLUR_IMAGES = config.get_blur_images()
        self.BLUR_COLLAGE = config.get_blur_collage()
        self.COUNTDOWN = config.get_countdown()
        self.DCIM_DIRECTORY = config.get_dcim_directory()
        self.DISK_MIN_FREE_GB = config.get_disk_min_free_gb()
        self.DISK_MAX_USED_PERCENT = config.get_disk_max_used_percent()
        self.PRINTER_WAIT_TIMEOUT = config.get_printer_wait_timeout()
        self.USB_EXPORT = config.get_usb_export_enabled()
        self.USB_MIN_FREE_GB = config.get_usb_min_free_gb()
        self.PRINTER = config.get_printer()
        self.CALIBRATION = config.get_calibration()
        self._dslr_liveview_params = config.get_dslr_liveview_params()
        self._dslr_capture_params = config.get_dslr_capture_params()
        self._log_retention_days = config.get_log_retention_days()
        self._log_max_files = config.get_log_max_files()

        self._rotate_logs()
        
        # Initialize RingLed if enabled in config
        if config.get_ringled():
            RINGLED = RingLed(num_pixels=12)
            Logger.info('PhotoboothApp: RingLed enabled')
        else:
            Logger.info('PhotoboothApp: RingLed disabled')

        # Assign local variables
        self.sm = None
        self._requested_screen = None
        self._requested_kwargs = None
        self.pending_photo_tasks = []
        self._pending_photo_error = None
        self._pending_photo_lock = threading.Lock()
        self.last_saved_session_directory = None
        self.processes = []
        self._process_lock = threading.Lock()
        self._process_state = {
            'kind': None,
            'token': 0,
            'error': None,
            'traceback': None,
            'started_at': None,
            'finished_at': None,
        }
        self._process_token = 0
        self.usb_transfer = None
        self.ringled = RINGLED
        self.devices = DeviceUtils(
            printer_name=self.PRINTER,
            zoom=self.CALIBRATION,
            dslr_liveview_params=self._dslr_liveview_params,
            dslr_capture_params=self._dslr_capture_params,
        )
        
        # Load templates from JSON files
        self.print_formats = load_templates('templates')
        
        # Check if templates were loaded
        if len(self.print_formats) == 0:
            Logger.error('No templates found in templates/ directory!')
            raise Exception('No templates found. Please ensure template JSON files exist in the templates/ directory.')

        # Create required directories
        self.tmp_directory = os.path.join(self.DCIM_DIRECTORY, 'tmp')
        self.save_directory = os.path.join(self.DCIM_DIRECTORY, 'save')
        if not os.path.exists(self.DCIM_DIRECTORY): os.makedirs(self.DCIM_DIRECTORY)
        if not os.path.exists(self.tmp_directory): os.makedirs(self.tmp_directory)
        if not os.path.exists(self.save_directory): os.makedirs(self.save_directory)

        # Start USB transfer
        if self.USB_EXPORT:
            self.usb_transfer = UsbTransfer(self, self.save_directory, min_free_gb=self.USB_MIN_FREE_GB)
            self.usb_transfer.start()
        else:
            Logger.info('PhotoboothApp: USB export disabled')
        
        # The web server always runs for gallery/admin access; SHARE only controls UI buttons.
        abs_save_directory = os.path.abspath(self.save_directory)
        self.web_server = WebServer(
            abs_save_directory,
            host='0.0.0.0',
            port=self.WEB_PORT,
            admin_password=config.get_admin_password(),
            restart_callback=self.request_restart,
        )
        if self.web_server.start():
            Logger.info(
                'PhotoboothApp: Web server started at %s:%s (share_ui=%s)',
                abs_save_directory,
                self.WEB_PORT,
                self.SHARE,
            )
        else:
            Logger.error('PhotoboothApp: Web server failed to start; gallery and admin are unavailable')
            self._requested_screen = ScreenMgr.ERROR
            self._requested_kwargs = {
                'message': f"Web server cannot be bound to port {self.WEB_PORT}.",
                'show_continue': True,
                'show_restart': True,
            }

        self._log_disk_space('startup')
        if self.is_disk_space_critical():
            self._requested_screen = ScreenMgr.ERROR
            self._requested_kwargs = self._disk_maintenance_kwargs()
        self._log_runtime_snapshot('startup')

    def build(self):
        Logger.info('PhotoboothApp: build().')
        self.sm = ScreenMgr(self, transition=FadeTransition(duration=0.08))
        if self._requested_screen:
            self.sm.current = self._requested_screen
        self.sm.current_screen.on_entry()
        if self._requested_screen and self._requested_kwargs:
            self.sm.current_screen.on_entry(self._requested_kwargs)
        return self.sm

    def on_stop(self):
        self._log_runtime_snapshot('shutdown')
        if self.ringled:
            self.ringled.clear()
        if getattr(self, 'web_server', None):
            self.web_server.stop()
        if getattr(self, 'usb_transfer', None):
            self.usb_transfer.stop()
        if getattr(self, 'devices', None):
            self.devices.close()

    def request_restart(self):
        """Request a clean application restart from a background thread."""
        Logger.warning('PhotoboothApp: restart requested')
        self._log_runtime_snapshot('restart_requested')
        Clock.schedule_once(lambda dt: self.stop(), 0)

    def request_transition_to(self, new_state, **kwargs):
        """
        Request a screen transition from any thread.
        """
        Clock.schedule_once(lambda dt: self.transition_to(new_state, **kwargs), 0)

    def transition_to(self, new_state, **kwargs):
        self.sm.current_screen.on_exit()
        self.sm.current = new_state
        self.sm.current_screen.on_entry(kwargs)

    def enter_maintenance_mode(self, message, show_continue=False, show_restart=True):
        Logger.error('PhotoboothApp: entering maintenance mode message=%s', message)
        self.request_transition_to(
            ScreenMgr.ERROR,
            message=message,
            show_continue=show_continue,
            show_restart=show_restart,
        )

    def get_current_screen_name(self):
        if self.sm is None:
            return None
        return self.sm.current

    def is_usb_copy_allowed(self):
        current_screen = self.get_current_screen_name()
        return current_screen == ScreenMgr.START

    def get_shot(self, shot_idx):
        return os.path.join(self.tmp_directory, "capture-{}.jpg".format(shot_idx))

    def get_collage(self):
        return os.path.join(self.tmp_directory, 'collage.jpg')

    def get_saved_collage(self):
        if not self.last_saved_session_directory:
            return None
        path = os.path.join(self.last_saved_session_directory, 'collage.jpg')
        return path if os.path.exists(path) else None

    def get_saved_collage(self):
        if not self.last_saved_session_directory:
            return None
        path = os.path.join(self.last_saved_session_directory, 'collage.jpg')
        return path if os.path.exists(path) else None

    def get_shots_to_take(self, format=0):
        return self.print_formats[format].get_photos_required()

    def get_layout_previews(self, format=0):
        return [f.get_preview() for f in self.print_formats]

    def get_format_aspect_ratio(self, format_idx):
        """Get the aspect ratio (width/height) for the given format."""
        return self.print_formats[format_idx].get_aspect_ratio()

    def _log_disk_space(self, context):
        try:
            usage = self.get_disk_usage()
            Logger.info(
                'PhotoboothApp: disk usage [%s] free=%.2fGB total=%.2fGB used=%.1f%% path=%s',
                context,
                usage['free_gb'],
                usage['total_gb'],
                usage['used_percent'],
                self.DCIM_DIRECTORY,
            )
        except Exception as exc:
            Logger.warning('PhotoboothApp: disk usage check failed [%s]: %s', context, exc)

    def _rotate_logs(self):
        try:
            now = time.time()
            max_age = self._log_retention_days * 86400
            log_files = [path for path in LOG_DIRECTORY.iterdir() if path.is_file()]

            removed = 0
            for path in log_files:
                try:
                    if now - path.stat().st_mtime > max_age:
                        path.unlink()
                        removed += 1
                except OSError as exc:
                    Logger.warning('PhotoboothApp: could not remove old log %s: %s', path, exc)

            remaining = sorted(
                [path for path in LOG_DIRECTORY.iterdir() if path.is_file()],
                key=lambda item: item.stat().st_mtime,
                reverse=True,
            )
            for path in remaining[self._log_max_files:]:
                try:
                    path.unlink()
                    removed += 1
                except OSError as exc:
                    Logger.warning('PhotoboothApp: could not remove extra log %s: %s', path, exc)

            Logger.info('PhotoboothApp: log rotation removed_files=%s retention_days=%s max_files=%s', removed, self._log_retention_days, self._log_max_files)
        except Exception as exc:
            Logger.warning('PhotoboothApp: log rotation failed: %s', exc)

    def get_disk_usage(self):
        usage = shutil.disk_usage(self.DCIM_DIRECTORY)
        free_gb = usage.free / (1024 ** 3)
        total_gb = usage.total / (1024 ** 3)
        used_percent = 0 if usage.total == 0 else ((usage.total - usage.free) / usage.total) * 100
        return {
            'free_gb': free_gb,
            'total_gb': total_gb,
            'used_percent': used_percent,
        }

    def is_disk_space_critical(self):
        try:
            usage = self.get_disk_usage()
        except Exception as exc:
            Logger.warning('PhotoboothApp: disk critical check failed: %s', exc)
            return False
        return usage['free_gb'] < self.DISK_MIN_FREE_GB or usage['used_percent'] >= self.DISK_MAX_USED_PERCENT

    def _disk_maintenance_kwargs(self):
        return {
            'message': 'Photo storage is full. Please call an operator.',
            'show_continue': False,
            'show_restart': True,
        }

    def ensure_disk_space_or_maintenance(self):
        if not self.is_disk_space_critical():
            return True
        self.enter_maintenance_mode(**self._disk_maintenance_kwargs())
        return False

    def _log_runtime_snapshot(self, context):
        Logger.info(
            'PhotoboothApp: runtime snapshot [%s] threads=%d current_screen=%s share=%s printer=%s',
            context,
            len(threading.enumerate()),
            self.get_current_screen_name(),
            self.SHARE,
            self.PRINTER,
        )

    def _start_background_process(self, kind, target, *args, **kwargs):
        with self._process_lock:
            self._process_token += 1
            process_token = self._process_token
            self._process_state = {
                'kind': kind,
                'token': process_token,
                'error': None,
                'traceback': None,
                'started_at': time.monotonic(),
                'finished_at': None,
            }

        Logger.info('PhotoboothApp: background %s started token=%s', kind, process_token)

        def run_target():
            error = None
            tb = None
            try:
                target(*args, **kwargs)
            except Exception as exc:
                error = str(exc) or exc.__class__.__name__
                tb = traceback.format_exc()
                Logger.error('PhotoboothApp: background %s failed: %s', kind, error)
                Logger.error(tb)
            finally:
                with self._process_lock:
                    if self._process_state.get('token') == process_token:
                        self._process_state['error'] = error
                        self._process_state['traceback'] = tb
                        self._process_state['finished_at'] = time.monotonic()

                duration = time.monotonic() - self._process_state['started_at'] if self._process_state.get('token') == process_token else None
                if error is None:
                    Logger.info('PhotoboothApp: background %s completed token=%s duration=%.2fs', kind, process_token, duration or 0)
                else:
                    Logger.error('PhotoboothApp: background %s finished with error token=%s duration=%.2fs', kind, process_token, duration or 0)
                self._log_runtime_snapshot(f'background_{kind}_done')

        process = threading.Thread(target=run_target, name=f'photobooth-{kind}-{process_token}', daemon=True)
        process.start()
        self.processes = [process]

    def _get_process_state(self):
        with self._process_lock:
            return dict(self._process_state)

    def has_process_failed(self, kind=None):
        state = self._get_process_state()
        if kind is not None and state.get('kind') != kind:
            return False
        return state.get('error') is not None

    def get_process_error(self, kind=None):
        state = self._get_process_state()
        if kind is not None and state.get('kind') != kind:
            return None
        return state.get('traceback') or state.get('error')

    def has_process_timed_out(self, kind, timeout_seconds):
        state = self._get_process_state()
        if state.get('kind') != kind:
            return False
        if state.get('finished_at') is not None:
            return False
        started_at = state.get('started_at')
        if started_at is None:
            return False
        return (time.monotonic() - started_at) >= timeout_seconds

    def abandon_background_processes(self, kind=None, reason='unknown'):
        with self._process_lock:
            if kind is not None and self._process_state.get('kind') != kind:
                return
            Logger.warning('PhotoboothApp: abandoning background process kind=%s reason=%s', self._process_state.get('kind'), reason)
            self._process_token += 1
            self._process_state['error'] = reason
            self._process_state['finished_at'] = time.monotonic()
        self.processes = []

    def trigger_shot(self, shot_idx, format_idx):
        Logger.info('PhotoboothApp: trigger_shot().')
        if not self.ensure_disk_space_or_maintenance():
            raise RuntimeError('Photo storage is almost full')
        aspect_ratio = self.get_format_aspect_ratio(format_idx)
        Logger.info('PhotoboothApp: shot request idx=%s format=%s aspect_ratio=%.4f', shot_idx, format_idx, aspect_ratio)
        self._log_disk_space('before_shot')
        flash_callback = self.ringled.flash if self.ringled else None
        self._start_background_process('shot', self.devices.capture, self.get_shot(shot_idx), aspect_ratio, flash_callback)

    def is_shot_completed(self, shot_idx):
        if any(process.is_alive() for process in self.processes): return False
        return True

    def trigger_collage(self, format=0):
        Logger.info('PhotoboothApp: trigger_collage().')
        if not self.ensure_disk_space_or_maintenance():
            raise RuntimeError('Photo storage is almost full')
        photos = []
        for i in range(0, self.get_shots_to_take(format)): photos.append(self.get_shot(i))
        Logger.info('PhotoboothApp: collage request format=%s photos=%s', format, len(photos))
        self._log_disk_space('before_collage')
        # Pass for_print=True to enable horizontal duplication for strip formats
        self._start_background_process(
            'collage',
            self.print_formats[format].assemble,
            output_path=self.get_collage(),
            image_paths=photos,
            for_print=True,
        )

    def is_collage_completed(self):
        if any(process.is_alive() for process in self.processes): return False
        return True

    def has_background_processes(self):
        return any(process.is_alive() for process in self.processes)

    def has_physical_flash(self):
        return self.devices.has_physical_flash()

    def has_printer(self):
        return self.devices.has_printer()

    def trigger_print(self, copies, format=0):
        Logger.info('PhotoboothApp: trigger_print().')
        if not self.has_printer():
            raise RuntimeError('Printer is not available')
        options = self.print_formats[format].get_print_params()
        options['copies'] = str(copies)
        Logger.info('PhotoboothApp: print request format=%s copies=%s printer_available=%s', format, copies, self.has_printer())
        self._log_disk_space('before_print')
        
        # Use duplicated print output only for templates that generate one.
        print_collage = self.get_collage().replace('.jpg', '_print.jpg')
        if self.print_formats[format].uses_print_version() and os.path.exists(print_collage):
            Logger.info(f'PhotoboothApp: Using print version: {print_collage}')
            return self.devices.print(print_collage, options)

        collage = self.get_collage() if os.path.exists(self.get_collage()) else self.get_saved_collage()
        if collage is None:
            raise FileNotFoundError('No collage available to print')
        return self.devices.print(collage, options)

    def start_photo_task(self, target, *args):
        def run_target():
            try:
                target(*args)
            except Exception:
                with self._pending_photo_lock:
                    self._pending_photo_error = traceback.format_exc()
                Logger.error(self._pending_photo_error)

        task = threading.Thread(target=run_target, name='photobooth-photo-task', daemon=True)
        with self._pending_photo_lock:
            self._pending_photo_error = None
            self.pending_photo_tasks = [task for task in self.pending_photo_tasks if task.is_alive()]
            self.pending_photo_tasks.append(task)
        task.start()

    def has_pending_photo_tasks(self):
        with self._pending_photo_lock:
            self.pending_photo_tasks = [task for task in self.pending_photo_tasks if task.is_alive()]
            return bool(self.pending_photo_tasks)

    def get_pending_photo_error(self):
        with self._pending_photo_lock:
            return self._pending_photo_error

    def clear_pending_photo_error(self):
        with self._pending_photo_lock:
            self._pending_photo_error = None

    def is_print_completed(self, print_task_id):
        try:
            status = self.devices.get_print_status(print_task_id)
            Logger.info('PhotoboothApp: print status task=%s status=%s', print_task_id, status)
            return status == 'done'
        except Exception as exc:
            Logger.error('PhotoboothApp: print status check failed task=%s error=%s', print_task_id, exc)
            return False

    def reset_devices(self, reason='unknown'):
        Logger.warning('PhotoboothApp: resetting devices reason=%s', reason)
        try:
            if getattr(self, 'devices', None):
                self.devices.close()
        except Exception as exc:
            Logger.warning('PhotoboothApp: device close during reset failed: %s', exc)

        self.devices = DeviceUtils(
            printer_name=self.PRINTER,
            zoom=self.CALIBRATION,
            dslr_liveview_params=self._dslr_liveview_params,
            dslr_capture_params=self._dslr_capture_params,
        )
        self._log_runtime_snapshot('devices_reset')

    def recover_devices_and_return_home(self, reason='unknown'):
        def recover():
            try:
                self.abandon_background_processes(kind='shot', reason=reason)
                self.reset_devices(reason=reason)
                self.request_transition_to(ScreenMgr.START)
            except Exception as exc:
                Logger.error('PhotoboothApp: device recovery failed: %s', exc)
                Logger.error(traceback.format_exc())
                self.enter_maintenance_mode(
                    message='Camera recovery failed. Please call an operator.',
                )

        threading.Thread(target=recover, name='photobooth-device-recovery', daemon=True).start()

    def save_collage(self):
        Logger.info('PhotoboothApp: save_collage().')
        if not self.ensure_disk_space_or_maintenance():
            raise RuntimeError('Photo storage is almost full')
        # List existing files
        all_files = os.listdir(self.tmp_directory)
        if len(all_files) == 0: return

        # Create new directory
        now = datetime.now()
        destination = os.path.join(self.save_directory, now.strftime('%Y%m%d_%H%M%S'))
        os.makedirs(destination, exist_ok=True)

        # Move to save_directory (exclude small previews and print versions)
        moved_files = 0
        for f in all_files:
            if '_small' in f or '_print' in f: continue
            src_path = os.path.join(self.tmp_directory, f)
            dst_path = os.path.join(destination, f)
            try:
                FileUtils.move_file(src_path, dst_path)
                moved_files += 1
            except FileNotFoundError:
                Logger.warning('PhotoboothApp: file disappeared before save: %s', src_path)
            except Exception as exc:
                Logger.error('PhotoboothApp: failed to save %s to %s: %s', src_path, dst_path, exc)
                raise

        if moved_files:
            self.last_saved_session_directory = destination
        self._log_disk_space('after_save')
        if getattr(self, 'web_server', None):
            session_id = os.path.basename(destination)
            for _ in range(moved_files):
                self.web_server.track_photo_taken(session_id=session_id)

    def purge_tmp(self):
        # List existing files and delete (including _print versions)
        all_files = os.listdir(self.tmp_directory)
        if len(all_files) == 0: return
        removed_files = 0
        for f in all_files:
            src_path = os.path.join(self.tmp_directory, f)
            if os.path.isfile(src_path):
                try:
                    if FileUtils.remove_file(src_path):
                        removed_files += 1
                except Exception as exc:
                    Logger.warning('PhotoboothApp: failed to purge temp file %s: %s', src_path, exc)
        Logger.info('PhotoboothApp: purged tmp directory removed_files=%s', removed_files)

if __name__ == '__main__':
    PhotoboothApp().run()
