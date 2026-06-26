import math

class Heave:
    def __init__(self):
        self.value = 0.0
        self.lastTime = 0.0
        
        self.fc   = 0.24420023692169276
        self.zeta = 0.7797975651763583
        self.px = 0.3560817875722976
        self.py = -0.9233830526072779
        self.pz = -0.14341305464217718
        self.scale  = 0.20627889373308725
        self.offset = -0.7941257971234911
        
        # ODE State variables
        self.h = 0.0
        self.v = 0.0

    def update(self, wx, wy, wz, ax, ay, az, pitch, roll, timestamp_us):
        if self.lastTime == 0.0:
            self.lastTime = timestamp_us
            return
            
        dt = (timestamp_us - self.lastTime) / 1000000.0

        if dt <= 0:
            return
            
        self.lastTime = timestamp_us
        
        a_proj  = self.px * ax + self.py * ay + self.pz * az
        omega_c = 2.0 * math.pi * self.fc
        omega_c_sq = omega_c * omega_c
        two_zeta_omega_c = 2.0 * self.zeta * omega_c
        
        self.v += (a_proj - two_zeta_omega_c * self.v - omega_c_sq * self.h) * dt
        self.h += self.v * dt
        self.value = self.h * self.scale + self.offset
