from IPython.display import display
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import control as ctl


class NumpyFilter:
    def see(self, yData, dt, limits=None, range=None, yLim=None):
        magnitude = np.fft.fft(yData).real
        frequency = np.fft.fftfreq(len(yData), dt)

        plt.figure(figsize=(6.65, 4))
        plt.plot(frequency, magnitude, label='frequencies')

        if limits is not None:
            low, high = limits
            if low is None: low = -high
            indices = np.where((frequency >= low) & (frequency <= high))
            plt.plot(frequency[indices], magnitude[indices], label='target')
        
        if range is not None:
            plt.xlim(range)
        
        if yLim is not None:
            plt.ylim(yLim)

        plt.grid(), plt.legend()
        plt.show()


class BandFilter:
    num = []
    den = []
    
    def __init__(self, dt=0.015, target=(0, 0)):
        s = ctl.TransferFunction.s
        low, high = target

        w1, w2 = 2*np.pi*low, 2*np.pi*high
        w0     = np.sqrt(w1 * w2)         # frequência central
        B      = w2 - w1                  # largura de banda
        Q      = w0 / B                   # fator de qualidade
        zeta   = 1 / (2 * Q)              # amortecimento

        C = (2*zeta*w0*s) / (s**2 + 2*zeta*w0*s + w0**2) 
        self.C = C

        C_z = ctl.c2d(C, dt, method='tustin')
        self.num, self.den = self.getFraction(C_z)
        self.Xn = np.zeros_like(self.num)
        self.Yn = np.zeros_like(self.den)
        self.dt = dt

    def getFraction(self, G_z):
        num, den = ctl.tfdata(G_z)
        num = np.squeeze(num)
        den = np.squeeze(den)

        num = num/den[0]
        den = den/den[0]

        if type(num) == np.float64:
            num = np.array([num])

        num = [float(val) for val in num]
        den = [float(val) for val in den]
        return (num, den) 

    def compute(self):
        out = 0.0

        for i in range(0, len(self.num)):
            out += self.Xn[i]*(self.num[i])
        
        for i in range(1, len(self.den)):
            out += self.Yn[i]*(-1*self.den[i])

        return out

    def update(self, input):
        for n in range(len(self.num)-1, 0, -1):
            self.Xn[n] = self.Xn[n-1]

        for n in range(len(self.den)-1, 0, -1):
            self.Yn[n] = self.Yn[n-1]
        
        self.Xn[0] = input
        self.Yn[0] = self.compute()
        return self.Yn[0]
    
    def apply(self, yData):
        N = len(yData)
        response = np.zeros(N)

        for x in range(N):
            value = yData[x]
            response[x] = self.update(value)

        return response
    
    def plot(self):
        ctl.bode(self.C, dB=True, Hz=False, deg=True, plot=True)
        display(self.C)


class LowBandFilter:
    num = []
    den = []
    
    def __init__(self, f_c=1.0, dt=0.005):
        w_c = 2*np.pi*f_c
        s = ctl.TransferFunction.s
        w_n  = w_c
        zeta = 0.7071067811865475

        C = w_n**2 / (s**2 + 2*zeta*w_n*s + w_n**2)
        self.C = C

        C_z = ctl.c2d(C, dt, method='tustin')
        self.num, self.den = self.getFraction(C_z)
        self.Xn = np.zeros_like(self.num)
        self.Yn = np.zeros_like(self.den)
        self.dt = dt

    def getFraction(self, G_z):
        num, den = ctl.tfdata(G_z)
        num = np.squeeze(num)
        den = np.squeeze(den)

        num = num/den[0]
        den = den/den[0]

        if type(num) == np.float64:
            num = np.array([num])

        num = [float(val) for val in num]
        den = [float(val) for val in den]
        return (num, den) 

    def compute(self):
        out = 0.0

        for i in range(0, len(self.num)):
            out += self.Xn[i]*(self.num[i])
        
        for i in range(1, len(self.den)):
            out += self.Yn[i]*(-1*self.den[i])

        return out

    def update(self, input):
        for n in range(len(self.num)-1, 0, -1):
            self.Xn[n] = self.Xn[n-1]

        for n in range(len(self.den)-1, 0, -1):
            self.Yn[n] = self.Yn[n-1]
        
        self.Xn[0] = input
        self.Yn[0] = self.compute()
        return self.Yn[0]
    
    def apply(self, yData):
        N = len(yData)
        response = np.zeros(N)

        for x in range(N):
            value = yData[x]
            response[x] = self.update(value)

        return response 
    
    def plot(self):
        ctl.bode(self.C, dB=True, Hz=False, deg=True, plot=True)
        display(self.C)


class Integral:
    Xn1 = 0
    Yn1 = 0

    def __init__(self, dt=0.05):
        self.dt = dt
        s = ctl.TransferFunction.s
        C_z = ctl.c2d(1/s, dt, method='tustin')
        
        num, den = ctl.tfdata(C_z)
        num = np.squeeze(num)
        den = np.squeeze(den)

        num = num/den[0]
        den = den/den[0]

        if type(num) == np.float64:
            num = np.array([num])

        num = [float(val) for val in num]
        den = [float(val) for val in den]
        out = ''
        
        for i in range(0, len(num)): 
            out += f'Xn{i}*({num[i]:.6f}) + '

        for i in range(1, len(den)): 
            out += f'Yn{i}*({-1*den[i]:.6f}) + '
        
        out = out.replace('Xn0', 'Xn')[:-3]
        print(out + ';')
        self.out = out
            
    def update(self, Xn):
        Xn1, Yn1 = self.Xn1, self.Yn1
        Yn = eval(self.out)
        self.Xn1 = Xn
        self.Yn1 = Yn
        return Yn
    
    def reset(self):
        self.Xn1 = 0
        self.Yn1 = 0