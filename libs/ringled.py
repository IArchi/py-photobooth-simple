import time
import math
import threading
import numpy as np
try:
    import spidev
    import colorsys
except:
    spidev = None

from kivy.logger import Logger

class WS2812:
    def __init__(self, spi, nb_leds=12):
        self._spi = spi
        self._nb_leds = nb_leds
        self._pixels = [[0,0,0]]*self._nb_leds

    def write(self, rgb, brightness=1.0):
        self._pixels = rgb
        scaled_rgb = [[int(c * brightness) for c in color] for color in rgb]
        grb = [[arr[1], arr[0], arr[2]] for arr in scaled_rgb]
        d = np.array(grb).ravel()
        tx = np.zeros(len(d)*4, dtype=np.uint8)
        for ibit in range(4):
            tx[3-ibit::4]=((d>>(2*ibit+1))&1)*0x60 + ((d>>(2*ibit+0))&1)*0x06 + 0x88
        self._spi.xfer(tx.tolist(), int(4/1.25e-6))

    def fill(self, color, brightness=1.0):
        self.write([color]*self._nb_leds)

    def set(self, pixel, color, brightness=1.0):
        self._pixels[pixel] = [int(c * brightness) for c in color]
        self.write(self._pixels)

    def get(self, pixel=-1):
        if pixel < 0: return self._pixels
        return self._pixels(pixel)

class RingLed:
    def __init__(self, num_pixels=12):
        Logger.info('RingLed: __init__().')
        self._num_pixels = num_pixels
        self._top_pixel = 6
        self._proc = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._leds = None
        if spidev is None: return
        spi = spidev.SpiDev()
        spi.open(0,0)
        self._leds = WS2812(spi, self._num_pixels)

    def _stop_worker(self):
        if self._proc and self._proc.is_alive():
            self._stop.set()
            self._proc.join(timeout=1)
            if self._proc.is_alive():
                Logger.warning('RingLed: worker thread did not stop cleanly')
        self._proc = None

    def _start_worker(self, name, target, *args):
        with self._lock:
            self._stop_worker()
            self._stop.clear()
            self._proc = threading.Thread(target=target, args=args, name=f'ringled-{name}', daemon=True)
            self._proc.start()

    def start_countdown(self, time_seconds):
        Logger.info('RingLed: start_countdown().')
        if spidev is None: return
        self._start_worker('countdown', self._countdown, time_seconds)

    def start_rainbow(self):
        Logger.info('RingLed: start_rainbow().')
        if spidev is None: return
        self._start_worker('rainbow', self._rainbow)

    def flash(self, stop=False):
        Logger.info('RingLed: flash().')
        if spidev is None: return
        with self._lock:
            self._stop_worker()
            self._stop.clear()
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
        self._start_worker('blink', self._blink, color)

    def wave(self, color):
        Logger.info('RingLed: wave().')
        if spidev is None: return
        self._start_worker('wave', self._wave, color)

    def clear(self):
        Logger.info('RingLed: clear().')
        if spidev is None: return
        with self._lock:
            self._stop_worker()
            self._stop.clear()
            self._leds.fill([0,0,0])

    def _blink(self, color):
        while True:
            self._leds.fill(color)
            time.sleep(0.1)
            self._leds.fill([0,0,0])
            time.sleep(0.1)
            if self._stop.is_set(): return

    def _wave(self, color):
        wave_intensity = 0.5
        wave_length = self._num_pixels
        while True:
            for step in range(self._num_pixels):
                for i in range(self._num_pixels):
                    # Calculate intensity based on a sine wave
                    intensity = (math.sin(2 * math.pi * ((i + step) % wave_length) / wave_length) + 1) / 2
                    intensity = wave_intensity * intensity  # Scale intensity to desired range
                    self._leds.set(i, color, brightness=intensity)
                    if self._stop.is_set(): return
                time.sleep(0.1)

    def _countdown(self, time_seconds):
        time_between_pixels = time_seconds / self._num_pixels
        p1 = reversed(range(0, self._top_pixel+1))
        p2 = reversed(range(self._top_pixel, self._num_pixels))

        self._leds.fill([255,255,255])
        time.sleep(0.1)
        for i in [*p1, *p2]:
            self._leds.set(i, [0,0,0])
            time.sleep(time_between_pixels)
            if self._stop.is_set(): return

    def _rainbow(self):
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
                    if self._stop.is_set(): return
                time.sleep(0.1)
