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

class Quaternion:
    def __init__(self, w=1.0, x=0.0, y=0.0, z=0.0):
        self.w, self.x, self.y, self.z = float(w), float(x), float(y), float(z)

    # q * p  ou  q * escalar
    def __mul__(self, other):
        if isinstance(other, Quaternion):
            return Quaternion(
                self.w * other.w - self.x * other.x - self.y * other.y - self.z * other.z,
                self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y,
                self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x,
                self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w,
            )
        # escalar
        return Quaternion(self.w * other, self.x * other, self.y * other, self.z * other)

    # permite  escalar * q
    __rmul__ = __mul__

    # soma elemento a elemento
    def __add__(self, other):
        return Quaternion(self.w + other.w, self.x + other.x, self.y + other.y, self.z + other.z)

    # conjugado
    def conj(self):
        return Quaternion(self.w, -self.x, -self.y, -self.z)

    # norma e normalização
    def norm(self):
        return math.sqrt(self.w*self.w + self.x*self.x + self.y*self.y + self.z*self.z)

    def normalize(self):
        n = self.norm()

        if n == 0:
            return
        
        self.w /= n
        self.x /= n
        self.y /= n
        self.z /= n

class Orientation:
    def __init__(self, dt=0.02, beta=0.1):
        self.dt   = dt
        self.beta = beta
        self.q = Quaternion()
        self.pitch = 0
        self.roll  = 0
        self.yaw   = 0

    # GIROSCÓPIO + ACELERÔMETRO
    def update(self, omega, accel):
        gx, gy, gz = omega.x, omega.y, omega.z
        ax, ay, az = accel.x, accel.y, accel.z

        q1, q2, q3, q4 = self.q.w, self.q.x, self.q.y, self.q.z
        norm = math.sqrt(ax*ax + ay*ay + az*az) # Normaliza acel
        
        if norm == 0.0:
            return
        
        ax, ay, az = ax/norm, ay/norm, az/norm

        # 2) Variáveis auxiliares
        _2q1 = 2.0 * q1
        _2q2 = 2.0 * q2
        _2q3 = 2.0 * q3
        _2q4 = 2.0 * q4
        _4q1 = 4.0 * q1
        _4q2 = 4.0 * q2
        _4q3 = 4.0 * q3
        _8q2 = 8.0 * q2
        _8q3 = 8.0 * q3
        q1q1 = q1 * q1
        q2q2 = q2 * q2
        q3q3 = q3 * q3
        q4q4 = q4 * q4

        # 3) Gradiente
        s1 = _4q1*q3q3 + _2q3*ax + _4q1*q2q2 - _2q2*ay
        s2 = _4q2*q4q4 - _2q4*ax + 4.0*q1q1*q2 - _2q1*ay - _4q2 + _8q2*q2q2 + _8q2*q3q3 + _4q2*az
        s3 = 4.0*q1q1*q3 + _2q1*ax + _4q3*q4q4 - _2q4*ay - _4q3 + _8q3*q2q2 + _8q3*q3q3 + _4q3*az
        s4 = 4.0*q2q2*q4 - _2q2*ax + 4.0*q3q3*q4 - _2q3*ay
        norm_s = math.sqrt(s1*s1 + s2*s2 + s3*s3 + s4*s4)

        if norm_s == 0.0:
            return
        
        s1 /= norm_s
        s2 /= norm_s
        s3 /= norm_s
        s4 /= norm_s

        # 4) q̇ = ½ q ⊗ ω − β s
        qDot1 = 0.5 * (-q2*gx - q3*gy - q4*gz) - self.beta * s1
        qDot2 = 0.5 * ( q1*gx + q3*gz - q4*gy) - self.beta * s2
        qDot3 = 0.5 * ( q1*gy - q2*gz + q4*gx) - self.beta * s3
        qDot4 = 0.5 * ( q1*gz + q2*gy - q3*gx) - self.beta * s4

        # 5) Integra
        q1 += qDot1 * self.dt
        q2 += qDot2 * self.dt
        q3 += qDot3 * self.dt
        q4 += qDot4 * self.dt

        self.q = Quaternion(q1, q2, q3, q4)
        self.q.normalize()
        self.to_euler()

    # GIROSCÓPIO + ACELERÔMETRO + MAGNETÔMETRO
    def updateMag(self, omega, accel, mag):
        gx, gy, gz = omega.x, omega.y, omega.z
        ax, ay, az = accel.x, accel.y, accel.z
        mx, my, mz = mag.x, mag.y, mag.z

        q1, q2, q3, q4 = self.q.w, self.q.x, self.q.y, self.q.z

        # auxiliares que faltavam
        _2q1 = 2.0 * q1
        _2q2 = 2.0 * q2
        _2q3 = 2.0 * q3
        _2q4 = 2.0 * q4

        # Normaliza acel
        norm = math.sqrt(ax*ax + ay*ay + az*az)

        if norm == 0.0:
            return
        
        ax, ay, az = ax/norm, ay/norm, az/norm

        # Normaliza mag
        norm = math.sqrt(mx*mx + my*my + mz*mz)

        if norm == 0.0:
            return
        
        mx, my, mz = mx/norm, my/norm, mz/norm

        # Referência do campo magnético
        _2q1mx = _2q1 * mx
        _2q1my = _2q1 * my
        _2q1mz = _2q1 * mz
        _2q2mx = _2q2 * mx

        hx = (mx * q1*q1 - _2q1my*q4 + _2q1mz*q3 + mx * q2*q2 + _2q2*my*q3 + _2q2*mz*q4 - mx * q3*q3 - mx * q4*q4)
        hy = (_2q1mx*q4 + my*q1*q1 - _2q1mz*q2 + _2q2mx*q3 - my*q2*q2 + my*q3*q3 + _2q3*mz*q4 - my*q4*q4)
        _2bx = math.sqrt(hx*hx + hy*hy)
        _2bz = (-_2q1mx*q3 + _2q1my*q2 + mz*q1*q1 + _2q2mx*q4 - mz*q2*q2 + _2q3*my*q4 - mz*q3*q3 + mz*q4*q4)
        _4bx = 2.0 * _2bx
        _4bz = 2.0 * _2bz

        s1 = (-_2q3*(2.0*q2*q4 - _2q1*q3 - ax) + _2q2*(2.0*q1*q2 + _2q3*q4 - ay) - _2bz*q3*(_2bx*(0.5 - q3*q3 - q4*q4) +
            _2bz*(q2*q4 - q1*q3) - mx) + (-_2bx*q4 + _2bz*q2) * (_2bx*(q2*q3 - q1*q4) +  _2bz*(q1*q2 + q3*q4) - my) + 
            _2bx*q3*(_2bx*(q1*q3 + q2*q4) + _2bz*(0.5 - q2*q2 - q3*q3) - mz))

        s2 = (_2q4*(2.0*q2*q4 - _2q1*q3 - ax) + _2q1*(2.0*q1*q2 + _2q3*q4 - ay) - 4.0*q2*(1 - 2.0*q2*q2 - 2.0*q3*q3 - az) +
            _2bz*q4*(_2bx*(0.5 - q3*q3 - q4*q4) + _2bz*(q2*q4 - q1*q3) - mx) + (_2bx*q3 + _2bz*q1) * (_2bx*(q2*q3 - q1*q4) +
            _2bz*(q1*q2 + q3*q4) - my) + (_2bx*q4 - _4bz*q2) * (_2bx*(q1*q3 + q2*q4) + _2bz*(0.5 - q2*q2 - q3*q3) - mz))

        s3 = (-_2q1*(2.0*q2*q4 - _2q1*q3 - ax) + _2q4*(2.0*q1*q2 + _2q3*q4 - ay) - 4.0*q3*(1 - 2.0*q2*q2 - 2.0*q3*q3 - az) +
            (-_4bx*q3 - _2bz*q1) * (_2bx*(0.5 - q3*q3 - q4*q4) + _2bz*(q2*q4 - q1*q3) - mx) + (_2bx*q2 + _2bz*q4) *
            (_2bx*(q2*q3 - q1*q4) + _2bz*(q1*q2 + q3*q4) - my) + (_2bx*q1 - _4bz*q3) * (_2bx*(q1*q3 + q2*q4) + _2bz*(0.5 - q2*q2 - q3*q3) - mz))

        s4 = (_2q2*(2.0*q2*q4 - _2q1*q3 - ax) + _2q3*(2.0*q1*q2 + _2q3*q4 - ay) + (-_4bx*q4 + _2bz*q2) * (_2bx*(0.5 - q3*q3 - q4*q4) +
            _2bz*(q2*q4 - q1*q3) - mx) + (-_2bx*q1 + _2bz*q3) * (_2bx*(q2*q3 - q1*q4) + _2bz*(q1*q2 + q3*q4) - my) + _2bx*q2*(_2bx*(q1*q3 + q2*q4) +
            _2bz*(0.5 - q2*q2 - q3*q3) - mz))

        norm_s = math.sqrt(s1*s1 + s2*s2 + s3*s3 + s4*s4)
        
        if norm_s == 0.0:
            return
        
        s1 /= norm_s
        s2 /= norm_s
        s3 /= norm_s
        s4 /= norm_s

        # q̇ = ½ q ⊗ ω − β s
        qDot1 = 0.5 * (-q2*gx - q3*gy - q4*gz) - self.beta * s1
        qDot2 = 0.5 * ( q1*gx + q3*gz - q4*gy) - self.beta * s2
        qDot3 = 0.5 * ( q1*gy - q2*gz + q4*gx) - self.beta * s3
        qDot4 = 0.5 * ( q1*gz + q2*gy - q3*gx) - self.beta * s4

        # Integra
        q1 += qDot1 * self.dt
        q2 += qDot2 * self.dt
        q3 += qDot3 * self.dt
        q4 += qDot4 * self.dt

        self.q = Quaternion(q1, q2, q3, q4)
        self.q.normalize()
        self.to_euler()

    # Z-Y-X (yaw-pitch-roll)
    def to_euler(self):
        q = self.q
        sinr_cosp = 2.0 * (q.w*q.x + q.y*q.z)
        cosr_cosp = 1.0 - 2.0 * (q.x*q.x + q.y*q.y)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        sinp = 2.0 * (q.w*q.y - q.z*q.x)
        pitch = math.asin(sinp) if abs(sinp) < 1.0 else math.copysign(math.pi/2, sinp)

        siny_cosp = 2.0 * (q.w*q.z + q.x*q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y*q.y + q.z*q.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        self.pitch = pitch
        self.roll  = roll
        self.yaw   = yaw
    