from utime import ticks_ms as millis
from globals.constants import DT_INTERVAL, RAW_DEBUG
from objects.processing.filters.index import ButterworthFilter
import math


class Omega:
    confidence = 0.1

    def __init__(self):
        self.fx = ButterworthFilter(f_c=0.20)
        self.fy = ButterworthFilter(f_c=0.20)
        self.fz = ButterworthFilter(f_c=0.20)
        self.x = self.y = self.z = 0
    
    def update(self, wx, wy, wz):
        self.x = (self.fx.compute(wx) if not RAW_DEBUG else wx) / 131.0 * math.pi / 180.0
        self.y = (self.fy.compute(wy) if not RAW_DEBUG else wy) / 131.0 * math.pi / 180.0
        self.z = (self.fz.compute(wz) if not RAW_DEBUG else wz) / 131.0 * math.pi / 180.0


class Acceleration:
    confidence = 0.1
    
    def __init__(self):
        self.fx = ButterworthFilter(f_c=0.15)
        self.fy = ButterworthFilter(f_c=0.15)
        self.fz = ButterworthFilter(f_c=0.15)
        self.x = self.y = self.z = 0

    def update(self, ax, ay, az):
        self.x = (self.fx.compute(ax) if not RAW_DEBUG else ax) / 16384.0 * 9.80665
        self.y = (self.fy.compute(ay) if not RAW_DEBUG else ay) / 16384.0 * 9.80665
        self.z = (self.fz.compute(az) if not RAW_DEBUG else az) / 16384.0 * 9.80665
