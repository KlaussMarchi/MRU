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

class Array:
    def __init__(self, data):
        self.data   = data
        self.length = len(self.data)

    def zeros(self, size):
        self.length = size
        self.data   = [0] * size

    def get(self, index):
        return self.data[index]
    
    def set(self, data):
        self.data = data
        self.length = len(data)

    def change(self, index, value):
        self.data[index] = value

    def mean(self):
        return sum(self.data) / self.length

    def std(self, mean=None):
        if mean is None:
            mean = self.mean()
        return math.sqrt(sum((x - mean)**2 for x in self.data) / self.length)

    def sum(self):
        return sum(self.data)

    def norm(self):
        A = math.sqrt(sum(x ** 2 for x in self.data))
        if A == 0:
            return self.copy()
        return Array([val / A for val in self.data])
    
    def __add__(self, other):
        if isinstance(other, Array):
            return Array([a + b for a, b in zip(self.data, other.data)])
        elif isinstance(other, (int, float)):
            return Array([a + other for a in self.data])
        return NotImplemented

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return Array([a * other for a in self.data])
        return NotImplemented
    
    def copy(self):
        return Array(self.data[:])

    def __repr__(self):
        return f"Array({self.data})"
    
    __rmul__ = __mul__
