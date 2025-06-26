from objects.sensors.MPU9250.analysis import Omega, Acceleration
from objects.wire.index import Wire
from time import sleep
import struct


class MPU9250:
    def __init__(self, sda, scl):
        self.sda, self.scl = sda, scl
        self.a = Acceleration()
        self.w = Omega()
        self.wire    = None
        self.address = None

    def setup(self):
        self.address = self.connect()
        self.wire.write(self.address, 0x6B, 0x00)  # wake up the device (saindo do sleep mode)
        sleep(0.1)
        self.wire.write(self.address, 0x1C, 0x00)  # ACCEL_CONFIG: seleciona faixa ±2g
        sleep(0.1)
        self.wire.write(self.address, 0x1B, 0x00)  # GYRO_CONFIG: seleciona faixa ±250 °/s
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

        for i in range(1, retries + 1):
            if self.wire.address is not None:
                return self.wire.address
        
            print(f'Tentativa {i}/{retries}: sem resposta')
            sleep(1.0)
        
        return self.wire.address

