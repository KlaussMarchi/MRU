from Device.index import Device
from Plotter.index import TimeGraph
from Utils.classes import AsyncThreading
from time import time, sleep
import numpy as np
import pandas as pd
import os, keyboard

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
        self.device.port = 'COM6'
        self.device.connect()
        self.device.stream()
        self.startTime = time()
        self.thread1   = AsyncThreading(self.device.handle)
        
    def user(self):
        caracteres = list('abcdefghijklmnopqrstuvwxyz0123456789')
        return any(keyboard.is_pressed(key) for key in list(keyboard.all_modifiers) + caracteres)

    def save(self):
        df = pd.DataFrame(self.values)
        
        if self.SAVE:
            df.to_csv('DataBase.csv', index=None)

    def handle(self):
        data = self.device.last
       
        if data is None:
            return
        
        self.update(data)
        self.values.append(data)

    def update(self, data):
        self.current = {
            'ax': data.get('ax'),
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
