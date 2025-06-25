from globals.constants import dt
from globals.classes import Integral
from globals.functions import sign
from objects.processing.array.index import Array
import math


class Omega:
    def __init__(self):
        self.x = self.y = self.z = 0

    def update(self, wx, wy, wz):
        self.x = wx
        self.y = wy
        self.z = wz

class Acceleration:
    def __init__(self):
        self.x = self.y = self.z = 0

    def update(self, ax, ay, az):
        self.x = ax
        self.y = ay
        self.z = az

class Velocity:
    def __init__(self):
        self.intX = Integral()
        self.intY = Integral()
        self.intZ = Integral()
        self.x = self.y = self.z = 0

    def update(self, a):
        self.x = self.intX.compute(a.x)
        self.y = self.intY.compute(a.y)
        self.z = self.intZ.compute(a.z)

class Position:
    def __init__(self):
        self.intX = Integral()
        self.intY = Integral()
        self.intZ = Integral()
        self.x = self.y = self.z = 0

    def update(self, v):
        self.x = self.intX.compute(v.x)
        self.y = self.intY.compute(v.y)
        self.z = self.intZ.compute(v.z)

class Quaternions:
    def __init__(self):
        self.q = Array([1.0, 0.0, 0.0, 0.0])
        self.data  = Array([1.0, 0.0, 0.0, 0.0])
        self.pitch = self.roll = self.yaw = 0

    def product(self, q1, q2):
        w1, x1, y1, z1 = q1.data
        w2, x2, y2, z2 = q2.data

        w = w1*w2 - x1*x2 - y1*y2 - z1*z2
        x = w1*x2 + x1*w2 + y1*z2 - z1*y2
        y = w1*y2 - x1*z2 + y1*w2 + z1*x2
        z = w1*z2 + x1*y2 - y1*x2 + z1*w2
        return Array([w, x, y, z])
    
    def euler(self, qData):
        q0, q1, q2, q3 = qData.data
        # Roll (x-axis rotation)
        sinr_cosp = 2 * (q0 * q1 + q2 * q3)
        cosr_cosp = 1 - 2 * (q1**2 + q2**2)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        
        # Pich (y-axis rotation)
        sinp  = 2*(q0 * q2 - q3 * q1)
        pitch = sign(sinp)*(math.pi/2) if abs(sinp) >= 1 else math.asin(sinp)

        # Yaw (z-axis rotation)
        siny_cosp = 2 * (q0 * q3 + q1 * q2)
        cosy_cosp = 1 - 2 * (q2**2 + q3**2)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        return (pitch, roll, yaw)

    def fromOmega(self, wx, wy, wz):
        omega = Array([0.0, wx, wy, wz])
        q_dot = self.product(omega, self.q)
        self.q = (q_dot * 0.5 * dt + self.q).norm()

    def fromAccel(self, ax, ay, az):
        ax, ay, az = Array([ax, ay, az]).norm().data
        pitch = math.atan2(-ax, math.sqrt(ay**2 + az**2))
        roll  = math.atan2(ay, az)
        yaw   = 0  # sem magnetômetro

        qroll  = Array([math.cos(roll/2),  math.sin(roll/2), 0, 0])
        qpitch = Array([math.cos(pitch/2), 0, math.sin(pitch/2), 0])
        qyaw   = Array([math.cos(yaw/2),   0, 0, math.sin(yaw/2)])

        #q = q_yaw ⊗ (q_pitch ⊗ q_roll)
        q_temp = self.product(qpitch, qroll)
        return self.product(qyaw, q_temp)
    
    def update(self, a, w):    
        self.fromOmega(w.x, w.y, w.z)
        #self.fromAccel(a.x, a.y, a.z)
        self.pitch, self.roll, self.yaw = self.euler(self.q)
