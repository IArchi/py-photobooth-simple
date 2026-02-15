import configparser

class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('./config.ini')

    def get_autorestart(self):
        return self.config.getboolean('Global', 'AUTORESTART')

    def get_fullscreen(self):
        return self.config.getboolean('Global', 'FULLSCREEN')

    def get_share(self):
        return self.config.getboolean('Global', 'SHARE')

    def get_ringled(self):
        return self.config.getboolean('Global', 'RINGLED')

    def get_countdown(self):
        return self.config.getint('Picture', 'COUNTDOWN')

    def get_dcim_directory(self):
        return self.config.get('Picture', 'DCIM_DIRECTORY')

    def get_printer(self):
        printer = self.config.get('Picture', 'PRINTER')
        return printer if printer != 'None' else None

    def get_calibration(self):
        calibration = self.config.get('Picture', 'CALIBRATION')
        return eval(calibration) if calibration != 'None' else None

    def get_filters(self):
        return self.config.getboolean('Picture', 'FILTERS')

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
