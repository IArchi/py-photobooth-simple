import os
import time
import psutil
import shutil
import traceback
from pathlib import Path

from threading import Event, Thread
from kivy.clock import Clock
from kivy.logger import Logger

from libs.screens import ScreenMgr

class UsbTransfer:
    REMOVABLE_MOUNT_ROOTS = ('/media', '/run/media', '/Volumes')

    def __init__(self, app, folder, min_free_gb=1.0):
        Logger.info('UsbTransfer: __init__().')
        self._app = app
        self._folder = folder
        self._min_free_bytes = int(max(0.0, min_free_gb) * 1024 ** 3)
        self._worker_thread: Thread = None
        self._stop_event = Event()
        self._pending_mounts = {}

    def start(self):
        Logger.info('UsbTransfer: start().')
        self._worker_thread = Thread(name='_usbtransfer_worker', target=self._worker_fun, daemon=True)
        self._worker_thread.start()

    def stop(self):
        Logger.info('UsbTransfer: stop().')
        if self._worker_thread and self._worker_thread.is_alive():
            self._stop_event.set()
            self._worker_thread.join(timeout=5)
            if self._worker_thread.is_alive():
                Logger.warning('UsbTransfer: worker did not stop within timeout')

    def _worker_fun(self):
        # init worker, get devices first time
        _previous_devices = self.get_current_removable_media()

        while not self._stop_event.is_set():
            current_devices = self.get_current_removable_media()
            added = current_devices - _previous_devices
            removed = _previous_devices - current_devices

            for device in added: self.handle_mount(device)
            for device in removed: self.handle_unmount(device)
            if self._pending_mounts:
                self._process_pending_mounts()
            _previous_devices = current_devices

            # poll every 1 seconds
            time.sleep(1)

    def handle_mount(self, device: psutil._common.sdiskpart):
        Logger.info("UsbTransfer: handle_mount({})".format(device.device))

        if not device.mountpoint:
            Logger.error("USB device {} not correctly mounted".format(device.device))
            return

        self._pending_mounts[device.device] = device
        Logger.info('UsbTransfer: pending exports=%s', len(self._pending_mounts))
        if not self._app.is_usb_copy_allowed():
            Logger.info('UsbTransfer: deferring copy for %s until start screen', device.device)
            return

        self._process_pending_mounts()

    def handle_unmount(self, device: psutil._common.sdiskpart):
        Logger.info("UsbTransfer: handle_unmount({})".format(device.device))
        self._pending_mounts.pop(device.device, None)

    def _process_pending_mounts(self):
        if not self._app.is_usb_copy_allowed():
            return

        pending_devices = list(self._pending_mounts.values())
        for device in pending_devices:
            if self._stop_event.is_set():
                return
            if not device.mountpoint:
                self._pending_mounts.pop(device.device, None)
                continue

            self._app.request_transition_to(ScreenMgr.COPYING)
            try:
                Logger.info('UsbTransfer: starting export device=%s mountpoint=%s', device.device, device.mountpoint)
                destination = Path(device.mountpoint, 'photobooth')
                self._check_destination_capacity(destination)
                copied_files = self.copy_without_overwrite(self._folder, destination)
                Logger.info('UsbTransfer: export completed device=%s mountpoint=%s copied_files=%s', device.device, device.mountpoint, copied_files)
            except Exception as exc:
                Logger.error('UsbTransfer: Failed to perform folder copy.')
                Logger.error(traceback.format_exc())
                if self._stop_event.is_set():
                    return
                Logger.warning('UsbTransfer: USB export skipped after failure: %s', exc)
            finally:
                self._pending_mounts.pop(device.device, None)
                if self._app.get_current_screen_name() == ScreenMgr.COPYING:
                    self._app.request_transition_to(ScreenMgr.START)

    def _check_destination_capacity(self, destination_path):
        destination_path.mkdir(parents=True, exist_ok=True)
        usage = shutil.disk_usage(destination_path)
        if usage.free < self._min_free_bytes:
            raise RuntimeError('USB drive has only %.2fGB free, minimum is %.2fGB' % (usage.free / (1024 ** 3), self._min_free_bytes / (1024 ** 3)))

    @staticmethod
    def get_current_removable_media():
        return {
            device
            for device in psutil.disk_partitions(all=False)
            if UsbTransfer.is_removable_partition(device)
        }

    @classmethod
    def is_removable_partition(cls, device: psutil._common.sdiskpart):
        mountpoint = Path(device.mountpoint or '')
        opts = {opt.strip() for opt in (device.opts or '').split(',') if opt.strip()}

        if not device.mountpoint or device.mountpoint == '/':
            return False

        if 'rootfs' in opts or 'dontbrowse' in opts or 'ro' in opts:
            return False

        return any(
            mountpoint == Path(root) or mountpoint.is_relative_to(root)
            for root in cls.REMOVABLE_MOUNT_ROOTS
        )

    def copy_folders_to_usb(self, usb_path):
        Logger.info("UsbTransfer: copy_folders_to_usb()")
        destination_path = Path(usb_path, 'photobooth')

        try:
            os.makedirs(destination_path, exist_ok=True)
        except Exception as exc:
            Logger.warning("UsbTransfer: Cannot create destination folder on USB drive")

        Logger.info("UsbTransfer: Copying {} to {}".format(self._folder, destination_path))
        try:
            shutil.copytree(self._folder, destination_path, dirs_exist_ok=True)
        except Exception as exc:
            Logger.warning("UsbTransfer: Cannot copy files to USB drive")
            return

    def copy_without_overwrite(self, src, dest):
        src_path = Path(src)
        dest_path = Path(dest)
        copied_files = 0

        if not src_path.exists(): raise ValueError("Source directory does not exist")
        dest_path.mkdir(parents=True, exist_ok=True)

        for item in src_path.iterdir():
            if self._stop_event.is_set():
                return copied_files
            s = src_path / item.name
            d = dest_path / item.name
            if s.is_dir():
                copied_files += self.copy_without_overwrite(s, d)
            else:
                if not d.exists():
                    Clock.schedule_once(lambda dt, label=item.name: self._app.sm.get_screen(ScreenMgr.COPYING).on_update({'label': label}), 0)
                    shutil.copy2(s, d)
                    copied_files += 1

        return copied_files
