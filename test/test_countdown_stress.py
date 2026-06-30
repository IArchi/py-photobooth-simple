#!/usr/bin/env python3
import argparse
import os
import sys
import tempfile
import threading
import time
import traceback
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

# Ponytail: this stays a focused screen-flow stress test with fake devices.
# If we ever need to reproduce hardware-specific DSLR bugs, extend the fake
# device scenarios instead of booting the full application here.
os.environ.setdefault('KIVY_NO_ARGS', '1')
os.environ.setdefault('KIVY_GL_BACKEND', 'mock')

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from kivy.config import Config as KivyConfig

KivyConfig.set('kivy', 'window', 'sdl2')
KivyConfig.set('graphics', 'fullscreen', '0')
KivyConfig.set('graphics', 'width', '800')
KivyConfig.set('graphics', 'height', '600')

from kivy.base import EventLoop
from kivy.clock import Clock

from libs.file_utils import FileUtils
import libs.screens as screens_module
from libs.screens import ConfirmCaptureScreen, CountdownScreen, ScreenMgr

screens_module.SHOT_TIMEOUT_SECONDS = 0.5


class DummyFormat:
    def get_aspect_ratio(self):
        return 1.0

    def get_photos_required(self):
        return 1


class FakeDevices:
    def __init__(self, hang_time=2.0):
        self.hang_time = hang_time
        self.current_scenario = 'ok_fast'
        self.preview = np.zeros((720, 720, 3), dtype=np.uint8)

    def get_preview_fps(self):
        return 30

    def get_preview(self, aspect_ratio=None):
        return self.preview.copy()

    def capture(self, output_name, aspect_ratio=None, flash_fn=None):
        scenario = self.current_scenario
        image = np.full((960, 960, 3), 180, dtype=np.uint8)
        small_path = FileUtils.get_small_path(output_name)

        if scenario == 'exception':
            raise RuntimeError('Synthetic capture failure at countdown end')

        if scenario == 'hang':
            time.sleep(self.hang_time)
            return

        if scenario == 'slow_full':
            time.sleep(0.15)

        if scenario != 'missing_full':
            cv2.imwrite(output_name, image)

        if scenario == 'delayed_small':
            def write_small_later():
                time.sleep(0.2)
                cv2.imwrite(small_path, FileUtils.resize(image))

            threading.Thread(target=write_small_later, daemon=True).start()
        elif scenario == 'corrupt_small':
            Path(small_path).write_bytes(b'not-a-jpeg')
        elif scenario not in {'missing_small', 'missing_full'}:
            cv2.imwrite(small_path, FileUtils.resize(image))


class FakeApp:
    FULLSCREEN = False
    SHARE = False
    FILTERS = False
    COUNTDOWN = 1
    ringled = None

    def __init__(self, tmp_dir, devices):
        self.tmp_directory = tmp_dir
        self.devices = devices
        self.print_formats = [DummyFormat(), DummyFormat()]
        self.processes = []
        self._process_state = {'kind': None, 'error': None, 'traceback': None, 'started_at': None, 'finished_at': None}
        self._process_token = 0
        self.transitions = []
        self.thread_errors = []
        self.last_transition = None
        self.confirm_screen = None

    def get_shot(self, shot_idx):
        return os.path.join(self.tmp_directory, f'capture-{shot_idx}.jpg')

    def get_shots_to_take(self, format=0):
        return self.print_formats[format].get_photos_required()

    def get_format_aspect_ratio(self, format_idx):
        return self.print_formats[format_idx].get_aspect_ratio()

    def trigger_shot(self, shot_idx, format_idx):
        aspect_ratio = self.get_format_aspect_ratio(format_idx)
        self._process_token += 1
        process_token = self._process_token
        self._process_state = {
            'kind': 'shot',
            'error': None,
            'traceback': None,
            'started_at': time.monotonic(),
            'finished_at': None,
            'token': process_token,
        }

        def run_capture():
            try:
                self.devices.capture(self.get_shot(shot_idx), aspect_ratio, None)
            except Exception as exc:
                tb = traceback.format_exc()
                self.thread_errors.append(tb)
                if self._process_state.get('token') == process_token:
                    self._process_state['error'] = str(exc) or exc.__class__.__name__
                    self._process_state['traceback'] = tb
            finally:
                if self._process_state.get('token') == process_token:
                    self._process_state['finished_at'] = time.monotonic()

        capture_thread = threading.Thread(target=run_capture, daemon=True)
        capture_thread.start()
        self.processes = [capture_thread]

    def is_shot_completed(self, shot_idx):
        return not any(process.is_alive() for process in self.processes)

    def has_process_failed(self, kind=None):
        return self._process_state.get('error') is not None and (kind is None or self._process_state.get('kind') == kind)

    def get_process_error(self, kind=None):
        if kind is not None and self._process_state.get('kind') != kind:
            return None
        return self._process_state.get('traceback') or self._process_state.get('error')

    def has_process_timed_out(self, kind, timeout_seconds):
        if self._process_state.get('kind') != kind:
            return False
        if self._process_state.get('finished_at') is not None:
            return False
        started_at = self._process_state.get('started_at')
        if started_at is None:
            return False
        return (time.monotonic() - started_at) >= timeout_seconds

    def transition_to(self, new_state, **kwargs):
        self.last_transition = new_state
        self.transitions.append((new_state, kwargs))
        if new_state == ScreenMgr.CONFIRM_CAPTURE and self.confirm_screen is not None:
            self.confirm_screen.on_entry(kwargs)


def pump_clock(duration, step=0.01):
    deadline = time.perf_counter() + duration
    while time.perf_counter() < deadline:
        Clock.tick()
        time.sleep(step)


def cleanup_iteration(countdown_screen, confirm_screen, tmp_dir):
    Clock.unschedule(countdown_screen.timer_trigger)
    Clock.unschedule(countdown_screen.timer_event)
    Clock.unschedule(confirm_screen.timer_event)

    try:
        countdown_screen.on_exit()
    except Exception:
        pass

    if hasattr(confirm_screen, 'auto_leave'):
        Clock.unschedule(confirm_screen.auto_leave)

    try:
        confirm_screen.on_exit()
    except Exception:
        pass

    for file_path in Path(tmp_dir).glob('*'):
        if file_path.is_file():
            file_path.unlink()

    pump_clock(0.02)


def run_iteration(app, countdown_screen, scenario, deadline):
    app.devices.current_scenario = scenario
    app.last_transition = None
    app.transitions.clear()
    app.thread_errors.clear()

    countdown_screen.on_entry({'shot': 0, 'format': 0})
    countdown_screen._timer_active = True
    countdown_screen.start_countdown()

    if countdown_screen._clock is not None:
        Clock.unschedule(countdown_screen._clock)
        countdown_screen._clock = None

    countdown_screen.timer_event(None)
    Clock.unschedule(countdown_screen.timer_trigger)
    countdown_screen._clock_trigger = None

    started_at = time.perf_counter()
    while time.perf_counter() - started_at < deadline:
        countdown_screen.timer_trigger(None)
        pump_clock(0.02)
        if app.last_transition in {ScreenMgr.CONFIRM_CAPTURE, ScreenMgr.ERROR}:
            break

    result = {
        'scenario': scenario,
        'transition': app.last_transition,
        'thread_errors': list(app.thread_errors),
    }

    if app.last_transition is None:
        result['status'] = 'hang'
    elif app.last_transition == ScreenMgr.ERROR:
        result['status'] = 'error_screen'
    elif app.thread_errors:
        result['status'] = 'thread_exception'
    else:
        result['status'] = 'ok'

    return result


def main():
    parser = argparse.ArgumentParser(description='Stress test the countdown end/capture handoff.')
    parser.add_argument('--iterations', type=int, default=200)
    parser.add_argument('--deadline', type=float, default=0.8, help='Max seconds allowed per countdown cycle')
    parser.add_argument('--hang-time', type=float, default=12.0, help='Synthetic capture stall duration')
    args = parser.parse_args()

    EventLoop.ensure_window()

    scenarios = [
        'ok_fast',
        'slow_full',
        'delayed_small',
        'missing_small',
        'corrupt_small',
        'missing_full',
        'exception',
        'hang',
    ]

    counts = Counter()
    failures = []

    for index in range(args.iterations):
        scenario = scenarios[index % len(scenarios)]

        with tempfile.TemporaryDirectory(prefix='countdown-stress-') as tmp_dir:
            app = FakeApp(tmp_dir=tmp_dir, devices=FakeDevices(hang_time=args.hang_time))
            countdown_screen = CountdownScreen(app, name=ScreenMgr.COUNTDOWN)
            confirm_screen = ConfirmCaptureScreen(app, name=ScreenMgr.CONFIRM_CAPTURE)
            app.confirm_screen = confirm_screen

            result = run_iteration(app, countdown_screen, scenario, args.deadline)
            counts[result['status']] += 1

            if result['status'] != 'ok':
                failures.append(result)

            cleanup_iteration(countdown_screen, confirm_screen, tmp_dir)

    print('Countdown stress test summary')
    print('=============================')
    print(f'Iterations: {args.iterations}')
    print(f'Deadline:   {args.deadline:.2f}s')
    print(f'Hang time:  {args.hang_time:.2f}s')
    print()

    for status in sorted(counts):
        print(f'{status:16} {counts[status]}')

    if failures:
        print()
        print('Sample failures')
        print('---------------')
        for failure in failures[:10]:
            print(f"scenario={failure['scenario']} status={failure['status']} transition={failure['transition']}")
            for thread_error in failure['thread_errors']:
                print(thread_error.rstrip())
                print('---')
        raise SystemExit(1)


if __name__ == '__main__':
    main()
