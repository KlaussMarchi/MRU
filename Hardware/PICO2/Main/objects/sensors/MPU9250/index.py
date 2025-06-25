from objects.sensors.MPU9250.analysis import Omega, Acceleration
from objects.wire.index import Wire
from time import sleep
import struct


class MPU9250:
    PWR_MGMT_1   = 0x6B
    SMPLRT_DIV   = 0x19
    CONFIG       = 0x1A
    ACCEL_XOUT_H = 0x3B

    def __init__(self, sda, scl):
        self.sda, self.scl = sda, scl
        self.a = Acceleration()
        self.w = Omega()
        self.wire    = None
        self.address = None

    def setup(self):
        self.address = self.connect()
        self.wire.write(self.address, self.PWR_MGMT_1, 0x00)
        sleep(0.1)
        self.wire.write(self.address, self.SMPLRT_DIV, 0x07)
        sleep(0.1)
        self.wire.write(self.address, self.CONFIG, 0x00)
        sleep(0.1)
        print('MPU9250 ready')

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

        for i in range(1, retries + 1):
            if self.wire.address is not None:
                return self.wire.address
        
            print(f'Tentativa {i}/{retries}: sem resposta')
            sleep(1.0)
        
        return self.wire.address

