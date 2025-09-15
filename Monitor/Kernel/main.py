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

        #self.kernel.set('frequency', 50)
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
        print(data)

        if None in data.values():
            return

        self.update(data)
        self.values.append(data)

    def update(self, data):
        #if abs(data['kernel'].get('ax')) > 1000: return

        self.current = {
            'ax_fusion': data['device']['s1'].get('ax'),
            'ax_kernel': data['kernel'].get('ax'),
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
        print('\nsalvando database')

        if monitor.SAVE:
            monitor.save()




"""
11:08:11.165 -> angle update: 60.00º
11:08:16.155 -> angle update: 90.00º
11:08:21.170 -> angle update: 120.00º
11:08:26.153 -> angle update: 90.00º
11:08:31.159 -> angle update: 135.00º
11:08:36.150 -> angle update: 40.00º
11:08:41.165 -> angle update: 120.00º
11:08:46.155 -> angle update: 75.00º
11:08:51.156 -> angle update: 50.00º
11:08:56.170 -> angle update: 95.00º
11:09:01.167 -> angle update: 135.00º
11:09:06.159 -> angle update: 40.00º

"""
