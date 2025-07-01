from Device.index import Device
from Plotter.index import TimeGraph
from Utils.classes import AsyncThreading
from time import time, sleep
import numpy as np
import pandas as pd
import os, keyboard
from Kernel.index import KernelSensor

script_path = os.path.abspath(__file__)
base_dir = os.path.dirname(script_path)
os.chdir(base_dir)


class Monitor:
    SAVE = True

    def __init__(self):
        self.current = None
        self.values  = []
        
    def setup(self):
        self.device = Device(rate=115200)
        self.kernel = KernelSensor()

        self.kernel.port = 'COM27'
        self.kernel.connect()

        self.device.port = 'COM26'
        self.device.connect()
        
        self.device.stream()
        self.kernel.stream()

        self.kernel.set('frequency', 50)
        self.startTime = time()

        self.thread1 = AsyncThreading(self.device.stream)
        self.thread2 = AsyncThreading(self.kernel.stream)
        
    def user(self):
        caracteres = list('abcdefghijklmnopqrstuvwxyz0123456789')
        return any(keyboard.is_pressed(key) for key in list(keyboard.all_modifiers) + caracteres)

    def save(self):
        df = pd.DataFrame(self.values)
        
        if self.SAVE:
            df.to_csv('DataBase.csv', index=None)

    def handle(self):
        data = {'device': self.device.last, 'kernel': self.kernel.last}
        #print(data)

        if None in data.values():
            return

        self.update(data)
        self.values.append(data)

    def update(self, data):
        n = np.mean([10.11, 10.26, 10.08, 10.09]) / np.mean([499, 498, 500, 498])

        self.current = {
            'ax_6050':  data['device']['s2'].get('ax'),
            'ax_9250':  data['device']['s3'].get('ax'),
            'ax_kernel': data['kernel'].get('ax') * n,
        }
        print(self.current)

    def get(self):
        if self.current is None:
            return
        
        return (time() - self.startTime, self.current)


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
        if monitor.SAVE:
            monitor.save()
