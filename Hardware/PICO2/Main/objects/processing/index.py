from objects.processing.computations.index import Omega, Acceleration, Velocity, Position, Quaternions
from objects.processing.fusion.index import Fusion
from time import ticks_ms as millis
from objects.device.index import device
from globals.constants import DT_INTERVAL
from objects.sensors.index import sensors


class Processing:
    def __init__(self):
        self.startTime = 0
        self.fusion = Fusion()
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

        wx = self.fusion.wx(sensors.sensor1.w.x, sensors.sensor2.w.x, sensors.sensor3.w.x)
        wy = self.fusion.wy(sensors.sensor1.w.y, sensors.sensor2.w.y, sensors.sensor3.w.y)
        wz = self.fusion.wz(sensors.sensor1.w.z, sensors.sensor2.w.z, sensors.sensor3.w.z)

        ax = self.fusion.ax(sensors.sensor1.a.x, sensors.sensor2.a.x, sensors.sensor3.a.x)
        ay = self.fusion.ay(sensors.sensor1.a.y, sensors.sensor2.a.y, sensors.sensor3.a.y)
        az = self.fusion.az(sensors.sensor1.a.z, sensors.sensor2.a.z, sensors.sensor3.a.z)

        self.w.update(wx, wy, wz) # velocidade angular fundida
        self.a.update(ax, ay, az) # aceleração linear fundida
        
        self.v.update(self.a.x, self.a.y, self.a.z) # velocidade linear processados
        self.p.update(self.v.x, self.v.y, self.v.z) # posição linear processados
        self.q.update(self.a, self.w) # pitch, roll, yaw processados

    def get(self):
        return {
            'time': (millis() - device.startProg)/1000.00,
            'ax': self.a.x,
            'ay': self.a.y,
            'az': self.a.z,
            'wx': self.w.x,
            'wy': self.w.y,
            'wz': self.w.z,
            'vx': self.v.x,
            'vy': self.v.y,
            'vz': self.v.z,
            'px': self.p.x,
            'py': self.p.y,
            'pz': self.p.z,
            'pitch': self.q.pitch,
            'roll':  self.q.roll,
            'yaw':   self.q.yaw,
        }
    
    def raw(self):
        data = {}
        
        for i, s in enumerate([sensors.sensor1, sensors.sensor2, sensors.sensor3]):
            data[f's{i+1}'] = s.get()

        return data


processing = Processing()