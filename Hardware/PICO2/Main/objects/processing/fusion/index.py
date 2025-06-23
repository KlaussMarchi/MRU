
def getMean(values):
    sum = 0.00
    n   = len(values)

    for i in range(n):
        sum += values[i]
    
    return sum/n

class Fusion:

    def __init__(self):
        pass

    def wx(self, *values):
        return getMean(values)
    
    def wy(self, *values):
        return getMean(values)
    
    def wz(self, *values):
        return getMean(values)
    
    def ax(self, *values):
        return getMean(values)
    
    def ay(self, *values):
        return getMean(values)
    
    def az(self, *values):
        return getMean(values)