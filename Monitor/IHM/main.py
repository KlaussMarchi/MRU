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
        self.device.port = '/dev/ttyACM0'
        self.device.connect()
        self.device.stream()
        self.startTime = time()
        self.thread1   = AsyncThreading(self.device.handle)
        
    def user(self):
        caracteres = list('abcdefghijklmnopqrstuvwxyz0123456789')
        return any(keyboard.is_pressed(key) for key in list(keyboard.all_modifiers) + caracteres)

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

    def handle(self):
        data = self.device.last
       
        if data is None:
            return
        
        self.update(data)
        self.values.append(data)

    def update(self, data):
        print(data)

        target = {
            'ax': data.get('ax')
        }

        if None in target.values():
            return

        self.current = target

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

