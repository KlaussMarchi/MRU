from Device.index import Device
from Plotter.index import TimeGraph
from Utils.classes import AsyncThreading, KeyboardListener
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
    INDEPENDENT = False
    NORMALIZE   = False

    def __init__(self, targets=['pitchM']):
        self.kb = KeyboardListener()
        self.kb.start()
        self.current = None
        self.valuesK = []
        self.valuesM = []
        self.valuesP = []
        self.targets = targets
        self.startProg = None
        self.SAVE = True
        self.stats = {}
        
    def setup(self):
        self.deviceM = Device(rate=9600)
        self.deviceK = Device(rate=19200)
        self.deviceP = Device(rate=9600)
        
        self.deviceM.port = '/dev/ttyACM0'
        self.deviceP.port = '/dev/ttyUSB0'
        self.deviceK.port = '/dev/ttyUSB1'

        self.deviceM.connect()
        self.deviceP.connect()
        #self.deviceK.connect()

        self.startTime = time()

        sleep(2.00)
        self.deviceM.send('$stream_start!')
        self.deviceP.send('$stream_start!')
        self.threadM = AsyncThreading(self.handleMeasure)
        self.threadP = AsyncThreading(self.handlePlate)
        #self.threadK = AsyncThreading(self.handleKongsberg)

    def handleMeasure(self):
        if not self.deviceM.available():
            return
        
        self.deviceM.last = self.deviceM.getList()

    def handlePlate(self):
        if not self.deviceP.available():
            return
        
        self.deviceP.last = self.deviceP.getList()

    def handleKongsberg(self):
        if not self.deviceK.available():
            return
        
        self.deviceK.last = self.deviceK.getNMEA()

    def handle(self):
        kongsberg_working = self.deviceK.last is not None
        measure_working   = self.deviceM.last is not None
        plate_working     = self.deviceP.last is not None

        if self.INDEPENDENT and (not measure_working and not plate_working):
            return

        if not self.INDEPENDENT and (not measure_working or not plate_working):
            return
        
        if self.startProg is None:
            self.startProg = time()

        passed = time() - self.startProg
        sendEvent('measure', ('working'   if measure_working else 'failed')   + f': {str(self.deviceM.last)[:100]}',   'green' if measure_working else 'red')
        sendEvent('kongsberg', ('working' if kongsberg_working else 'failed') + f': {str(self.deviceK.last)[:100]}', 'green' if kongsberg_working else 'red')
        sendEvent('plate', ('working' if plate_working else 'failed') + f': {str(self.deviceP.last)[:100]}', 'green' if plate_working else 'red')
        sendEvent('time', passed, 'blue')
        print()
        
        if kongsberg_working:
            self.deviceK.last['time'] = passed

        if measure_working:
            self.deviceM.last['time'] = passed

        if plate_working:
            self.deviceP.last['time'] = passed
            
        if self.current is None:
            self.current = {target: 0.5 for target in self.targets}
            
        for target in self.targets:
            val = None
            if target.endswith('K') and kongsberg_working:
                val = self.deviceK.last.get(target[:-1])
            elif target.endswith('M') and measure_working:
                val = self.deviceM.last.get(target[:-1])
            elif target.endswith('P') and plate_working:
                val = self.deviceP.last.get(target[:-1])
                
            if val is not None:
                if target not in self.stats:
                    self.stats[target] = {'min': val, 'max': val}
                
                self.stats[target]['min'] = min(self.stats[target]['min'], val)
                self.stats[target]['max'] = max(self.stats[target]['max'], val)
                
                vmin = self.stats[target]['min']
                vmax = self.stats[target]['max']
                
                if self.NORMALIZE:
                    if vmax - vmin == 0:
                        norm_val = 0.5
                    else:
                        norm_val = (val - vmin) / (vmax - vmin)
                        
                    self.current[target] = norm_val
                else:
                    self.current[target] = val

        if kongsberg_working:
            self.valuesK.append(self.deviceK.last)
            self.deviceK.last = None
            
        if measure_working:
            self.valuesM.append(self.deviceM.last)
            self.deviceM.last = None

        if plate_working:
            self.valuesP.append(self.deviceP.last)
            self.deviceP.last = None

    def get(self):
        if self.current is None:
            return

        if self.kb.is_pressed('n'):
            self.NORMALIZE = not self.NORMALIZE
            self.reset()
            print(f"\n[INFO] Normalization: {'ON' if self.NORMALIZE else 'OFF'}")

        if self.kb.is_pressed('p'):
            self.targets = ['pitchM']; self.reset()

        if self.kb.is_pressed('r'):
            self.targets = ['rollM']; self.reset()

        if self.kb.is_pressed('y'):
            self.targets = ['yawM']; self.reset()

        if self.kb.is_pressed('h'):
            self.targets = ['hM']; self.reset()

        if self.kb.is_pressed('k'):
            self.targets = ['pitchM']; self.reset()

        if self.kb.is_pressed('w'):
            self.targets = ['wxM']; self.reset()

        if self.kb.is_pressed('a'):
            self.targets = ['axM']; self.reset()

        if self.kb.is_pressed('o'):
            self.targets = ['q0M']; self.reset()
                    
        return (time() - self.startTime, self.current)

    def reset(self):
        self.stats = {} # Limpa os stats para re-normalizar com a nova variavel
        self.graph.need_reset = True
        self.startTime = time()
        self.current = None

    def saveDevice(self, data, device, folder):
        if not data:
            return pd.DataFrame().to_csv(os.path.join(folder, device, 'data.csv'), index=False)
        
        keys = set()
        for record in data:
            keys.update(record.keys())

        data = [{key: record.get(key, 0) for key in keys} for record in data]
        df = pd.DataFrame(data)
        df.to_csv(os.path.join(folder, device, 'data.csv'), index=False)
            
    def save(self, folder='output'):
        setFolder(os.path.join(folder, 'reference'))
        setFolder(os.path.join(folder, 'target'))
        setFolder(os.path.join(folder, 'mru'))
        
        with open(os.path.join(folder, 'info.json'), 'w') as file:
            file.write(json.dumps({
                "description": "Reference is Plate, Target is Measure, and MRU is Kongsberg"
            }, indent=4))

        self.saveDevice(self.valuesK, 'mru', folder)
        self.saveDevice(self.valuesM, 'target', folder)
        self.saveDevice(self.valuesP, 'reference', folder)


if __name__ == '__main__':
    monitor = Monitor()
    monitor.setup()
    thread = AsyncThreading(monitor.handle, interval=0.001)

    try:
        graph = TimeGraph(callback=monitor.get, xLim=[0, 20])
        monitor.graph = graph
        graph.start()
    except Exception as error:
        print('error: ', error)
    finally:      
        if monitor.SAVE:
            print('\nsalvando database')
            monitor.save()
