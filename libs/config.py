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

    def get_fullscreen(self):
        return self.config.getboolean('Global', 'FULLSCREEN', fallback=True)

    def get_share(self):
        return self.config.getboolean('Global', 'SHARE', fallback=True)

    def get_ringled(self):
        return self.config.getboolean('Global', 'RINGLED', fallback=False)

    def get_admin_password(self):
        password = self.config.get('Global', 'ADMIN_PASSWORD', fallback='').strip()
        return password if password and password.upper() != 'NONE' else None

    def get_web_port(self):
        return self.config.getint('Global', 'WEB_PORT', fallback=5000)

    def get_countdown(self):
        return self.config.getint('Picture', 'COUNTDOWN', fallback=5)

    def get_dcim_directory(self):
        dcim_directory = self.config.get('Picture', 'DCIM_DIRECTORY')
        path = Path(dcim_directory).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return str(path.resolve())

    def get_disk_min_free_gb(self):
        return max(0.0, self.config.getfloat('Picture', 'DISK_MIN_FREE_GB', fallback=2.0))

    def get_disk_max_used_percent(self):
        return min(100.0, max(0.0, self.config.getfloat('Picture', 'DISK_MAX_USED_PERCENT', fallback=90.0)))

    def get_log_retention_days(self):
        return max(1, self.config.getint('Global', 'LOG_RETENTION_DAYS', fallback=14))

    def get_log_max_files(self):
        return max(1, self.config.getint('Global', 'LOG_MAX_FILES', fallback=40))

    def get_printer_wait_timeout(self):
        return max(5, self.config.getint('Picture', 'PRINTER_WAIT_TIMEOUT', fallback=45))

    def get_usb_export_enabled(self):
        return self.config.getboolean('Picture', 'USB_EXPORT', fallback=True)

    def get_usb_min_free_gb(self):
        return max(0.0, self.config.getfloat('Picture', 'USB_MIN_FREE_GB', fallback=1.0))

    def get_printer(self):
        printer = self.config.get('Picture', 'PRINTER')
        return printer if printer != 'None' else None

    def get_calibration(self):
        calibration = self.config.get('Picture', 'CALIBRATION')
        return ast.literal_eval(calibration) if calibration != 'None' else None

    def get_filters(self):
        return self.config.getboolean('Picture', 'FILTERS', fallback=False)

    def get_preview_blur_refresh_frames(self):
        return max(1, self.config.getint('Picture', 'PREVIEW_BLUR_REFRESH_FRAMES', fallback=3))

    def get_blur_camera(self):
        return self.config.getboolean('Picture', 'BLUR_CAMERA', fallback=True)

    def get_blur_images(self):
        return self.config.getboolean('Picture', 'BLUR_IMAGES', fallback=False)

    def get_blur_collage(self):
        return self.config.getboolean('Picture', 'BLUR_COLLAGE', fallback=False)

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
