from Plotter.index import TimeGraph
from Utils.classes import AsyncThreading
from time import time, sleep
import numpy as np
import pandas as pd
import os
from Protobuf.index import Protobuf

script_path = os.path.abspath(__file__)
base_dir = os.path.dirname(script_path)

os.chdir(base_dir)
TARGETS = ['ax']


class Monitor:
    SAVE = False

    def __init__(self):
        self.current = None
        self.values  = []
        
    def setup(self):
        self.protobuf = Protobuf()
        self.protobuf.setup()

        self.startTime = time()
        self.thread1   = AsyncThreading(self.protobuf.handle)

    def handle(self):
        data = self.protobuf.data

        if data is None:
            return
        
        self.update(data)
        self.values.append(data)

    def update(self, data):
        target = {key: data.get(key) for key in TARGETS}
        print(data)
        
        if None in target.values():
            return

        self.current = target

    def get(self):
        if self.current is None:
            return
        
        return (time() - self.startTime, self.current)

    def save(self):
        if not self.values:
            return
        
        keys = set()
        for record in self.values:
            keys.update(record.keys())
        
        data = [{key: record.get(key, 0) for key in keys} for record in self.values]
        df   = pd.DataFrame(data)
        
        if self.SAVE:
            df.to_csv('DataBase.csv', index=None)


if __name__ == '__main__':
    monitor = Monitor()
    monitor.setup()
    thread = AsyncThreading(monitor.handle, interval=0.001)

    try:
        graph = TimeGraph(callback=monitor.get, xLim=[0, 6])
        graph.start()
    except Exception as error:
        print('error: ', error)
    finally:
        print('\nsalvando database')
        
        if monitor.SAVE:
            monitor.save()

