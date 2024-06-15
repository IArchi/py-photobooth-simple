import time
import threading
try:
    import spidev
    import colorsys
except:
    spidev = None

from kivy.logger import Logger

from libs.ws2812 import WS2812

class RingLed:
    def __init__(self, num_pixels=12):
        Logger.info('RingLed: __init__().')
        self._num_pixels = num_pixels
        self._top_pixel = 6
        if spidev is None: return
        self._stop = threading.Event()
        self._proc = None
        self._leds = WS2812(spidev.SpiDev(), self._num_pixels)

    def _start_thread(self, target, args=None):
        if self._proc and self._proc.is_alive():
            self._stop.set()
            self._proc.join()
        self._stop.clear()
        if args: self._proc = threading.Thread(target=target, args=args)
        else: self._proc = threading.Thread(target=target)
        self._proc.start()

    def start_countdown(self, time_seconds):
        Logger.info('RingLed: start_countdown().')
        if spidev is None: return
        self._start_thread(self._countdown, args=[time_seconds])

    def start_rainbow(self):
        Logger.info('RingLed: start_rainbow().')
        if spidev is None: return
        self._start_thread(self._rainbow)

    def flash(self, stop=False):
        Logger.info('RingLed: flash().')
        if spidev is None: return
        if self._proc and self._proc.is_alive():
            self._stop.set()
            self._proc.join()
        if not stop:
            self._leds.fill([255, 255, 255])
            time.sleep(0.1)
        else:
            self._leds.fill([0, 0, 0])

    def blink(self, color):
        Logger.info('RingLed: blink().')
        if spidev is None: return
        self._start_thread(self._blink, args=[color])

    def clear(self):
        Logger.info('RingLed: clear().')
        if spidev is None: return
        self._stop.set()
        if self._proc:
            self._proc.join()
        self._leds.fill([0, 0, 0])

    def _blink(self, color):
        while not self._stop.is_set():
            self._leds.fill(color)
            time.sleep(0.1)
            self._leds.fill([0, 0, 0])
            time.sleep(0.1)

    def _countdown(self, time_seconds):
        time_between_pixels = time_seconds / self._num_pixels
        p1 = reversed(range(0, self._top_pixel + 1))
        p2 = reversed(range(self._top_pixel, self._num_pixels))

        self._leds.fill([255, 255, 255])
        for i in [*p1, *p2]:
            if self._stop.is_set(): return
            self._leds.set(i, [0, 0, 0])
            time.sleep(time_between_pixels)

    def _rainbow(self):
        hue_step = 1.0 / self._num_pixels

        while not self._stop.is_set():
            for step in range(self._num_pixels):
                if self._stop.is_set(): return
                for i in range(self._num_pixels):
                    hue = (hue_step * ((i + step) % self._num_pixels)) % 1.0
                    rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    rgb_scaled = [int(255 * x) for x in rgb]
                    self._leds.set(i, rgb_scaled)
                time.sleep(0.1)
