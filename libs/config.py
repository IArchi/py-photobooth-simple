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
