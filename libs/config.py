import configparser

class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('./config.ini')

    def get_locales(self):
        return self.config.get('Global', 'LOCALES')

    def get_fullscreen(self):
        return self.config.getboolean('Global', 'FULLSCREEN')

    def get_countdown(self):
        return self.config.getint('Picture', 'COUNTDOWN')

    def get_dcim_directory(self):
        return self.config.get('Picture', 'DCIM_DIRECTORY')

    def get_printer(self):
        printer = self.config.get('Picture', 'PRINTER')
        return printer if printer != 'None' else None

    def get_hybrid_zoom(self):
        hybrid_zoom = self.config.get('Picture', 'HYBRID_ZOOM')
        return eval(hybrid_zoom) if hybrid_zoom != 'None' else None