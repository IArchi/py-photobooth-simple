#!/usr/bin/python3

import os
import sys
import signal
import threading
import traceback
from datetime import datetime
from kivy.app import App
from kivy.clock import Clock
from kivy.logger import Logger
from kivy.uix.screenmanager import NoTransition

from libs.config import Config
from libs.device_utils import DeviceUtils
from libs.screens import ScreenMgr
from libs.ringled import RingLed
from libs.template_collage import load_templates
from libs.usb_transfer import UsbTransfer
from libs.web_server import WebServer

RINGLED = RingLed(num_pixels=12)
autorestart = True

def signal_handler(sig, frame):
    global autorestart
    print("\nCtrl+C detected. Exiting gracefully...")
    autorestart = False
    if RINGLED: RINGLED.clear()
    sys.exit(0)
signal.signal(signal.SIGINT, signal_handler)

class PhotoboothApp(App):
    def __init__(self, **kwargs):
        global autorestart
        Logger.info('PhotoboothApp: __init__().')
        super(PhotoboothApp, self).__init__(**kwargs)

        # Load configuration
        config = Config()
        autorestart = config.get_autorestart()
        self.FULLSCREEN = config.get_fullscreen()
        self.SHARE = config.get_share()
        self.COUNTDOWN = config.get_countdown()
        self.DCIM_DIRECTORY = config.get_dcim_directory()
        self.PRINTER = config.get_printer()
        self.CALIBRATION = config.get_calibration()

        # Assign local variables
        self.sm = None
        self._requested_screen = None
        self._requested_kwargs = None
        self.processes = []
        self.ringled = RINGLED
        self.devices = DeviceUtils(printer_name=self.PRINTER, zoom=self.CALIBRATION)
        
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
        UsbTransfer(self, self.save_directory).start()
        
        # Initialize web server for photo gallery (convert to absolute path) only if SHARE is enabled
        if self.SHARE:
            abs_save_directory = os.path.abspath(self.save_directory)
            self.web_server = WebServer(abs_save_directory, host='0.0.0.0', port=5000)
            self.web_server.start()
            Logger.info(f'PhotoboothApp: Web server started for photo gallery at {abs_save_directory}')
        else:
            self.web_server = None
            Logger.info('PhotoboothApp: Web server disabled (SHARE=False)')

    def build(self):
        Logger.info('PhotoboothApp: build().')
        self.sm = ScreenMgr(self, transition=NoTransition())
        self.sm.current_screen.on_entry()
        return self.sm

    def on_stop(self):
        self.ringled.clear()

    def request_transition_to(self, new_state, **kwargs):
        """
        Request a screen transition. 
        OPTIMIZED: Direct call instead of polling for better performance.
        """
        self.transition_to(new_state, **kwargs)

    def transition_to(self, new_state, **kwargs):
        self.sm.current_screen.on_exit()
        self.sm.current = new_state
        self.sm.current_screen.on_entry(kwargs)

    def get_shot(self, shot_idx):
        return os.path.join(self.tmp_directory, "capture-{}.jpg".format(shot_idx))

    def get_collage(self):
        return os.path.join(self.tmp_directory, 'collage.jpg')

    def get_shots_to_take(self, format=0):
        return self.print_formats[format].get_photos_required()

    def get_layout_previews(self, format=0):
        return [f.get_preview() for f in self.print_formats]

    def get_format_aspect_ratio(self, format_idx):
        """Get the aspect ratio (width/height) for the given format."""
        return self.print_formats[format_idx].get_aspect_ratio()

    def trigger_shot(self, shot_idx, format_idx):
        Logger.info('PhotoboothApp: trigger_shot().')
        aspect_ratio = self.get_format_aspect_ratio(format_idx)
        t = threading.Thread(target=self.devices.capture, args=(self.get_shot(shot_idx), aspect_ratio, self.ringled.flash))
        t.start()
        self.processes = [t]

    def is_shot_completed(self, shot_idx):
        if any(process.is_alive() for process in self.processes): return False
        return True

    def trigger_collage(self, format=0):
        Logger.info('PhotoboothApp: trigger_collage().')
        photos = []
        for i in range(0, self.get_shots_to_take(format)): photos.append(self.get_shot(i))
        # Pass for_print=True to enable horizontal duplication for strip formats
        t = threading.Thread(target=self.print_formats[format].assemble, kwargs={'output_path':self.get_collage(), 'image_paths':photos, 'for_print':True})
        t.start()
        self.processes = [t]

    def is_collage_completed(self):
        if any(process.is_alive() for process in self.processes): return False
        return True

    def has_physical_flash(self):
        return self.devices.has_physical_flash()

    def has_printer(self):
        return self.devices.has_printer()

    def trigger_print(self, copies, format=0):
        Logger.info('PhotoboothApp: trigger_print().')
        options = self.print_formats[format].get_print_params()
        options['copies'] = str(copies)
        
        # Check if a print version exists (for duplicated templates)
        print_collage = self.get_collage().replace('.jpg', '_print.jpg')
        if os.path.exists(print_collage):
            Logger.info(f'PhotoboothApp: Using print version: {print_collage}')
            return self.devices.print(print_collage, options)
        else:
            return self.devices.print(self.get_collage(), options)

    def is_print_completed(self, print_task_id):
        try:
            return self.devices.get_print_status(print_task_id) == 'done'
        except:
            return True

    def save_collage(self):
        Logger.info('PhotoboothApp: save_collage().')
        # List existing files
        all_files = os.listdir(self.tmp_directory)
        if len(all_files) == 0: return

        # Create new directory
        now = datetime.now()
        destination = os.path.join(self.save_directory, now.strftime('%Y%m%d_%H%M%S'))
        os.makedirs(destination, exist_ok=True)

        # Move to save_directory (exclude small previews and print versions)
        for f in all_files:
            if '_small' in f or '_print' in f: continue
            src_path = os.path.join(self.tmp_directory, f)
            dst_path = os.path.join(destination, f)
            os.rename(src_path, dst_path)

    def purge_tmp(self):
        # List existing files and delete (including _print versions)
        all_files = os.listdir(self.tmp_directory)
        if len(all_files) == 0: return
        for f in all_files:
            src_path = os.path.join(self.tmp_directory, f)
            if os.path.isfile(src_path):
                os.remove(src_path)

if __name__ == '__main__':
    # Auto restart app on crash
    while autorestart:
        try:
            PhotoboothApp().run()
            break # stop the loop if the app completes sucessfully
        except Exception as e:
            print("Application errored out!", e)
            print(traceback.format_exc())
            print("Retrying ... ")
