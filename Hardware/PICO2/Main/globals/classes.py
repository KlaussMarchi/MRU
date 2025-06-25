from utime import ticks_ms as millis
from globals.constants import DT_INTERVAL
import math


class Integral:
    def __init__(self):
        self.Xn1 = 0
        self.Yn1 = 0
        self.startTime = millis()

    def compute(self, Xn):
        if millis() - self.startTime < DT_INTERVAL:
            return self.Yn1 

        Yn = Xn*(0.025000) + self.Xn1*(0.025000) + self.Yn1*(1.000000)
        self.Xn1, self.Yn1 = Xn, Yn
        return Yn

class Derivative:
    def __init__(self):
        self.Xn1 = 0
        self.Yn1 = 0
        self.startTime = millis()

    def compute(self, Xn):
        if millis() - self.startTime < DT_INTERVAL:
            return self.Yn1 

        Yn = Xn*(20.000000) + self.Xn1*(-20.000000) + self.Yn1*(0.367879);
        self.Xn1, self.Yn1 = Xn, Yn
        return Yn

