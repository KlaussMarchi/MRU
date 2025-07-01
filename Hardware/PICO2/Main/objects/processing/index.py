from objects.processing.computations.index import Omega, Acceleration, Velocity, Position, Quaternions
from objects.processing.fusion.index import Fusion
from globals.constants import DT_INTERVAL, RAW_DEBUG
from objects.device.index import device
from objects.sensors.index import sensors
from utime import ticks_ms as millis


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
        
        if RAW_DEBUG:
            return
        
        self.startTime = millis()
        wx = self.fusion.wx(sensors.sensor1.w, sensors.sensor2.w)
        wy = self.fusion.wy(sensors.sensor1.w, sensors.sensor2.w)
        wz = self.fusion.wz(sensors.sensor1.w, sensors.sensor2.w)

        ax = self.fusion.ax(sensors.sensor1.a, sensors.sensor2.a)
        ay = self.fusion.ay(sensors.sensor1.a, sensors.sensor2.a)
        az = self.fusion.az(sensors.sensor1.a, sensors.sensor2.a)

        self.w.update(wx, wy, wz) # velocidade angular fundida
        self.a.update(ax, ay, az) # aceleração linear fundida
        
        self.v.update(self.a) # velocidade linear processados
        self.p.update(self.v) # posição linear processados
        self.q.update(self.a, self.w) # pitch, roll, yaw processados

    def get(self):
        return {
            'time': device.time(),
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
        data = {'time': device.time()}
        
        for i, s in enumerate([sensors.sensor1, sensors.sensor2]):
            data[f's{i+1}'] = s.get()

        return data


processing = Processing()