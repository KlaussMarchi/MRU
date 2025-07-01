from objects.sensors.MPU6050.analysis import Omega, Acceleration
from objects.wire.index import Wire
from time import sleep
import struct


class MPU6050:
    def __init__(self, sda, scl):
        self.sda, self.scl = sda, scl
        self.a = Acceleration()
        self.w = Omega()

    def setup(self):
        self.address = self.connect()
        self.wire.write(self.address, 0x6B, 0x00)
        sleep(0.1)
        self.wire.write(self.address, 0x19, 0x07)
        sleep(0.1)

    def update(self):
        data = self.wire.read(self.address, 0x3B, 14)

        if not data or len(data) != 14:
            return
        
        ax, ay, az, _, wx, wy, wz = struct.unpack('>hhhhhhh', data)
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

