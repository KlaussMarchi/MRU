from Plotter.index import TimeGraph
from Utils.classes import AsyncThreading
from time import time, sleep
import numpy  as np
import pandas as pd
import os
from Protobuf.index import Protobuf

script_path = os.path.abspath(__file__)
base_dir    = os.path.dirname(script_path)
os.chdir(base_dir)


class Monitor:
    SAVE = True

    def __init__(self, targets=['yaw']):
        self.current = None
        self.values  = []
        self.targets = targets
        
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
        target = {key: data.get(key) for key in self.targets}
        print(data)
        
        if None in target.values():
            return

        self.current = target

    def get(self):
        if self.current is None:
            return

        if self.thread1.kb.is_pressed('r'):
            self.reset()

        if self.thread1.kb.is_pressed('a'):
            self.targets = ['ax', 'az']; self.reset()

        if self.thread1.kb.is_pressed('e'):
            self.targets = ['e']; self.reset()

        if self.thread1.kb.is_pressed('w'):
            self.targets = ['wx', 'wz']; self.reset()

        if self.thread1.kb.is_pressed('p'):
            self.targets = ['pitch']; self.reset()

        if self.thread1.kb.is_pressed('r'):
            self.targets = ['roll']; self.reset()

        if self.thread1.kb.is_pressed('y'):
            self.targets = ['yaw']; self.reset()

        if self.thread1.kb.is_pressed('1'):
            self.targets = ['q0', 'q1', 'q2', 'q3']; self.reset()
        
        return (time() - self.startTime, self.current)

    def reset(self):
        self.graph.reset()
        self.startTime = time()

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
        monitor.graph = graph
        graph.start()
    except Exception as error:
        print('error: ', error)
    finally:
        print('\nsalvando database')
        
        if monitor.SAVE:
            monitor.save()

