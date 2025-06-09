from machine import Pin, ADC
from time import ticks_ms as millis
from time import sleep_ms as delay
from globals.constants import DT_INTERVAL

class CRS0304S:
    startTime  = 0
    wx, wy, wz = (0, 0, 0)

    def __init__(self):
        self.pin = ADC(Pin(28))

    def setup(self):
        self.startTime = millis()
        print('Sensor CRS0304S Ready')

    def update(self):
        self.wx = self.pin.read_u16()

    def handle(self):
        if millis() - self.startTime < DT_INTERVAL:
            return
        
        self.startTime = millis()
        self.update()
        print(self.get())

    def get(self):
        return {
            'wx': self.wx,
            'wy': self.wy,
            'wz': self.wz,
        }
