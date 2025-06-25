from Device.index import device
from Plotter.index import TimeGraph
from Processing.Filter.laplace import LaplaceFilter
from Utils.classes import AsyncThreading
from time import time
import pandas as pd

import os
script_path = os.path.abspath(__file__)
base_dir = os.path.dirname(script_path)
os.chdir(base_dir)

device.connect()
device.stream(command=False)

startTime = time()
lastVal = None
filter  = LaplaceFilter(Ts=1.2, UP=0.05, dt=0.015)
df_list = []


def handleServer():
    global lastVal
    data = device.getJson()
    print(data)

    if data is None:
        return
    
    lastVal = {'wx': data['wx'], 'wy': data['wy'], }
    df_list.append(data)


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
        pass
    finally:
        df = pd.DataFrame(df_list)
        df.to_csv('DataBase.csv', index=None)
