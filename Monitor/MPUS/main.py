from Device.index import Device
from Plotter.index import TimeGraph
from Utils.classes import AsyncThreading
from time import time, sleep
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
        self.device.connect()
        
        self.device.stream(command=False)
        self.startTime = time()
    
    def user(self):
        caracteres = list("abcdefghijklmnopqrstuvwxyz0123456789")
        return any(keyboard.is_pressed(key) for key in list(keyboard.all_modifiers) + caracteres)

    def save(self):
        df = pd.DataFrame(self.values)
        
        if self.SAVE:
            df.to_csv('DataBase.csv', index=None)

    def handle(self):
        data = self.device.getJson()
        print(data)

        if data is None:
            return

        self.update(data)
        self.values.append(data)

    def update(self, data):
        self.current = {
            'ax_kern':  data['s1'].get('ax'),
        }

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
