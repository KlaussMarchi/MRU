from Device.index import Device
from Plotter.index import TimeGraph
from Processing.Filter.laplace import LaplaceFilter

from Utils.classes import AsyncThreading
from time import sleep, time
import numpy as np

device = Device(rate=115200)
device.connect()
device.stream(command=False)

startTime = time()
lastVal   = None
filter = LaplaceFilter(Ts=1.2, UP=0.05, dt=0.015)


def handleServer():
    global lastVal
    data = device.getJson()
    print(data)

    if data is None:
        return
    
    filter.update(data['wx'])

    lastVal = {
        'wx': data['wx'],
        'wx_filtered': filter.compute()
    }


def getData():
    global lastVal, startTime
    timePassed = (time() - startTime)

    if lastVal is None:
        return
    
    return (timePassed, lastVal)


if __name__ == '__main__':
    thread = AsyncThreading(handleServer, interval=0.001)

    graph = TimeGraph(callback=getData, xLim=[0, 6])
    graph.start()
