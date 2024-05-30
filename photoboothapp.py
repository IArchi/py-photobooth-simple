import os
import threading
from datetime import datetime
from kivy.app import App
from kivy.logger import Logger
from kivy.uix.screenmanager import NoTransition

from locales import Locales
from libs.device_utils import DeviceUtils
from libs.screens import ScreenMgr
from libs.ringled import RingLed
from libs.collage import CollageManager
from libs.usb_transfer import UsbTransfer

class PhotoboothApp(App):
    # Configuration
    LOCALES = Locales.get_EN
    FULLSCREEN = False
    COUNTDOWN = 3
    ROOT_DIRECTORY = './DCIM' #'/tmp/photobooth'
    PRINTER = 'truc'
    PRINT_FORMATS = [CollageManager.PORTRAIT_8x3, CollageManager.LANDSCAPE_6x8]

    def __init__(self, **kwargs):
        Logger.info('PhotoboothApp: __init__().')
        super(PhotoboothApp, self).__init__(**kwargs)

        self.sm = None
        self.processes = []
        self.ringled = RingLed()
        self.devices = DeviceUtils(printer_name=self.PRINTER)

        # Create required directories
        self.tmp_directory = os.path.join(self.ROOT_DIRECTORY, 'tmp')
        self.save_directory = os.path.join(self.ROOT_DIRECTORY, 'save')
        if not os.path.exists(self.ROOT_DIRECTORY): os.makedirs(self.ROOT_DIRECTORY)
        if not os.path.exists(self.tmp_directory): os.makedirs(self.tmp_directory)
        if not os.path.exists(self.save_directory): os.makedirs(self.save_directory)

        # Start USB transfer
        UsbTransfer(self.save_directory).start()

    def build(self):
        Logger.info('PhotoboothApp: build().')
        self.sm = ScreenMgr(self, transition=NoTransition(), locales=self.LOCALES())
        return self.sm

    def transition_to(self, new_state, *args):
        self.sm.current_screen.on_leave()
        self.sm.current = new_state
        self.sm.current_screen.on_entry(args)

    def get_shot(self, shot_idx):
        return os.path.join(self.tmp_directory, "capture-{}.jpg".format(shot_idx))

    def get_collage(self):
        return os.path.join(self.tmp_directory, 'collage.jpg')

    def get_logo(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo_thick.png')

    def get_shots_to_take(self, format=0):
        return self.PRINT_FORMATS[format].get_photos_required()

    def get_layout_previews(self, format=0):
        return [f.get_preview() for f in self.PRINT_FORMATS]

    def trigger_shot(self, shot_idx):
        Logger.info('PhotoboothApp: trigger_shot().')
        t = threading.Thread(target=self.devices.capture, args=(self.get_shot(shot_idx),))
        self.processes = [t]
        t.start()

    def is_shot_completed(self, shot_idx):
        if any((process.is_alive() is None for process in self.processes)): return False
        return True

    def trigger_collage(self, format=0):
        Logger.info('PhotoboothApp: trigger_collage().')
        photos = []
        for i in range(0, self.get_shots_to_take()): photos.append(self.get_shot(i))
        t = threading.Thread(target=self.PRINT_FORMATS[format].assemble, kwargs={'output_name':self.get_collage(), 'photos':photos, 'logo':self.get_logo()})
        self.processes = [t]
        t.start()

    def is_collage_completed(self):
        if any((process.is_alive() is None for process in self.processes)): return False
        return True

    def has_printer(self):
        return self.devices.has_printer()

    def trigger_print(self, copies, format=0):
        Logger.info('PhotoboothApp: trigger_print().')
        return self.devices.print(self.get_collage(), copies=copies, print_format=self.PRINT_FORMATS[format].get_print_format())

    def is_print_completed(self, print_task_id):
        return self.devices.get_print_status(print_task_id) == 'done'

    def save_collage(self):
        Logger.info('PhotoboothApp: save_collage().')
        # List existing files
        all_files = os.listdir(self.tmp_directory)
        if len(all_files) == 0: return

        # Create new directory
        now = datetime.now()
        destination = os.path.join(self.save_directory, now.strftime('%Y%m%d_%H%M%S'))
        os.makedirs(destination, exist_ok=True)

        # Move to save_directory
        for f in all_files:
            print(f)
            src_path = os.path.join(self.tmp_directory, f)
            dst_path = os.path.join(destination, f)
            os.rename(src_path, dst_path)

if __name__ == '__main__':
    PhotoboothApp().run()
