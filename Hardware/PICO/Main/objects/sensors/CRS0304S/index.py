from machine import Pin, ADC
from objects.sensors.CRS0304S.analysis import Omega, Acceleration



class CRS0304S:
    def __init__(self, pin):
        self.pin = Pin(pin)
        self.a = Acceleration()
        self.w = Omega()

    def setup(self):
        self.pin = ADC(self.pin)
        print('Sensor Ready')

    def update(self):
        wx = self.pin.read_u16()
        wy = self.pin.read_u16()
        wz = self.pin.read_u16()
        ax = self.pin.read_u16()
        ay = self.pin.read_u16()
        az = self.pin.read_u16()
        self.a.update(ax, ay, az)
        self.w.update(wx, wy, wz)
    
    def get(self, update=False):
        if update:
            self.update()

        return {
            'wx': self.w.x, 
            'wy': self.w.y, 
            'wz': self.w.z, 
            'ax': self.a.x, 
            'ay': self.a.y, 
            'az': self.a.z, 
        }

        
