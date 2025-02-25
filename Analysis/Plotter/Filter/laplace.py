import numpy as np
import control as ctl
from time import time


class LaplaceFilter:
    output = None

    def __init__(self, Ts=0.2, UP=0.030, T=0.1):
        zeta = -np.log(UP)/np.sqrt(np.pi**2 + np.log(UP)**2)
        Wn = 4/(zeta*Ts)

        s = ctl.TransferFunction.s
        C = Wn**2/(s**2 + 2*zeta*Wn*s + Wn**2)
        print('TF: ', C)

        C_z = ctl.c2d(C, T, method='tustin')
        self.output = self.getFrac(C_z)
        self.xSize  = len(self.output[0])
        self.ySize  = len(self.output[1])
        self.Xn = np.zeros(self.xSize)
        self.Yn = np.zeros(self.ySize)
        
        self.T  = T
        self.startTime = time()

    def getFrac(self, G_z):
        num, den = ctl.tfdata(G_z)
        num = np.squeeze(num)
        den = np.squeeze(den)

        num = num/den[0]
        den = den/den[0]

        if type(num) == np.float64:
            num = np.array([num])

        return list(num), list(den)

    def compute(self):
        num, den = self.output
        out = 0.0

        for i in range(0, len(num)):
            out += self.Xn[i]*(num[i])
        
        for i in range(1, len(den)):
            out += self.Yn[i]*(-1*den[i])

        return out

    def update(self, input):
        if time() - self.startTime < self.T:
            return self.Yn[0]
        
        self.startTime = time()

        for n in range(self.xSize-1, 0, -1):
            self.Xn[n] = self.Xn[n-1]

        for n in range(self.ySize-1, 0, -1):
            self.Yn[n] = self.Yn[n-1]
        
        self.Xn[0] = input
        self.Yn[0] = self.compute()
        return self.Yn[0]


#l = LaplaceFilter(Ts=8, UP=0.001)
#import matplotlib.pyplot as plt
#tData = np.linspace(0, 10, 1000)
#xData = np.random.uniform(-1, 1, 1000)
#yData = [l.update(x) for x in xData]
#plt.plot(tData, xData)
#plt.plot(tData, yData)
#plt.show()
