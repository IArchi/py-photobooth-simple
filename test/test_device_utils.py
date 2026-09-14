import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
from libs.device_utils import CupsPrinter, DeviceUtils, PrinterStatusError
from photoboothapp import PhotoboothApp


class FakePrinter:
    def __init__(self):
        self.file_path = None
        self.print_params = None

    def print(self, file_path, print_params):
        self.file_path = file_path
        self.print_params = print_params
        return 123

    def is_available(self):
        return True

    def get_status(self):
        return {'ok': True, 'state': 'idle', 'reasons': []}


class FakePrintFormat:
    def __init__(self, print_params=None, uses_print_version=False):
        self._print_params = print_params or {}
        self._uses_print_version = uses_print_version

    def get_print_params(self):
        return dict(self._print_params)

    def uses_print_version(self):
        return self._uses_print_version


class FakeStatsStore:
    def can_print(self):
        return True


def test_device_utils_print_returns_printer_task_id():
    devices = object.__new__(DeviceUtils)
    devices._printer = FakePrinter()

    assert devices.print('photo.jpg', {'copies': '1'}) == 123


def test_device_utils_print_without_printer_fails():
    devices = object.__new__(DeviceUtils)
    devices._printer = None

    with pytest.raises(RuntimeError):
        devices.print('photo.jpg', {'copies': '1'})


def test_photobooth_app_has_printer_uses_devices():
    class NoPrinterDevices:
        def has_printer(self):
            return False

    app = PhotoboothApp.__new__(PhotoboothApp)
    app.devices = NoPrinterDevices()

    assert app.has_printer() is False


def test_uncertain_print_state_blocks_duplicates_until_jobs_are_cleared():
    class Devices:
        def has_printer(self):
            return True

        def cancel_stale_print_jobs(self, strict=False):
            assert strict is True
            return 1

    app = PhotoboothApp.__new__(PhotoboothApp)
    app.devices = Devices()
    app.stats_store = FakeStatsStore()
    app._print_state_uncertain = False

    app.mark_print_state_uncertain()
    assert app.can_start_print() is False
    assert app.cancel_stale_print_jobs() == 1
    assert app.can_start_print() is True


def test_device_diagnostic_reports_hybrid_camera_and_printer():
    class Camera:
        def is_healthy(self):
            return True

    devices = object.__new__(DeviceUtils)
    devices._preview = Camera()
    devices._capture = Camera()
    devices._printer = FakePrinter()
    devices._printer._name = 'DNP'

    status = devices.get_diagnostic_status()

    assert status['camera_ok'] is True
    assert status['camera_name'] == 'Camera + Camera'
    assert status['printer_ok'] is True
    assert status['printer_name'] == 'DNP'
    assert status['printer_reasons'] == []


def test_cups_status_reports_normalized_paper_jam():
    printer = object.__new__(CupsPrinter)
    printer._name = 'DNP'
    printer._instance = type('Connection', (), {
        'getPrinters': lambda self: {
            'DNP': {
                'printer-state': 5,
                'printer-state-reasons': ['media-jam-error'],
                'printer-is-accepting-jobs': True,
            }
        }
    })()

    assert printer.get_status() == {
        'ok': False,
        'state': 'stopped',
        'reasons': ['media-jam'],
    }


def test_cups_completed_job_is_only_reported_as_sent():
    printer = object.__new__(CupsPrinter)
    printer._name = 'DNP'
    printer._instance = type('Connection', (), {
        'getJobAttributes': lambda self, task_id: {'job-state': 9, 'job-state-reasons': ['none']},
        'getPrinters': lambda self: {
            'DNP': {'printer-state': 3, 'printer-state-reasons': ['none'], 'printer-is-accepting-jobs': True}
        },
    })()

    assert printer.get_print_status(123) == 'sent'


def test_cups_job_failure_preserves_reason_code():
    printer = object.__new__(CupsPrinter)
    printer._name = 'DNP'
    printer._instance = type('Connection', (), {
        'getJobAttributes': lambda self, task_id: {'job-state': 8, 'job-state-reasons': ['media-empty-error']},
    })()

    with pytest.raises(PrinterStatusError) as error:
        printer.get_print_status(123)

    assert error.value.reasons == ['media-empty']


def test_camera_reconnect_replaces_devices(monkeypatch):
    class Devices:
        def __init__(self, *args, **kwargs):
            self.closed = False

        def close(self):
            self.closed = True

    old_devices = Devices()
    app = PhotoboothApp.__new__(PhotoboothApp)
    app.devices = old_devices
    app.PRINTER = None
    app.CALIBRATION = None
    app._dslr_liveview_params = {}
    app._dslr_capture_params = {}
    app._device_reconnect_lock = __import__('threading').Lock()
    app._device_reconnecting = False
    app._device_reconnect_last_attempt = 0
    monkeypatch.setattr('photoboothapp.DeviceUtils', Devices)

    class ImmediateThread:
        def __init__(self, target, **kwargs):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr('photoboothapp.threading.Thread', ImmediateThread)

    app.request_camera_reconnect()

    assert app.devices is not old_devices
    assert old_devices.closed is True
    assert app._device_reconnecting is False


def test_app_diagnostic_marks_missing_printer_configuration_as_disabled():
    class Devices:
        def get_diagnostic_status(self):
            return {'camera_ok': True, 'printer_ok': True, 'printer_configured': True}

    class WebServer:
        def is_running(self):
            return True

    app = PhotoboothApp.__new__(PhotoboothApp)
    app.devices = Devices()
    app.web_server = WebServer()
    app.PRINTER = None
    app.WEB_PORT = 5000
    app._device_reconnecting = False
    app.get_disk_usage = lambda: {'free_gb': 10, 'total_gb': 20, 'used_percent': 50}
    app.get_print_limit_info = lambda: {'enabled': False, 'prints': 3, 'remaining': None}
    app.is_disk_space_critical = lambda: False
    app.request_camera_reconnect = lambda: None

    assert app.get_diagnostic_status()['printer_configured'] is False


def test_trigger_print_ignores_stale_print_collage_for_fullpage(tmp_path):
    printer = FakePrinter()
    collage = tmp_path / 'collage.jpg'
    print_collage = tmp_path / 'collage_print.jpg'
    collage.write_bytes(b'fullpage')
    print_collage.write_bytes(b'stale strip')

    app = PhotoboothApp.__new__(PhotoboothApp)
    app.devices = printer
    app.stats_store = FakeStatsStore()
    app.print_formats = [FakePrintFormat({'PageSize': 'w288h432'}, uses_print_version=False)]
    app.get_collage = lambda: str(collage)
    app.get_saved_collage = lambda: None
    app.has_printer = lambda: True
    app._log_disk_space = lambda context: None

    assert app.trigger_print(1, format=0) == 123
    assert printer.file_path == str(collage)
    assert printer.print_params == {'PageSize': 'w288h432', 'copies': '1'}


def test_trigger_print_uses_print_collage_for_duplicated_strip(tmp_path):
    printer = FakePrinter()
    collage = tmp_path / 'collage.jpg'
    print_collage = tmp_path / 'collage_print.jpg'
    collage.write_bytes(b'strip')
    print_collage.write_bytes(b'duplicated strip')

    app = PhotoboothApp.__new__(PhotoboothApp)
    app.devices = printer
    app.stats_store = FakeStatsStore()
    app.print_formats = [FakePrintFormat({'PageSize': 'w288h432-div2'}, uses_print_version=True)]
    app.get_collage = lambda: str(collage)
    app.get_saved_collage = lambda: None
    app.has_printer = lambda: True
    app._log_disk_space = lambda context: None

    assert app.trigger_print(1, format=0) == 123
    assert printer.file_path == str(print_collage)
    assert printer.print_params == {'PageSize': 'w288h432-div2', 'copies': '1'}
