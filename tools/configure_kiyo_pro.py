#!/usr/bin/env python3
"""Configure/test a Razer Kiyo Pro stream on Linux.

This tool does two separate things:
- negotiates a video stream (default: 1920x1080 MJPG)
- optionally applies Kiyo Pro vendor controls (HDR/FOV/AF)

Important:
- width/height/fourcc are per-stream settings, not persistent camera settings
- keep the same values in Cv2Camera if you want the app to behave identically
"""

import argparse
import ctypes
import os
import sys
import time
from fcntl import ioctl

try:
    import cv2
except ImportError:
    cv2 = None


_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14

_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS

_IOC_WRITE = 1
_IOC_READ = 2

V4L2_CAP_VIDEO_CAPTURE = 0x00000001
KIYO_PRO_USB_ID = '1532:0e05'


def _IOC(dir_, type_, nr, size):
    return (
        ctypes.c_int32(dir_ << _IOC_DIRSHIFT).value
        | ctypes.c_int32(ord(type_) << _IOC_TYPESHIFT).value
        | ctypes.c_int32(nr << _IOC_NRSHIFT).value
        | ctypes.c_int32(size << _IOC_SIZESHIFT).value
    )


def _IOC_TYPECHECK(t):
    return ctypes.sizeof(t)


def _IOR(type_, nr, size):
    return _IOC(_IOC_READ, type_, nr, _IOC_TYPECHECK(size))


def _IOWR(type_, nr, size):
    return _IOC(_IOC_READ | _IOC_WRITE, type_, nr, _IOC_TYPECHECK(size))


class v4l2_capability(ctypes.Structure):
    _fields_ = [
        ('driver', ctypes.c_char * 16),
        ('card', ctypes.c_char * 32),
        ('bus_info', ctypes.c_char * 32),
        ('version', ctypes.c_uint32),
        ('capabilities', ctypes.c_uint32),
        ('device_caps', ctypes.c_uint32),
        ('reserved', ctypes.c_uint32 * 3),
    ]


class uvc_xu_control_query(ctypes.Structure):
    _fields_ = [
        ('unit', ctypes.c_uint8),
        ('selector', ctypes.c_uint8),
        ('query', ctypes.c_uint8),
        ('size', ctypes.c_uint16),
        ('data', ctypes.c_void_p),
    ]


VIDIOC_QUERYCAP = _IOR('V', 0, v4l2_capability)
UVCIOC_CTRL_QUERY = _IOWR('u', 0x21, uvc_xu_control_query)

UVC_SET_CUR = 0x01
UVC_GET_LEN = 0x85

EU1_SET_ISP = 0x01
UVC_EU1_GUID = b'\xd0\x9e\xe4\x23\x78\x11\x31\x4f\xae\x52\xd2\xfb\x8a\x8d\x3b\x48'

AF_RESPONSIVE = b'\xff\x06\x00\x00\x00\x00\x00\x00'
AF_PASSIVE = b'\xff\x06\x01\x00\x00\x00\x00\x00'

HDR_OFF = b'\xff\x02\x00\x00\x00\x00\x00\x00'
HDR_ON = b'\xff\x02\x01\x00\x00\x00\x00\x00'

HDR_DARK = b'\xff\x07\x00\x00\x00\x00\x00\x00'
HDR_BRIGHT = b'\xff\x07\x01\x00\x00\x00\x00\x00'

FOV_WIDE = b'\xff\x01\x00\x03\x00\x00\x00\x00'
FOV_MEDIUM_PRE = b'\xff\x01\x00\x03\x01\x00\x00\x00'
FOV_MEDIUM = b'\xff\x01\x01\x03\x01\x00\x00\x00'
FOV_NARROW_PRE = b'\xff\x01\x00\x03\x02\x00\x00\x00'
FOV_NARROW = b'\xff\x01\x01\x03\x02\x00\x00\x00'

SAVE = b'\xc0\x03\xa8\x00\x00\x00\x00\x00'


def to_buf(raw):
    return ctypes.create_string_buffer(raw)


def resolve_video_name(device):
    return os.path.basename(os.path.realpath(device))


def sysfs_usb_file(device, filename):
    video_name = resolve_video_name(device)
    return f'/sys/class/video4linux/{video_name}/../../../{filename}'


def read_text(path):
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            return handle.read().strip()
    except OSError:
        return ''


def find_unit_id_in_sysfs(device, guid):
    descfile = sysfs_usb_file(device, 'descriptors')
    if not os.path.isfile(descfile):
        return 0
    try:
        with open(descfile, 'rb') as handle:
            descriptors = handle.read()
    except OSError:
        return 0
    guid_start = descriptors.find(guid)
    if guid_start > 0:
        return descriptors[guid_start - 1]
    return 0


def find_usb_ids_in_sysfs(device):
    vendorfile = sysfs_usb_file(device, 'idVendor')
    productfile = sysfs_usb_file(device, 'idProduct')
    if not (os.path.isfile(vendorfile) and os.path.isfile(productfile)):
        return ''
    return f'{read_text(vendorfile)}:{read_text(productfile)}'


def get_device_capabilities(device):
    cap = v4l2_capability()
    fd = os.open(device, os.O_RDWR, 0)
    try:
        ioctl(fd, VIDIOC_QUERYCAP, cap)
    finally:
        os.close(fd)
    return cap.device_caps


def get_length_xu_control(fd, unit_id, selector):
    length = ctypes.c_uint16(0)
    query = uvc_xu_control_query()
    query.unit = unit_id
    query.selector = selector
    query.query = UVC_GET_LEN
    query.size = 2
    query.data = ctypes.cast(ctypes.pointer(length), ctypes.c_void_p)
    ioctl(fd, UVCIOC_CTRL_QUERY, query)
    return int(length.value)


def query_xu_control(fd, unit_id, selector, query_code, data):
    length = get_length_xu_control(fd, unit_id, selector)
    query = uvc_xu_control_query()
    query.unit = unit_id
    query.selector = selector
    query.query = query_code
    query.size = length
    query.data = ctypes.cast(ctypes.pointer(data), ctypes.c_void_p)
    ioctl(fd, UVCIOC_CTRL_QUERY, query)


class KiyoProControls:
    CONTROL_MENU = {
        'af_mode': {
            'passive': AF_PASSIVE,
            'responsive': AF_RESPONSIVE,
        },
        'hdr': {
            'off': HDR_OFF,
            'on': HDR_ON,
        },
        'hdr_mode': {
            'dark': HDR_DARK,
            'bright': HDR_BRIGHT,
        },
        'fov': {
            'wide': FOV_WIDE,
            'medium': FOV_MEDIUM,
            'narrow': FOV_NARROW,
        },
    }

    BEFORE_VALUES = {
        FOV_MEDIUM: FOV_MEDIUM_PRE,
        FOV_NARROW: FOV_NARROW_PRE,
    }

    def __init__(self, device, fd):
        self.device = device
        self.fd = fd
        self.unit_id = find_unit_id_in_sysfs(device, UVC_EU1_GUID)
        self.usb_ids = find_usb_ids_in_sysfs(device)

    def supported(self):
        return self.unit_id != 0 and self.usb_ids == KIYO_PRO_USB_ID

    def print_controls(self):
        for name, menu in self.CONTROL_MENU.items():
            print(f'{name}={"|".join(menu.keys())}')

    def apply(self, **params):
        for name, value in params.items():
            if value is None:
                continue

            menu = self.CONTROL_MENU.get(name)
            if menu is None:
                raise ValueError(f'Unknown control: {name}')

            payload = menu.get(value)
            if payload is None:
                raise ValueError(f'Invalid value for {name}: {value}')

            before = self.BEFORE_VALUES.get(payload)
            if before is not None:
                query_xu_control(self.fd, self.unit_id, EU1_SET_ISP, UVC_SET_CUR, to_buf(before))

            query_xu_control(self.fd, self.unit_id, EU1_SET_ISP, UVC_SET_CUR, to_buf(payload))

        query_xu_control(self.fd, self.unit_id, EU1_SET_ISP, UVC_SET_CUR, to_buf(SAVE))


def detect_kiyo_devices():
    devices = []
    by_id_dir = '/dev/v4l/by-id'
    if not os.path.isdir(by_id_dir):
        return devices

    for entry in sorted(os.listdir(by_id_dir)):
        device = os.path.join(by_id_dir, entry)
        try:
            if find_usb_ids_in_sysfs(device) != KIYO_PRO_USB_ID:
                continue
            if not (get_device_capabilities(device) & V4L2_CAP_VIDEO_CAPTURE):
                continue
        except OSError:
            continue
        devices.append(device)

    return devices


def pick_device(explicit_device=None):
    if explicit_device:
        if isinstance(explicit_device, str) and explicit_device.isdigit():
            return int(explicit_device)
        return explicit_device
    detected = detect_kiyo_devices()
    if detected:
        return detected[0]
    return 0


def fallback_index_from_device(device):
    if not isinstance(device, str):
        return None
    basename = os.path.basename(device)
    if basename.startswith('video') and basename[5:].isdigit():
        return int(basename[5:])
    return None


def open_capture(device):
    if cv2 is None:
        raise RuntimeError('OpenCV (cv2) is required to negotiate/test the stream')

    backend = getattr(cv2, 'CAP_V4L2', cv2.CAP_ANY) if sys.platform.startswith('linux') else cv2.CAP_ANY
    capture = cv2.VideoCapture(device, backend)
    if not capture.isOpened():
        capture.release()
        fallback_index = fallback_index_from_device(device)
        if fallback_index is not None:
            capture = cv2.VideoCapture(fallback_index, cv2.CAP_ANY)
    if not capture.isOpened():
        raise RuntimeError(f'Cannot open {device}')
    return capture


def fourcc_to_string(value):
    value = int(value)
    chars = [chr((value >> (8 * i)) & 0xFF) for i in range(4)]
    return ''.join(chars).strip() or '????'


def negotiate_stream(device, width, height, fps, fourcc, warmup_frames=10):
    capture = open_capture(device)
    try:
        capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        if fps is not None:
            capture.set(cv2.CAP_PROP_FPS, fps)

        frame = None
        for _ in range(max(1, warmup_frames)):
            ok, current = capture.read()
            if ok:
                frame = current
            time.sleep(0.02)

        actual = {
            'width': int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'fps': capture.get(cv2.CAP_PROP_FPS),
            'fourcc': fourcc_to_string(capture.get(cv2.CAP_PROP_FOURCC)),
            'frame': frame,
        }
        return capture, actual
    except Exception:
        capture.release()
        raise


def toggle_value(current, values):
    index = values.index(current)
    return values[(index + 1) % len(values)]


def draw_overlay(frame, actual, measured_fps, control_state, controls_available, status_message=None):
    frame = cv2.putText(frame, 'Stream: {}x{} {}'.format(
        actual['width'],
        actual['height'],
        actual['fourcc'],
    ), (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    frame = cv2.putText(frame, 'FPS requested: {:.1f} | measured: {:.1f}'.format(
        actual['fps'],
        measured_fps,
    ), (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    if controls_available:
        frame = cv2.putText(frame, 'HDR (Key: h): {}'.format(control_state['hdr']), (10, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        frame = cv2.putText(frame, 'HDR Mode (Key: m): {}'.format(control_state['hdr_mode']), (10, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        frame = cv2.putText(frame, 'FOV (Key: f): {}'.format(control_state['fov']), (10, 195), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        frame = cv2.putText(frame, 'AF (Key: a): {}'.format(control_state['af_mode']), (10, 235), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    else:
        frame = cv2.putText(frame, 'Kiyo Pro vendor controls unavailable on this device', (10, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 200, 255), 2, cv2.LINE_AA)

    frame = cv2.putText(frame, 'Exit (Key: q)', (10, 275), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2, cv2.LINE_AA)

    if status_message:
        frame = cv2.putText(frame, status_message, (10, 315), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

    return frame


def preview_loop(capture, actual, kiyo=None, control_state=None):
    print('Preview active. Press q or ESC to quit.')
    controls_available = kiyo is not None and kiyo.supported()
    if control_state is None:
        control_state = {
            'hdr': 'off',
            'hdr_mode': 'bright',
            'fov': 'wide',
            'af_mode': 'responsive',
        }

    status_message = None
    status_until = 0
    last_frame_at = None
    measured_fps = 0.0

    while True:
        ok, frame = capture.read()
        if not ok:
            continue

        now = time.perf_counter()
        if last_frame_at is not None:
            instant_fps = 1.0 / max(now - last_frame_at, 1e-6)
            measured_fps = instant_fps if measured_fps == 0.0 else (measured_fps * 0.9 + instant_fps * 0.1)
        last_frame_at = now

        if status_until and time.time() > status_until:
            status_message = None
            status_until = 0

        frame = draw_overlay(frame, actual, measured_fps, control_state, controls_available, status_message)
        cv2.imshow('Kiyo Pro', frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord('q'), ord('Q')):
            break
        if key == 255:
            continue

        if not controls_available:
            continue

        lower_key = chr(key).lower() if key < 256 else ''
        try:
            if lower_key == 'h':
                control_state['hdr'] = toggle_value(control_state['hdr'], ['off', 'on'])
                kiyo.apply(hdr=control_state['hdr'], hdr_mode=control_state['hdr_mode'])
                status_message = 'Applied HDR={}'.format(control_state['hdr'])
            elif lower_key == 'm':
                control_state['hdr_mode'] = toggle_value(control_state['hdr_mode'], ['bright', 'dark'])
                kiyo.apply(hdr_mode=control_state['hdr_mode'])
                status_message = 'Applied HDR mode={}'.format(control_state['hdr_mode'])
            elif lower_key == 'f':
                control_state['fov'] = toggle_value(control_state['fov'], ['wide', 'medium', 'narrow'])
                kiyo.apply(fov=control_state['fov'])
                status_message = 'Applied FOV={}'.format(control_state['fov'])
            elif lower_key == 'a':
                control_state['af_mode'] = toggle_value(control_state['af_mode'], ['responsive', 'passive'])
                kiyo.apply(af_mode=control_state['af_mode'])
                status_message = 'Applied AF={}'.format(control_state['af_mode'])
            else:
                continue
            status_until = time.time() + 2
        except Exception as exc:
            status_message = 'Control apply failed: {}'.format(exc)
            status_until = time.time() + 3

    cv2.destroyAllWindows()


def parse_args():
    parser = argparse.ArgumentParser(
        description='Configure/test a Razer Kiyo Pro stream on Linux',
        epilog=(
            'Examples:\n'
            '  python3 tools/configure_kiyo_pro.py\n'
            '  python3 tools/configure_kiyo_pro.py --detect\n'
            '  python3 tools/configure_kiyo_pro.py --device /dev/video0 --hdr off --fov wide\n'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--device', default=None, help='video device path or camera index (default: first detected Kiyo Pro, else camera 0)')
    parser.add_argument('--detect', action='store_true', help='list detected Kiyo Pro capture devices and exit')
    parser.add_argument('--list-controls', action='store_true', help='list supported Kiyo Pro vendor controls and exit')
    parser.add_argument('--width', type=int, default=1920, help='requested stream width')
    parser.add_argument('--height', type=int, default=1080, help='requested stream height')
    parser.add_argument('--fps', type=int, default=30, help='requested stream fps')
    parser.add_argument('--fourcc', default='MJPG', help='requested V4L2 fourcc (default: MJPG)')
    parser.add_argument('--af-mode', choices=['passive', 'responsive'], default=None, help='apply Kiyo Pro autofocus mode')
    parser.add_argument('--hdr', choices=['off', 'on'], default=None, help='apply Kiyo Pro HDR on/off')
    parser.add_argument('--hdr-mode', choices=['dark', 'bright'], default=None, help='apply Kiyo Pro HDR mode')
    parser.add_argument('--fov', choices=['wide', 'medium', 'narrow'], default=None, help='apply Kiyo Pro field of view')
    return parser.parse_args()


def main():
    args = parse_args()

    if args.detect:
        devices = detect_kiyo_devices()
        if not devices:
            print('No Razer Kiyo Pro capture device detected.')
            return 1
        for device in devices:
            print(device)
        return 0

    device = pick_device(args.device)
    print(f'Device: {device}')

    kiyo = None
    kiyo_fd = None
    control_state = {
        'hdr': args.hdr or 'off',
        'hdr_mode': args.hdr_mode or 'bright',
        'fov': args.fov or 'wide',
        'af_mode': args.af_mode or 'responsive',
    }

    controls_requested = any((args.af_mode, args.hdr, args.hdr_mode, args.fov))

    if args.list_controls or controls_requested:
        if not isinstance(device, str):
            raise RuntimeError('Kiyo Pro vendor controls require a Linux video device path, for example /dev/video0')

        kiyo_fd = os.open(device, os.O_RDWR, 0)
        try:
            kiyo = KiyoProControls(device, kiyo_fd)
            if not kiyo.supported():
                raise RuntimeError(f'{device} is not a supported Razer Kiyo Pro control device')

            if args.list_controls:
                kiyo.print_controls()
                if not controls_requested:
                    return 0

            kiyo.apply(
                af_mode=control_state['af_mode'] if args.af_mode else None,
                hdr=control_state['hdr'] if args.hdr else None,
                hdr_mode=control_state['hdr_mode'] if args.hdr_mode else None,
                fov=control_state['fov'] if args.fov else None,
            )
            if controls_requested:
                print('Applied Kiyo Pro vendor controls.')
        except Exception:
            if kiyo_fd is not None:
                os.close(kiyo_fd)
                kiyo_fd = None
            raise

    if isinstance(device, str) and kiyo is None:
        try:
            kiyo_fd = os.open(device, os.O_RDWR, 0)
            kiyo = KiyoProControls(device, kiyo_fd)
            if not kiyo.supported():
                os.close(kiyo_fd)
                kiyo_fd = None
                kiyo = None
        except Exception:
            if kiyo_fd is not None:
                os.close(kiyo_fd)
                kiyo_fd = None
            kiyo = None

    capture, actual = negotiate_stream(
        device=device,
        width=args.width,
        height=args.height,
        fps=args.fps,
        fourcc=args.fourcc.upper(),
    )
    try:
        print(
            'Negotiated stream: '
            f"{actual['width']}x{actual['height']} {actual['fourcc']} {actual['fps']:.1f}fps"
        )
        if actual['frame'] is None:
            raise RuntimeError('The camera opened, but no frame was received.')
        preview_loop(capture, actual, kiyo=kiyo, control_state=control_state)
    finally:
        capture.release()
        if kiyo_fd is not None:
            os.close(kiyo_fd)

    print('Note: width/height/fourcc are per-stream settings; keep the same values in Cv2Camera.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
