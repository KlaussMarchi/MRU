from objects.sensors.MPU6050.analysis import Omega, Acceleration
from objects.wire.index import Wire
from time import sleep
import struct


class MPU6050:
    PWR_MGMT_1   = 0x6B
    SMPLRT_DIV   = 0x19
    CONFIG       = 0x1A
    ACCEL_XOUT_H = 0x3B
    
    def __init__(self, sda, scl):
        self.sda, self.scl = sda, scl
        self.a = Acceleration()
        self.w = Omega()

    def setup(self):
        self.address = self.connect()
        self.wire.write(self.address, self.PWR_MGMT_1, 0x00)
        sleep(0.1) # sample rate = 1 kHz
        self.wire.write(self.address, self.SMPLRT_DIV, 0x07) 
        print('MPU ready')

    def update(self):
        raw = self.wire.read(self.address, self.ACCEL_XOUT_H, 14)

        if not raw or len(raw) != 14:
            return
        
        wx, wy, wz, t, ax, ay, az = struct.unpack('>hhhhhhh', raw)
        self.a.update(ax, ay, az)
        self.w.update(wx, wy, wz)

    def get(self, update=False):
        if update:
            self.update()

        return {
            'wx': self.w.x, 
            'wy': self.w.y, 
            'wz': self.w.z, 
            'ax': self.a.x, 
            'ay': self.a.y, 
            'az': self.a.z, 
        }
    
    def connect(self, retries=3):
        self.wire = Wire(0, self.sda, self.scl, freq=400000)

        for i in range(retries):
            if self.wire.address is not None:
                return self.wire.address
            
            print('Endereço não encontrado, tent', i+1, 'de', retries)
            sleep(1.0)

        if self.wire.address is not None:
            print(f'new address: {hex(self.wire.address)}')
        
        return self.wire.address

