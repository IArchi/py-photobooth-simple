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
        spi = spidev.SpiDev()
        spi.open(0,0)
        self._proc = None
        self._stop = threading.Event()
        self._leds = WS2812(spi, self._num_pixels)

    def start_countdown(self, time_seconds):
        Logger.info('RingLed: start_countdown().')
        if spidev is None: return
        if self._proc and self._proc.is_alive():
            self._stop.clear()
            time.sleep(0.1)
        self._proc = threading.Thread(target=self._countdown, args=[time_seconds])
        self._proc.start()

    def start_rainbow(self):
        Logger.info('RingLed: start_rainbow().')
        if spidev is None: return
        if self._proc and self._proc.is_alive():
            self._stop.clear()
            time.sleep(0.1)
        self._proc = threading.Thread(target=self._rainbow)
        self._proc.start()

    def flash(self, stop=False):
        Logger.info('RingLed: flash().')
        if spidev is None: return
        if self._proc and self._proc.is_alive():
            self._stop.clear()
            time.sleep(0.1)
        if not stop:
            self._leds.fill([255,255,255])
            time.sleep(0.1)
        else:
            self._leds.fill([0,0,0])
        #self._proc = threading.Thread(target=self._flash)
        #self._proc.start()

    def blink(self, color):
        Logger.info('RingLed: blink().')
        if spidev is None: return
        if self._proc and self._proc.is_alive():
            self._stop.clear()
            time.sleep(0.1)
        self._proc = threading.Thread(target=self._blink, args=[color,])
        self._proc.start()

    def clear(self):
        Logger.info('RingLed: clear().')
        if spidev is None: return
        self._stop.set()
        self._leds.fill([0,0,0])

    def _blink(self, color):
        self._stop.clear()
        while True:
            self._leds.fill(color)
            time.sleep(0.1)
            self._leds.fill([0,0,0])
            time.sleep(0.1)
            if self._stop.isSet(): return

    def _countdown(self, time_seconds):
        self._stop.clear()
        time_between_pixels = time_seconds / self._num_pixels
        p1 = reversed(range(0, self._top_pixel+1))
        p2 = reversed(range(self._top_pixel, self._num_pixels))

        self._leds.fill([255,255,255])
        for i in [*p1, *p2]:
            self._leds.set(i, [0,0,0])
            time.sleep(time_between_pixels)
            if self._stop.isSet(): return

    def _rainbow(self):
        self._stop.clear()
        hue_step = 1.0 / self._num_pixels

        while True:
            for step in range(self._num_pixels):
                for i in range(self._num_pixels):
                    # Calculate hue for the current LED, with an offset for rotation
                    hue = (hue_step * ((i + step) % self._num_pixels)) % 1.0
                    # Convert HSV to RGB
                    rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    # Scale the RGB values to 0-255
                    rgb_scaled = [int(255 * x) for x in rgb]
                    self._leds.set(i, rgb_scaled)
                    if self._stop.isSet(): return
                time.sleep(0.1)
