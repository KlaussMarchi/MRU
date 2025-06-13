from time import ticks_ms as millis
from globals.constants import DT_INTERVAL


class Omega:
    class Filter:
        Xn1 = Xn2 = 0
        Yn1 = Yn2 = 0

        def __init__(self):
            self.startTime = millis()

        def compute(self, Xn):
            if millis() - self.startTime < DT_INTERVAL:
                return self.Yn1
            
            self.startTime = millis()
            Yn = Xn*(0.133618) + self.Xn1*(-0.000000) + self.Xn2*(-0.133618) + self.Yn1*(1.669797) + self.Yn2*(-0.732763)
            self.Xn2, self.Xn1 = self.Xn1, Xn
            self.Yn2, self.Yn1 = self.Yn1, Yn
            return Yn
    
    def __init__(self):
        self.fx = self.Filter()
        self.fy = self.Filter()
        self.fz = self.Filter()
        self.x = self.y = self.z = 0

    def update(self, wx, wy, wz):
        self.x = self.fx.compute(wx)
        self.y = self.fy.compute(wy)
        self.z = self.fz.compute(wz)

    def get(self):
        return [self.x, self.y, self.z]


class Acceleration:
    class Filter:
        Xn1 = Xn2 = 0
        Yn1 = Yn2 = 0

        def __init__(self):
            self.startTime = millis()

        def compute(self, Xn):
            if millis() - self.startTime < DT_INTERVAL:
                return self.Yn1
            
            self.startTime = millis()
            Yn = Xn*(0.133618) + self.Xn1*(-0.000000) + self.Xn2*(-0.133618) + self.Yn1*(1.669797) + self.Yn2*(-0.732763)
            self.Xn2, self.Xn1 = self.Xn1, Xn
            self.Yn2, self.Yn1 = self.Yn1, Yn
            return Yn
    
    def __init__(self):
        self.fx = self.Filter()
        self.fy = self.Filter()
        self.fz = self.Filter()
        self.x = self.y = self.z = 0

    def update(self, ax, ay, az):
        self.x = self.fx.compute(ax)
        self.y = self.fy.compute(ay)
        self.z = self.fz.compute(az)

    def get(self):
        return [self.x, self.y, self.z]
