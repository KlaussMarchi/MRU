import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
from time import time
import threading
from Serial.index import Device

class TimeGraph:
    startTime = time()

    def __init__(self, xLim=[0, 5], interval=0.1, callback=None):
        self.xLim = xLim
        self.interval = int(interval * 1000)
        self.size = len(np.arange(xLim[0], xLim[1], interval))
        self.x = 0
        self.y = 0
        self.xData = [self.x]
        self.yData = [self.y]
        self.callback = callback
    
    def handleThread(self):
        print('starting thread')

        while True:
            data = self.callback()
            print('received: ', data)

            if data is None:
                continue
            
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

    def start(self):
        thread = threading.Thread(target=self.handleThread)
        thread.daemon = True
        thread.start()

        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.line, = self.ax.plot(self.xData, self.yData, color='blue')
        self.ax.set_title('Plotter Serial')
        self.ax.set_xlabel('time')
        self.ax.set_ylabel('response')
        self.ax.grid()
        ani = FuncAnimation(self.fig, self.update, interval=self.interval, blit=False, cache_frame_data=False)
        plt.show()


startTime = time()

def getValue():
    t = time() - startTime
    y = np.sin(0.5*t)
    return t, y

if __name__ == "__main__":
    #arduino = Device()
    #arduino.connect()
    #arduino.startStream()

    graph = TimeGraph(xLim=[0, 15], interval=0.001, callback=getValue)
    graph.start()
