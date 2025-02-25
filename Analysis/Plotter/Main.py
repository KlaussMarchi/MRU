import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
from time import time, sleep
import threading
from Serial.index import Device
from Utils.functions import sendEvent
from Utils.classes import AsyncThreading
from Filter.laplace import LaplaceFilter

class TimeGraph:
    startTime = time()

    def __init__(self, xLim=[0, 5], interval=0.1, callback=None):
        self.xLim = xLim
        self.interval = int(interval * 1000)
        self.size     = len(np.arange(xLim[0], xLim[1], interval))
        self.x = 0
        self.y = 0
        self.xData = [self.x]
        self.yData = [self.y]
        self.callback = callback

    def start(self):
        self.thread = AsyncThreading(self.handleThread)
        sendEvent('event', 'thread started')

        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.line, = self.ax.plot(self.xData, self.yData, color='blue')
        self.ax.set_title('Plotter Serial')
        self.ax.set_xlabel('time')
        self.ax.set_ylabel('response')
        self.ax.grid()
        ani = FuncAnimation(self.fig, self.update, interval=self.interval, blit=False, cache_frame_data=False)
        plt.show()
    
    def handleThread(self):
        data = self.callback()

        if data is None:
            return
        
        if len(data) == 2:
            self.x, self.y = data
        
    def update(self, frame):
        self.xData.append(self.x)
        self.yData.append(self.y)
        
        self.xData = self.xData[-self.size:]
        self.yData = self.yData[-self.size:]

        if self.xData[-1] > self.xLim[1]:
            self.xLim[0] += self.xData[-1] - self.xLim[1]
            self.xLim[1] = self.xData[-1]

        minY = min(self.yData)
        maxY = max(self.yData)
        minY = minY * 0.95 if minY > 0 else minY * 1.05
        maxY = maxY * 1.05 if maxY > 0 else maxY * 0.95

        self.ax.set_xlim(self.xLim[0], self.xLim[1])
        self.ax.set_ylim(minY, maxY)
        self.line.set_data(self.xData, self.yData)
        return (self.line, )


def getTarget():
    global arduino, laplpace
    data = arduino.data
    
    if data is None:
        return None
    
    t = data.get('t')
    y = data.get('wz')

    if t is None or y is None:
        return None

    filtered = laplace.update(y)
    return t, filtered
    


if __name__ == "__main__":
    arduino = Device()
    arduino.connect()
    arduino.startStream()
    laplace = LaplaceFilter(Ts=1.5, UP=0.1, T=0.050)

    graph = TimeGraph(xLim=[0, 15], interval=0.05, callback=getTarget)
    graph.start()
