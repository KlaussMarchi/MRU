from utime import ticks_ms as millis
from globals.constants import DT_INTERVAL
import math


class LowPassFilter:
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

class ButterworthFilter:
    def __init__(self, f_c):
        self.f_c = f_c / 2.0  
        self.b, self.a = self.coefs()
        self.Xn1 = self.Xn2 = 0.0
        self.Yn1 = self.Yn2 = 0.0

    def reset(self):
        self.Xn1 = self.Xn2 = 0.0
        self.Yn1 = self.Yn2 = 0.0

    def coefs(self):
        wc = math.tan(math.pi * self.f_c)
        c2 = wc*wc
        norm = 1 + math.sqrt(2)*wc + c2

        b0 = c2/norm
        b1 = 2*c2/norm
        b2 = c2/norm

        a1 = 2*(c2 - 1)/norm
        a2 = (1 - math.sqrt(2)*wc + c2)/norm
        return [b0, b1, b2], [1.0, -a1, -a2]
    
    def compute(self, Xn):
        Yn = (
            self.b[0] * Xn +
            self.b[1] * self.Xn1 +
            self.b[2] * self.Xn2 +
            self.a[1] * self.Yn1 +
            self.a[2] * self.Yn2
        )
        self.Xn2, self.Xn1 = self.Xn1, Xn
        self.Yn2, self.Yn1 = self.Yn1, Yn
        return Yn
