from utime import ticks_ms as millis
from globals.constants import DT_INTERVAL, RAW_DEBUG
import math


class Omega:
    confidence = 0.1

    class Filter:
        def __init__(self):
            self.Xn1 = self.Xn2 = 0
            self.Yn1 = self.Yn2 = 0
            self.startTime = millis()

        def compute(self, Xn):
            if millis() - self.startTime < DT_INTERVAL:
                return self.Yn1
            
            self.startTime = millis()
            Yn = Xn*(0.003613) + self.Xn1*(0.007225) + self.Xn2*(0.003613) + self.Yn1*(1.822927) + self.Yn2*(-0.837377)
            self.Xn2, self.Xn1 = self.Xn1, Xn
            self.Yn2, self.Yn1 = self.Yn1, Yn
            return Yn
    
    def __init__(self):
        self.fx = self.Filter()
        self.fy = self.Filter()
        self.fz = self.Filter()
        self.x = self.y = self.z = 0

    def update(self, wx, wy, wz):
        self.x = (self.fx.compute(wx) if not RAW_DEBUG else wx) / 131.0 * math.pi / 180.0
        self.y = (self.fy.compute(wy) if not RAW_DEBUG else wy) / 131.0 * math.pi / 180.0
        self.z = (self.fz.compute(wz) if not RAW_DEBUG else wz) / 131.0 * math.pi / 180.0


class Acceleration:
    confidence = 0.1
    
    class Filter:
        def __init__(self):
            self.Xn1 = self.Xn2 = 0
            self.Yn1 = self.Yn2 = 0
            self.startTime = millis()

        def compute(self, Xn):
            if millis() - self.startTime < DT_INTERVAL:
                return self.Yn1
            
            self.startTime = millis()
            Yn = Xn*(0.192252) + self.Xn1*(0.000000) + self.Xn2*(-0.192252) + self.Yn1*(1.605324) + self.Yn2*(-0.615497)
            self.Xn2, self.Xn1 = self.Xn1, Xn
            self.Yn2, self.Yn1 = self.Yn1, Yn
            return Yn
    
    def __init__(self):
        self.fx = self.Filter()
        self.fy = self.Filter()
        self.fz = self.Filter()
        self.x = self.y = self.z = 0

    def update(self, ax, ay, az):
        self.x = (self.fx.compute(ax) if not RAW_DEBUG else ax) / 16384.0 * 9.80665
        self.y = (self.fy.compute(ay) if not RAW_DEBUG else ay) / 16384.0 * 9.80665
        self.z = (self.fz.compute(az) if not RAW_DEBUG else az) / 16384.0 * 9.80665
