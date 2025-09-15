import math


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
            return Array([a + b for a,b in zip(self.data, other.data)])
        
        if isinstance(other, (int, float)):
            return Array([a + other for a in self.data])
        
        return None

    def __sub__(self, other):
        if isinstance(other, Array):
            return Array([a - b for a,b in zip(self.data, other.data)])
        
        if isinstance(other, (int, float)):
            return Array([a - other for a in self.data])
        
        return None
    
    def __rsub__(self, other):
        if isinstance(other, (int, float)):
            return Array([other - a for a in self.data])
        return None
    
    def __mul__(self, other):
        if isinstance(other, Array):
            return Array([a * b for a,b in zip(self.data, other.data)])
        
        if isinstance(other, (int, float)):
            return Array([a * other for a in self.data])
        
        return None
    
    def __truediv__(self, other):
        if isinstance(other, Array):
            return Array([a / b for a,b in zip(self.data, other.data)])
        
        elif isinstance(other, (int, float)):
            return Array([a / other for a in self.data])
        
        return None

    def __rtruediv__(self, other):
        if isinstance(other, (int, float)):
            return Array([other / a for a in self.data])
        
        return None

    def copy(self):
        return Array(self.data[:])

    def __repr__(self):
        return f"Array({self.data})"
    
    __radd__ = __add__
    __rmul__ = __mul__
