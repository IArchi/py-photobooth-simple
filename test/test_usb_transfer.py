import time
import errno
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from libs.usb_transfer import UsbTransfer
from libs.screens import CopyingScreen


class App:
    pass


def test_copy_timeout_stops_recursive_export(tmp_path):
    source = tmp_path / 'source'
    destination = tmp_path / 'destination'
    source.mkdir()
    (source / 'photo.jpg').write_bytes(b'photo')
    transfer = UsbTransfer(App(), source, copy_timeout=10)

    with pytest.raises(TimeoutError):
        transfer.copy_without_overwrite(source, destination, deadline=time.monotonic() - 1)


def test_read_only_volume_is_detected():
    drive = SimpleNamespace(device='/dev/sda1', mountpoint='/media/pi/USB', opts='ro,nosuid')
    assert UsbTransfer.is_removable_partition(drive)
    drive.mountpoint = '/'
    assert not UsbTransfer.is_removable_partition(drive)


def test_unmounted_usb_detection_ignores_mounted_disks(monkeypatch):
    monkeypatch.setattr('libs.usb_transfer.sys.platform', 'linux')
    disks = [
        {'name': '/dev/sda', 'tran': 'usb', 'size': 1000, 'children': [
            {'mountpoints': [None]}, {'mountpoints': ['/media/pi/USB']},
        ]},
        {'name': '/dev/sdb', 'tran': 'usb', 'size': 1000, 'children': [
            {'mountpoints': [None]},
        ]},
        {'name': '/dev/sdc', 'tran': 'usb', 'size': 0},
        {'name': '/dev/mmcblk0', 'tran': None, 'rm': False, 'size': 1000},
    ]
    monkeypatch.setattr('libs.usb_transfer.subprocess.run', lambda *a, **kw: SimpleNamespace(
        stdout=json.dumps({'blockdevices': disks}),
    ))
    assert UsbTransfer.get_unmounted_usb_devices() == {'/dev/sdb'}


@pytest.mark.parametrize('mountpoint,opts,error', [
    ('', '', None),
    ('/media/pi/USB', 'ro,nosuid', None),
    ('/media/pi/USB', 'rw', PermissionError(errno.EACCES, 'Permission denied')),
    ('/media/pi/USB', 'rw', OSError(errno.EROFS, 'Read-only filesystem')),
])
def test_incompatible_drive_shows_message_without_copying(monkeypatch, mountpoint, opts, error):
    app = Mock()
    app.is_usb_copy_allowed.return_value = True
    transfer = UsbTransfer(app, '/photos')
    transfer._stop_event = Mock()
    transfer._stop_event.is_set.return_value = False
    transfer._check_destination_capacity = Mock(side_effect=error)
    transfer.copy_without_overwrite = Mock()
    transfer._finish_copy = Mock()
    monkeypatch.setattr('libs.usb_transfer.Clock.schedule_once', lambda callback, delay: callback(0))
    monkeypatch.setattr(transfer, 'get_unmounted_usb_devices', lambda: {'/dev/sda'})

    transfer.handle_mount(SimpleNamespace(device='/dev/sda', mountpoint=mountpoint, opts=opts))

    transfer.copy_without_overwrite.assert_not_called()
    result = transfer._finish_copy.call_args.args[0]
    assert result['status'] == 'error'
    assert result['error_key'] == 'copying.incompatible'
    assert not transfer._pending_mounts


def test_unmounted_detection_waits_for_automount(monkeypatch):
    transfer = UsbTransfer(Mock(), '/photos')
    snapshots = iter([set(), {'/dev/sda'}, {'/dev/sda'}, {'/dev/sda'}])
    monkeypatch.setattr(transfer, 'get_unmounted_usb_devices', lambda: next(snapshots))
    monkeypatch.setattr(transfer, 'get_current_removable_media', lambda: set())
    clock = iter([0, 5, 11])
    monkeypatch.setattr('libs.usb_transfer.time.monotonic', lambda: next(clock))
    polls = []

    def sleep(seconds):
        polls.append(seconds)
        if len(polls) == 3:
            transfer._stop_event.set()

    monkeypatch.setattr('libs.usb_transfer.time.sleep', sleep)
    transfer.handle_mount = Mock()
    transfer._worker_fun()
    transfer.handle_mount.assert_called_once()
    assert transfer.handle_mount.call_args.args[0].mountpoint == ''


def test_unmounted_warning_cancelled_when_automount_succeeds(monkeypatch):
    transfer = UsbTransfer(Mock(), '/photos')
    snapshots = iter([set(), {'/dev/sda'}, set(), set()])
    monkeypatch.setattr(transfer, 'get_unmounted_usb_devices', lambda: next(snapshots))
    monkeypatch.setattr(transfer, 'get_current_removable_media', lambda: set())
    clock = iter([0, 5, 11])
    monkeypatch.setattr('libs.usb_transfer.time.monotonic', lambda: next(clock))
    polls = []

    def sleep(seconds):
        polls.append(seconds)
        if len(polls) == 3:
            transfer._stop_event.set()

    monkeypatch.setattr('libs.usb_transfer.time.sleep', sleep)
    transfer.handle_mount = Mock()
    transfer._worker_fun()
    transfer.handle_mount.assert_not_called()


def test_usb_inspection_failure_is_nonfatal(monkeypatch):
    monkeypatch.setattr('libs.usb_transfer.sys.platform', 'linux')
    monkeypatch.setattr('libs.usb_transfer.subprocess.run', Mock(side_effect=FileNotFoundError))
    assert UsbTransfer.get_unmounted_usb_devices() == set()


def test_copying_screen_translates_usb_error():
    screen = SimpleNamespace(app=Mock(), loading=Mock(), info=Mock(), progress=Mock())
    screen.app.t.side_effect = lambda key: 'translated ' + key
    CopyingScreen.on_update(screen, {'status': 'error', 'error_key': 'copying.incompatible'})
    assert screen.progress.text == 'translated copying.incompatible'
    screen.loading.stop_animation.assert_called_once()
