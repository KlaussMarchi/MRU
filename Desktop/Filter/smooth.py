import numpy as np

class Smooth:
    def __init__(self, size=20):
        self.size  = size
        self.array = np.zeros(size)
        self.sum   = 0.0
        self.index = 0

    def update(self, value):
        i = self.index
        self.sum = self.sum - self.array[i]
        self.array[i] = value

        self.sum = self.sum + self.array[i]
        i =  (i + 1) if (i + 1 < self.size) else 0;

        self.index = i
        return (self.sum / self.size);

