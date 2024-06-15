#!/usr/bin/python3

import os
import threading
from datetime import datetime
from kivy.app import App
from kivy.logger import Logger
from kivy.uix.screenmanager import NoTransition

from libs.locales import Locales
from libs.device_utils import DeviceUtils
from libs.screens import ScreenMgr
from libs.ringled import RingLed
from libs.collage import CollageManager
from libs.usb_transfer import UsbTransfer

class PhotoboothApp(App):
    # Configuration
    LOCALES = Locales.get_EN
    FULLSCREEN = True
    COUNTDOWN = 3
    DCIM_DIRECTORY = './DCIM' #'/tmp/photobooth'
    PRINTER = 'truc'

    def __init__(self, **kwargs):
        Logger.info('PhotoboothApp: __init__().')
        super(PhotoboothApp, self).__init__(**kwargs)

        self.sm = None
        self.processes = []
        self.ringled = RingLed()
        self.devices = DeviceUtils(printer_name=self.PRINTER)
        self.print_formats = [CollageManager.POLAROID, CollageManager.STRIP]

        # Create required directories
        self.tmp_directory = os.path.join(self.DCIM_DIRECTORY, 'tmp')
        self.save_directory = os.path.join(self.DCIM_DIRECTORY, 'save')
        if not os.path.exists(self.DCIM_DIRECTORY): os.makedirs(self.DCIM_DIRECTORY)
        if not os.path.exists(self.tmp_directory): os.makedirs(self.tmp_directory)
        if not os.path.exists(self.save_directory): os.makedirs(self.save_directory)

        # Start USB transfer
        UsbTransfer(self, self.save_directory).start()

    def build(self):
        Logger.info('PhotoboothApp: build().')
        self.sm = ScreenMgr(self, transition=NoTransition(), locales=self.LOCALES())
        return self.sm

    def transition_to(self, new_state, **kwargs):
        self.sm.current_screen.on_leave()
        self.sm.current = new_state
        self.sm.current_screen.on_entry(kwargs)

    def get_shot(self, shot_idx):
        return os.path.join(self.tmp_directory, "capture-{}.jpg".format(shot_idx))

    def get_collage(self):
        return os.path.join(self.tmp_directory, 'collage.jpg')

    def get_logo(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo.png')

    def get_shots_to_take(self, format=0):
        return self.print_formats[format].get_photos_required()

    def get_layout_previews(self, format=0):
        return [f.get_preview(self.get_logo()) for f in self.print_formats]

    def is_square_format(self, format_idx):
        return self.print_formats[format_idx].is_squared()

    def trigger_shot(self, shot_idx, format_idx):
        Logger.info('PhotoboothApp: trigger_shot().')
        t = threading.Thread(target=self.devices.capture, args=(self.get_shot(shot_idx), self.print_formats[format_idx].is_squared(), self.app.ringled.flash))
        self.processes = [t]
        t.start()

    def is_shot_completed(self, shot_idx):
        if any((process.is_alive() is None for process in self.processes)): return False
        return True

    def trigger_collage(self, format=0):
        Logger.info('PhotoboothApp: trigger_collage().')
        photos = []
        for i in range(0, self.get_shots_to_take(format)): photos.append(self.get_shot(i))
        t = threading.Thread(target=self.print_formats[format].assemble, kwargs={'output_path':self.get_collage(), 'image_paths':photos, 'logo_path':self.get_logo()})
        self.processes = [t]
        t.start()

    def is_collage_completed(self):
        if any((process.is_alive() is None for process in self.processes)): return False
        return True

    def has_printer(self):
        return self.devices.has_printer()

    def trigger_print(self, copies, format=0):
        Logger.info('PhotoboothApp: trigger_print().')
        return self.devices.print(self.get_collage(), copies=copies, print_format=self.print_formats[format].get_print_format())

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

    def purge_tmp(self):
        # List existing files and delete
        all_files = os.listdir(self.tmp_directory)
        if len(all_files) == 0: return
        for f in all_files:
            src_path = os.path.join(self.tmp_directory, f)
            os.remove(src_path)

if __name__ == '__main__':
    PhotoboothApp().run()

    # # Auto restart app on crash
    # while True:
    #     try:
    #         PhotoboothApp().run()
    #         break # stop the loop if the app completes sucessfully
    #     except Exception as e:
    #         print("Application errored out!", e)
    #         print("Retrying ... ")
