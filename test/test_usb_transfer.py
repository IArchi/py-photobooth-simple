import time

import pytest

from libs.usb_transfer import UsbTransfer


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
