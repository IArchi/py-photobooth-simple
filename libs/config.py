import configparser
import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / 'config.ini'

class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        loaded_files = self.config.read(CONFIG_PATH)
        if not loaded_files:
            raise FileNotFoundError(f'Cannot load configuration file: {CONFIG_PATH}')

    def _get_value(self, getter_name, sections, option, fallback=None):
        getter = getattr(self.config, getter_name)
        for section in sections:
            if self.config.has_option(section, option):
                return getter(section, option)
        return fallback

    def _get_string(self, sections, option, fallback=''):
        return self._get_value('get', sections, option, fallback=fallback)

    def _get_boolean(self, sections, option, fallback=False):
        return self._get_value('getboolean', sections, option, fallback=fallback)

    def _get_int(self, sections, option, fallback=0):
        return self._get_value('getint', sections, option, fallback=fallback)

    def _get_float(self, sections, option, fallback=0.0):
        return self._get_value('getfloat', sections, option, fallback=fallback)

    def get_fullscreen(self):
        return self._get_boolean(('Global',), 'FULLSCREEN', fallback=True)

    def get_share(self):
        return self._get_boolean(('Global',), 'SHARE', fallback=True)

    def get_ringled(self):
        return self._get_boolean(('Global',), 'RINGLED', fallback=False)

    def get_admin_password(self):
        password = self._get_string(('Global',), 'ADMIN_PASSWORD', fallback='').strip()
        return password if password and password.upper() != 'NONE' else None

    def get_web_port(self):
        return 5000

    def get_countdown(self):
        return self._get_int(('Capture', 'Picture'), 'COUNTDOWN', fallback=5)

    def get_dcim_directory(self):
        dcim_directory = self._get_string(('Storage', 'Picture'), 'DCIM_DIRECTORY', fallback='./DCIM')
        path = Path(dcim_directory).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return str(path.resolve())

    def get_disk_min_free_gb(self):
        return max(0.0, self._get_float(('Storage', 'Picture'), 'DISK_MIN_FREE_GB', fallback=2.0))

    def get_disk_max_used_percent(self):
        return min(100.0, max(0.0, self._get_float(('Storage', 'Picture'), 'DISK_MAX_USED_PERCENT', fallback=90.0)))

    def get_log_retention_days(self):
        return max(1, self._get_int(('Log', 'Global'), 'LOG_RETENTION_DAYS', fallback=14))

    def get_log_max_files(self):
        return max(1, self._get_int(('Log', 'Global'), 'LOG_MAX_FILES', fallback=40))

    def get_printer_wait_timeout(self):
        return max(5, self._get_int(('Print', 'Picture'), 'PRINTER_WAIT_TIMEOUT', fallback=45))

    def get_usb_export_enabled(self):
        return self._get_boolean(('USB', 'Picture'), 'USB_EXPORT', fallback=True)

    def get_usb_min_free_gb(self):
        return max(0.0, self._get_float(('USB', 'Picture'), 'USB_MIN_FREE_GB', fallback=1.0))

    def get_printer(self):
        printer = self._get_string(('Print', 'Picture'), 'PRINTER', fallback='None')
        return printer if printer != 'None' else None

    def get_max_prints(self):
        max_prints = self._get_string(('Print', 'Picture'), 'MAX_PRINTS', fallback='None').strip()
        if not max_prints or max_prints.upper() == 'NONE':
            return None
        return max(0, int(max_prints))

    def get_calibration(self):
        calibration = self._get_string(('Capture', 'Picture'), 'CALIBRATION', fallback='None')
        return ast.literal_eval(calibration) if calibration != 'None' else None

    def get_filters(self):
        return self._get_boolean(('Capture', 'Picture'), 'FILTERS', fallback=False)

    def get_preview_blur_refresh_frames(self):
        return max(1, self._get_int(('Capture', 'Picture'), 'PREVIEW_BLUR_REFRESH_FRAMES', fallback=3))

    def get_blur_camera(self):
        return self._get_boolean(('Capture', 'Picture'), 'BLUR_CAMERA', fallback=True)

    def get_blur_images(self):
        return self._get_boolean(('Capture', 'Picture'), 'BLUR_IMAGES', fallback=False)

    def get_blur_collage(self):
        return self._get_boolean(('Capture', 'Picture'), 'BLUR_COLLAGE', fallback=False)

    def _get_dslr_params(self, section):
        """Returns a dict param -> value for the given DSLR section. Empty or None value = do not set."""
        keys = ['SHUTTERSPEED', 'APERTURE', 'FOCUSMODE', 'ISO']
        out = {}
        if not self.config.has_section(section):
            return out
        for k in keys:
            if self.config.has_option(section, k):
                v = self.config.get(section, k).strip()
                if v and v.upper() != 'NONE':
                    out[k] = v
        return out

    def get_dslr_liveview_params(self):
        return self._get_dslr_params('DSLR_Liveview')

    def get_dslr_capture_params(self):
        return self._get_dslr_params('DSLR_Capture')
