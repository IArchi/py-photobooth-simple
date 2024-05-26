import os
import shlex
import shutil
import subprocess
from datetime import datetime
from kivy.app import App
from kivy.logger import Logger
from kivy.uix.screenmanager import NoTransition

from libs.device_utils import DeviceUtils
from libs.screens import ScreenMgr
from libs.ringled import RingLed
from libs.collage import Collage
from libs.usb_transfer import UsbTransfer

class PhotoboothApp(App):
    # Configuration
    COUNTDOWN = 3
    SHOTS_TO_TAKE = 3
    ROOT_DIRECTORY = '/tmp/photobooth'
    PRINTER = 'truc'
    PRINT_DUAL = True

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
        self.sm = ScreenMgr(self, transition=NoTransition())
        return self.sm

    def transition_to(self, new_state, *args):
        self.sm.current_screen.on_leave()
        self.sm.current = new_state
        self.sm.current_screen.on_entry(args)

    def get_shot(self, shot_idx):
        return os.path.join(self.tmp_directory, "capture-{}.jpg".format(shot_idx))

    def get_collage(self):
        return os.path.join(self.tmp_directory, 'collage.jpg')

    def trigger_shot(self, shot_idx):
        Logger.info('PhotoboothApp: trigger_shot().')
        self.process = self.devices.capture(self.get_shot(shot_idx))

    def is_shot_completed(self, shot_idx):
        if any((process.poll() is None for process in self.processes)): return False
        return True

    def trigger_collage(self):
        Logger.info('PhotoboothApp: trigger_collage().')
        # Create a list with all the shots and the logo
        photos = []
        for i in range(0, self.SHOTS_TO_TAKE): photos.append(self.get_shot(i))
        photos.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.png'))

        collage_process = Collage.create_collage(self.get_collage(), photos, dual=self.PRINT_DUAL)
        self.processes = [collage_process]

    def is_collage_completed(self):
        if any((process.poll() is None for process in self.processes)): return False
        return True

    def trigger_print(self, copies):
        Logger.info('PhotoboothApp: trigger_print().')
        return self.devices.print(self.get_collage(), copies=copies, dual=self.PRINT_DUAL)

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
            src_path = os.path.join(self.tmp_directory, f)
            dst_path = os.path.join(destination, f)
            os.rename(src_path, dst_path)
            os.remove(src_path)

if __name__ == '__main__':
    PhotoboothApp().run()
