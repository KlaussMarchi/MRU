from Device.index import Device
from Plotter.index import TimeGraph
from Processing.Filter.laplace import LaplaceFilter
import pandas as pd

from Utils.classes import AsyncThreading
from time import sleep, time
import numpy as np

device = Device(rate=115200)
device.connect()
device.stream(command=False)

startTime = time()
lastVal = None
filter  = LaplaceFilter(Ts=1.2, UP=0.05, dt=0.015)
df = []


def handleServer():
    global lastVal
    data = device.getJson()
    print(data)

    if data is None:
        return
    
    lastVal = {
        'wx_sensor1': data['s1']['wx'],
        'wx_sensor2': data['s1']['wx']
    }

    df.append(lastVal)


def getData():
    global lastVal, startTime
    timePassed = (time() - startTime)

    if lastVal is None:
        return
    
    return (timePassed, lastVal)


if __name__ == '__main__':
    thread = AsyncThreading(handleServer, interval=0.001)

    try:
        graph = TimeGraph(callback=getData, xLim=[0, 6])
        graph.start()
    except:
        df = pd.DataFrame(df)
        df.to_csv('DataBase.csv', index=None)