from Device.index import Device
from Server.index import Server
from Plotter.index import TimeGraph

from Utils.classes import AsyncThreading
from time import sleep, time
import numpy as np

server = Server()
device = Device(rate=115200)
device.connect()
device.startStream()

startTime = time()
lastVal   = None


def handleServer():
    global lastVal
    data = device.getJson()
    #data  = server.getData()
    print(data)

    if data is None:
        return

    lastVal = {
        'ax': data['ax'],
        'ay': data['ay'],
    }


def getData():
    global lastVal, startTime
    timePassed = (time() - startTime)

    if lastVal is None:
        return
    
    return (timePassed, lastVal)


if __name__ == '__main__':
    thread = AsyncThreading(handleServer, interval=0.05)

    graph = TimeGraph(callback=getData, xLim=[0, 6])
    graph.start()
