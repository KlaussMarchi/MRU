from Device.index import Device
from Plotter.index import TimeGraph
from Utils.classes import AsyncThreading
from Utils.functions import sendEvent
from time import time, sleep
import numpy as np
import pandas as pd
import os, shutil

script_path = os.path.abspath(__file__)
base_dir = os.path.dirname(script_path)
os.chdir(base_dir)

def setFolder(folder):
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

class Monitor:
    def __init__(self, targets=['pitch']):
        self.current = None
        self.valuesK = []
        self.valuesM = []
        self.targets = targets
        self.startProg = None
        self.SAVE = True
        
    def setup(self):
        self.deviceM = Device(rate=9600)
        self.deviceK = Device(rate=19200)
        
        self.deviceM.port = '/dev/ttyACM0'
        self.deviceK.port = '/dev/ttyUSB0'

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
        
        self.deviceM.last = self.deviceM.getList()

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

        sendEvent('time:', passed, 'blue')
        sendEvent('kongsberg:', self.deviceK.last, 'green')
        sendEvent('measure:', self.deviceM.last, 'green')
        print()

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
            self.targets = ['pitch']; self.reset()

        if self.threadK.kb.is_pressed('w'):
            self.targets = ['wx']; self.reset()

        if self.threadK.kb.is_pressed('a'):
            self.targets = ['ax']; self.reset()

        if self.threadK.kb.is_pressed('o'):
            self.targets = ['q0']; self.reset()
                    
        return (time() - self.startTime, self.current)

    def reset(self):
        self.graph.need_reset = True
        self.startTime = time()

    def save(self, folder='output'):
        setFolder(os.path.join(folder, 'kongsberg'))
        setFolder(os.path.join(folder, 'measure'))

        keysK = set()
        for record in self.valuesK:
            keysK.update(record.keys())
        dataK = [{key: record.get(key, 0) for key in keysK} for record in self.valuesK]
        dfK = pd.DataFrame(dataK)
        dfK.to_csv(os.path.join(folder, 'kongsberg', 'data.csv'), index=False)
        
        keysM = set()
        for record in self.valuesM:
            keysM.update(record.keys())
        dataM = [{key: record.get(key, 0) for key in keysM} for record in self.valuesM]
        dfM = pd.DataFrame(dataM)
        dfM.to_csv(os.path.join(folder, 'measure', 'data.csv'), index=False)


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
        if monitor.SAVE:
            print('\nsalvando database')
            monitor.save()
