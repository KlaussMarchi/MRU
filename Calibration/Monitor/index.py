from Device.index import Device
from Plotter.index import TimeGraph
from Utils.classes import AsyncThreading
from Utils.functions import sendEvent
from time import time, sleep
import numpy as np
import pandas as pd
import os, shutil, json

script_path = os.path.abspath(__file__)
base_dir = os.path.dirname(script_path)
os.chdir(base_dir)

def setFolder(folder):
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

class Monitor:
    def __init__(self, targets=['pitchM', 'rollK']):
        self.current = None
        self.valuesK = []
        self.valuesM = []
        self.targets = targets
        self.startProg = None
        self.SAVE = True
        self.stats = {}
        
    def setup(self):
        self.deviceM = Device(rate=9600)
        self.deviceK = Device(rate=19200)
        
        self.deviceM.port = '/dev/ttyACM0'
        self.deviceK.port = '/dev/ttyUSB0'

        self.deviceM.connect()
        self.deviceK.connect()

        self.startTime = time()

        sleep(2.00)
        self.deviceM.send('$stream_start!')
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
        kongsberg_working = self.deviceK.last is not None
        measure_working   = self.deviceM.last is not None

        if not kongsberg_working or not measure_working:
            return
        
        if self.startProg is None:
            self.startProg = time()

        passed = time() - self.startProg
        sendEvent('measure', ('working'   if measure_working else 'failed')   + f': {str(self.deviceM.last)[:100]}',   'green' if measure_working else 'red')
        sendEvent('kongsberg', ('working' if kongsberg_working else 'failed') + f': {str(self.deviceK.last)[:100]}', 'green' if kongsberg_working else 'red')
        sendEvent('time', passed, 'blue')
        print()
        
        if self.deviceK.last is not None:
            self.deviceK.last['time'] = passed

        if self.deviceM.last is not None:
            self.deviceM.last['time'] = passed
            
        if self.current is None:
            self.current = {target: 0.5 for target in self.targets}
            
        for target in self.targets:
            val = None
            if target.endswith('K') and self.deviceK.last is not None:
                val = self.deviceK.last.get(target[:-1])

            elif target.endswith('M') and self.deviceM.last is not None:
                val = self.deviceM.last.get(target[:-1])
                
            if val is not None:
                if target not in self.stats:
                    self.stats[target] = {'min': val, 'max': val}
                
                self.stats[target]['min'] = min(self.stats[target]['min'], val)
                self.stats[target]['max'] = max(self.stats[target]['max'], val)
                
                vmin = self.stats[target]['min']
                vmax = self.stats[target]['max']
                
                if vmax - vmin == 0:
                    norm_val = 0.5
                else:
                    norm_val = (val - vmin) / (vmax - vmin)
                    
                self.current[target] = norm_val

        if self.deviceK.last is not None:
            #sendEvent('kongsberg:', self.deviceK.last, 'green')
            self.valuesK.append(self.deviceK.last)
            self.deviceK.last = None
            
        if self.deviceM.last is not None:
            #sendEvent('measure:', self.deviceM.last, 'green')
            self.valuesM.append(self.deviceM.last)
            self.deviceM.last = None

    def get(self):
        if self.current is None:
            return

        if self.threadK.kb.is_pressed('p'):
            self.targets = ['pitchM', 'rollK']; self.reset()

        if self.threadK.kb.is_pressed('r'):
            self.targets = ['eM', 'rollK']; self.reset()

        if self.threadK.kb.is_pressed('y'):
            self.targets = ['yawM', 'yawK']; self.reset()

        if self.threadK.kb.is_pressed('e'):
            self.targets = ['wxK', 'eM']; self.reset()

        if self.threadK.kb.is_pressed('k'):
            self.targets = ['pitchM', 'pitchK']; self.reset()

        if self.threadK.kb.is_pressed('w'):
            self.targets = ['wxM', 'wzK']; self.reset()

        if self.threadK.kb.is_pressed('a'):
            self.targets = ['axM', 'axK']; self.reset()

        if self.threadK.kb.is_pressed('o'):
            self.targets = ['q0M', 'q0K']; self.reset()
                    
        return (time() - self.startTime, self.current)

    def reset(self):
        self.stats = {} # Limpa os stats para re-normalizar com a nova variavel
        self.graph.need_reset = True
        self.startTime = time()
        self.current = None

    def save(self, folder='output'):
        setFolder(os.path.join(folder, 'reference'))
        setFolder(os.path.join(folder, 'target'))
        
        with open(os.path.join(folder, 'info.json'), 'w'    ) as file:
            file.write(json.dumps({
                "description": "Reference is MRU and target is Kongsberg",
                "limits": {
                    "dynamic": [15, 600],
                    "static":  [700, 999999999]
                }
            }, indent=4))

        keysK = set()
        for record in self.valuesK:
            keysK.update(record.keys())
        dataK = [{key: record.get(key, 0) for key in keysK} for record in self.valuesK]
        dfK = pd.DataFrame(dataK)
        dfK.to_csv(os.path.join(folder, 'reference', 'data.csv'), index=False)
        
        keysM = set()
        for record in self.valuesM:
            keysM.update(record.keys())
        dataM = [{key: record.get(key, 0) for key in keysM} for record in self.valuesM]
        dfM = pd.DataFrame(dataM)
        dfM.to_csv(os.path.join(folder, 'target', 'data.csv'), index=False)


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
