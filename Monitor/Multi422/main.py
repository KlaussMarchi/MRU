from Device.index import Device
from Plotter.index import TimeGraph
from Utils.classes import AsyncThreading
from time import time, sleep
import numpy as np
import pandas as pd
import os

script_path = os.path.abspath(__file__)
base_dir = os.path.dirname(script_path)
os.chdir(base_dir)

class Monitor:
    def __init__(self, targets=['pitch', 'roll', 'yaw']):
        self.current = None
        self.valuesK = []
        self.valuesM = []
        self.targets = targets
        self.startProg = None
        self.SAVE = True
        
    def setup(self):
        self.deviceK = Device(rate=19200)
        self.deviceM = Device(rate=9600)

        self.deviceK.connect()
        self.deviceM.connect()

        self.startTime = time()
        self.threadK = AsyncThreading(self.handleKongsberg)
        self.threadM = AsyncThreading(self.handleMeasure)

    def handleKongsberg(self):
        if not self.deviceK.available():
            return
        
        self.deviceK.last = self.deviceK.getNMEA()

    def handleMeasure(self):
        if not self.deviceM.available():
            return
        
        self.deviceM.last = self.deviceM.getJson()

    def handle(self):
        if self.deviceK.last is None or self.deviceM.last is None:
            return
        
        if self.startProg is None:
            self.startProg = time()

        passed = time() - self.startProg
        self.deviceK.last['time'] = passed
        self.deviceM.last['time'] = passed
        
        self.current = {}
        for key in self.targets:
            self.current[f'{key}_K'] = self.deviceK.last.get(key)
            self.current[f'{key}_M'] = self.deviceM.last.get(key)

        self.valuesK.append(self.deviceK.last)
        self.valuesM.append(self.deviceM.last)
        self.deviceK.last = None
        self.deviceM.last = None

    def get(self):
        if self.current is None:
            return

        if self.threadK.kb.is_pressed('p'):
            self.targets = ['pitch']; self.reset()

        if self.threadK.kb.is_pressed('r'):
            self.targets = ['roll']; self.reset()

        if self.threadK.kb.is_pressed('y'):
            self.targets = ['yaw']; self.reset()

        if self.threadK.kb.is_pressed('k'):
            self.targets = ['pitch', 'roll', 'yaw']; self.reset()

        if self.threadK.kb.is_pressed('w'):
            self.targets = ['wx', 'wy', 'wz']; self.reset()

        if self.threadK.kb.is_pressed('a'):
            self.targets = ['ax', 'ay', 'az']; self.reset()

        if self.threadK.kb.is_pressed('o'):
            self.targets = ['q0', 'q1', 'q2', 'q3']; self.reset()
                    
        return (time() - self.startTime, self.current)

    def reset(self):
        self.graph.need_reset = True
        self.startTime = time()

    def save(self):
        if getattr(self, 'SAVE', False) is False:
            return

        if self.valuesK:
            keysK = set()
            for record in self.valuesK:
                keysK.update(record.keys())
            dataK = [{key: record.get(key, 0) for key in keysK} for record in self.valuesK]
            dfK = pd.DataFrame(dataK)
            dfK.to_csv('kongsberg.csv', index=False)
            
        if self.valuesM:
            keysM = set()
            for record in self.valuesM:
                keysM.update(record.keys())
            dataM = [{key: record.get(key, 0) for key in keysM} for record in self.valuesM]
            dfM = pd.DataFrame(dataM)
            dfM.to_csv('measure.csv', index=False)


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
