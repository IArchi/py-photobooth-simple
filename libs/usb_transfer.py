import os
import time
import psutil
import shutil
from pathlib import Path

from threading import Event, Thread
from kivy.logger import Logger

from libs.screens import ScreenMgr

class UsbTransfer:
    def __init__(self, app, folder):
        Logger.info('UsbTransfer: __init__().')
        self._app = app
        self._folder = folder
        self._worker_thread: Thread = None
        self._stop_event = Event()

    def start(self):
        Logger.info('UsbTransfer: start().')
        self._worker_thread = Thread(name='_usbtransfer_worker', target=self._worker_fun, daemon=True)
        self._worker_thread.start()

    def stop(self):
        Logger.info('UsbTransfer: stop().')
        if self._worker_thread and self._worker_thread.is_alive():
            self._stop_event.set()
            self._worker_thread.join()

    def _worker_fun(self):
        # init worker, get devices first time
        _previous_devices = self.get_current_removable_media()

        while not self._stop_event.is_set():
            current_devices = self.get_current_removable_media()
            added = current_devices - _previous_devices
            removed = _previous_devices - current_devices

            for device in added: self.handle_mount(device)
            for device in removed: self.handle_unmount(device)
            _previous_devices = current_devices

            # poll every 1 seconds
            time.sleep(1)

    def handle_mount(self, device: psutil._common.sdiskpart):
        Logger.info("UsbTransfer: handle_mount({})".format(device.device))

        if device.mountpoint:
            # TODO : Does not work from outside app thread
            self._app.request_transition_to(ScreenMgr.COPYING)
            try:
                self.copy_folders_to_usb(device.mountpoint)
            except:
                Logger.error('UsbTransfer: Failed to perform folder copy.')
            finally:
                self._app.request_transition_to(ScreenMgr.WAITING)
        else:
            Logger.error("USB device {} not correctly mounted".format(device.device))

    def handle_unmount(self, device: psutil._common.sdiskpart):
        Logger.info("UsbTransfer: handle_unmount({})".format(device.device))

    @staticmethod
    def get_current_removable_media():
        return {device for device in psutil.disk_partitions(all=False)}

    def copy_folders_to_usb(self, usb_path):
        Logger.info("UsbTransfer: copy_folders_to_usb()")
        destination_path = Path(usb_path, 'photobooth')

        try:
            os.makedirs(destination_path, exist_ok=True)
        except Exception as exc:
            Logger.warning("UsbTransfer: Cannot create destination folder on USB drive")

        Logger.info("UsbTransfer: Copying {}".format(self._folder))
        try:
            shutil.copytree(folder, destination_path, dirs_exist_ok=True)
        except Exception as exc:
            Logger.warning("UsbTransfer: Cannot copy files to USB drive")
            return
