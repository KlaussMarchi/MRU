from objects.processing.compute import *
from time import ticks_ms as millis
from objects.device.index import device
from globals.constants import DT_INTERVAL
from objects.sensors.index import sensors


class Processing:
    def __init__(self):
        self.startTime = 0
        self.w = Omega()
        self.a = Acceleration()
        self.v = Velocity()
        self.p = Position()
        self.q = Quaternions()
    
    def setup(self):
        self.startTime = millis()
    
    def handle(self):
        if millis() - self.startTime < DT_INTERVAL:
            return
        
        self.startTime = millis()
        ax, ay, az = sensors.sensor1.a.get()
        wx, wy, wz = sensors.sensor1.w.get()

        self.w.update(ax, ay, az)
        self.a.update(wx, wy, wz)
        self.v.update(self.a.x, self.a.y, self.a.z)
        self.p.update(self.v.x, self.v.y, self.v.z)
        self.q.update(self.a, self.w)

    def get(self):
        return {
            'time': (millis() - device.startProg)/1000.00,
            'ax': self.a.x,
            'ay': self.a.y,
            'az': self.a.z,
            'wx': self.w.x,
            'wy': self.w.y,
            'wz': self.w.z,
            'vx': self.v.z,
            'vy': self.v.y,
            'vz': self.v.z,
            'px': self.p.x,
            'py': self.p.y,
            'pz': self.p.z,
            'pitch': self.q.pitch,
            'roll':  self.q.roll,
            'yaw':   self.q.yaw,
        }


processing = Processing()