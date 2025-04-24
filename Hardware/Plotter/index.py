import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
from Utils.functions import sendEvent
from Utils.classes import AsyncThreading
from time import time as getTime
from time import sleep as delay

class TimeGraph:
    startTime = getTime()

    def __init__(self, xLim=[0, 5], interval=0.001, callback=None):
        self.xLim = xLim
        self.interval = int(interval * 1000) 
        self.size = len(np.arange(xLim[0], xLim[1], interval))
        self.t = 0
        self.newData = []   # [('y1', [1, 2, 3]), ('y2', [4, 5, 6])]...
        self.time  = []     # VETOR DE TEMPO
        self.data  = {}     # {'y1': [1, 2, 3], 'y2': [4, 5, 6], ...}
        self.lines = {}     # OBJETOS DE CADA LINHA
        self.callback = callback
        self.thread   = None

    def start(self):
        self.thread = AsyncThreading(self.handleThread)
        sendEvent('event', 'thread started')

        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.ax.set_title('Plotter Serial')
        self.ax.set_xlabel('time')
        self.ax.set_ylabel('response')
        self.ax.grid()
        self.ani = FuncAnimation(self.fig, self.update, interval=self.interval, blit=False, cache_frame_data=False)
        plt.show()

    def handleThread(self):
        data = self.callback()

        if data is None:
            return

        if len(data) != 2:
            return
        
        self.t, self.newData = data

    def update(self, frame):
        if not self.newData:
            return []

        self.time.append(self.t)
        self.time = self.time[-self.size:]

        for (label, value) in self.newData.items():
            if label not in self.data:
                self.data[label] = []
            
            self.data[label].append(value)
            self.data[label] = self.data[label][-self.size:] 

        self.adjustXLim()
        self.adjustYLim()
        lines = self.updateLines()
        return lines

    def adjustXLim(self):
        if len(self.time) == 0:
            return

        if self.time[-1] > self.xLim[1]:
            desloc = (self.time[-1] - self.xLim[1])
            self.xLim[0] += desloc
            self.xLim[1] += desloc

        self.ax.set_xlim(self.xLim[0], self.xLim[1])

    def adjustYLim(self):
        allValues = []

        for label in self.data:
            allValues.extend(self.data[label])

        if len(allValues) == 0:
            return

        minY = min(allValues)
        maxY = max(allValues)
        minY = minY * 0.95 if minY >= 0 else minY * 1.05
        maxY = maxY * 1.05 if maxY >= 0 else maxY * 0.95
        self.ax.set_ylim(minY, maxY)

    def updateLines(self):
        updated_lines = []

        for label, seriesData in self.data.items():
            if label not in self.lines:
                lineObj, = self.ax.plot([], [], label=label)
                self.lines[label] = lineObj
                self.ax.legend()

            lineObj = self.lines[label]
            lineObj.set_data(self.time, seriesData)
            updated_lines.append(lineObj)

        return updated_lines
