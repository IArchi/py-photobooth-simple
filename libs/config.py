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
        return self.config.get('Picture', 'DCIM_DIRECTORY')

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
