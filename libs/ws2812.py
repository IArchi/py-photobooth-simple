import numpy as np

class WS2812:
    def __init__(self, spi, nb_leds=12):
        self._spi = spi
        self._nb_leds = nb_leds
        self._pixels = [[0,0,0]]*self._nb_leds
    
    def write(self, rgb):
        self._pixels = rgb
        grb = [[arr[1], arr[0], arr[2]] for arr in rgb]
        d = np.array(grb).ravel()
        tx = np.zeros(len(d)*4, dtype=np.uint8)
        for ibit in range(4):
            tx[3-ibit::4]=((d>>(2*ibit+1))&1)*0x60 + ((d>>(2*ibit+0))&1)*0x06 + 0x88
        self._spi.xfer(tx.tolist(), int(4/1.25e-6))

    def fill(self, color):
        self.write([color]*self._nb_leds)

    def set(self, pixel, color):
        self._pixels[pixel] = color
        self.write(self._pixels)

    def get(self, pixel=-1):
        if pixel < 0: return self._pixels
        return self._pixels(pixel)
