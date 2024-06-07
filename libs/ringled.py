import time
import threading
try:
    import board
except:
    board = None
import neopixel_spi
from kivy.logger import Logger

class RingLed:
    def __init__(self):
        Logger.info('RingLed: __init__().')
        self._num_pixels = 12
        if board is None: return
        self._top_pixel = 6 # Depends on the orientation of the led ring
        self._order = neopixel_spi.RGBW
        self._proc = None
        self._stop = threading.Event()
        self._pixels = neopixel_spi.NeoPixel_SPI(board.SPI(), self._num_pixels, bpp=4, brightness=0.2, auto_write=False, pixel_order=self._order, bit0=0b10000000)

        # Identify top pixel
        self._pixels.fill((0,0,0,0))
        self._pixels[self._top_pixel] = (0, 0, 255, 0)
        self._pixels.show()

    def start_countdown(self, time_seconds):
        Logger.info('RingLed: start_countdown().')
        if board is None: return
        self._proc = threading.Thread(target=self._countdown, args=[time_seconds])
        self._proc.start()

    def start_rainbow(self):
        Logger.info('RingLed: start_rainbow().')
        if board is None: return
        self._proc = threading.Thread(target=self._rainbow)
        self._proc.start()

    def flash(self):
        Logger.info('RingLed: flash().')
        if board is None: return
        self._proc = threading.Thread(target=self._flash)
        self._proc.start()

    def blink(self, color):
        Logger.info('RingLed: blink().')
        if board is None: return
        self._proc = threading.Thread(target=self._blink, args=[color,])
        self._proc.start()

    def stop(self):
        Logger.info('RingLed: stop().')
        if board is None: return
        if self._proc is None: return
        self._stop.set()
        self._pixels.fill((0,0,0,0))
        self._pixels.show()

    def _flash(self):
        self._pixels.fill((255,255,255,255))
        self._pixels.show()
        time.sleep(0.5)
        self._pixels.fill((0,0,0,0))
        self._pixels.show()

    def _blink(self, color):
        self._stop.clear()
        while True:
            self._pixels.fill(color)
            self._pixels.show()
            time.sleep(0.1)
            self._pixels.fill((0,0,0,0))
            self._pixels.show()
            time.sleep(0.1)
            if self._stop.isSet(): return

    def _wheel(self, pos):
        if pos < 0 or pos > 255:
            r = g = b = 0
        elif pos < 85:
            r = int(pos * 3)
            g = int(255 - pos * 3)
            b = 0
        elif pos < 170:
            pos -= 85
            r = int(255 - pos * 3)
            g = 0
            b = int(pos * 3)
        else:
            pos -= 170
            r = 0
            g = int(pos * 3)
            b = int(255 - pos * 3)
        return (r, g, b) if self._order in (neopixel_spi.RGB, neopixel_spi.GRB) else (r, g, b, 0)

    def _countdown(self, time_seconds):
        self._stop.clear()
        raw_time_between_pixels = time_seconds / self._num_pixels
        time_between_pixels = raw_time_between_pixels# * 1.75

        self._pixels.fill((255,255,255,255))
        self._pixels.show()

        p1 = reversed(range(0, self._top_pixel+1))
        p2 = reversed(range(self._top_pixel, self._num_pixels))
        for i in [*p1, *p2]:
            self._pixels[i] = (0, 0, 0, 0)
            self._pixels.show()
            time.sleep(time_between_pixels)
            if self._stop.isSet(): return

    def _rainbow(self):
        self._stop.clear()
        while True:
            for j in range(255):
                for i in range(self._num_pixels):
                    pixel_index = (i * 256 // self._num_pixels) + j
                    self._pixels[i] = self._wheel(pixel_index & 255)
                self._pixels.show()
                time.sleep(0.001)
                if self._stop.isSet(): return
