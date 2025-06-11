from machine import Pin, ADC
from globals.constants import DT_INTERVAL
from objects.sensors.CRS0304S.analysis import Omega, Acceleration



class CRS0304S:
    def __init__(self):
        self.pin = ADC(Pin(28))
        self.a = Acceleration()
        self.w = Omega()

    def setup(self):
        print('Sensor CRS0304S Ready')

    def update(self):
        wx = self.pin.read_u16()
        wy = self.pin.read_u16()
        wz = self.pin.read_u16()
        ax = self.pin.read_u16()
        ay = self.pin.read_u16()
        az = self.pin.read_u16()
        self.a.update(ax, ay, az)
        self.w.update(wx, wy, wz)

        
