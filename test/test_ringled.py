import sys
import time

sys.path.append('..')
from libs.ringled import RingLed

leds = RingLed()

print('Start countdown')
leds.start_countdown(5)
time.sleep(6)

print('Start rainbow')
leds.start_rainbow()
time.sleep(5)
leds.stop()

print('Start flash')
leds.flash()
time.sleep(5)

print('Start blink')
leds.blink((255,0,0,255))
time.sleep(5)

print('Stop')
leds.stop()
