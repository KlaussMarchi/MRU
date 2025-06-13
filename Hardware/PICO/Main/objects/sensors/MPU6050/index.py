from objects.wire.index import Wire
from time import sleep
import struct
import ujson


class MPU6050:
    ACCEL_SCALE_MODIFIER = 16384.0   # LSB/g
    GYRO_SCALE_MODIFIER  = 131.0     # LSB/°/s
    PWR_MGMT_1   = 0x6B
    SMPLRT_DIV   = 0x19
    CONFIG       = 0x1A
    GYRO_CONFIG  = 0x1B
    ACCEL_CONFIG = 0x1C
    ACCEL_XOUT_H = 0x3B
    ACCEL_YOUT_H = 0x3D
    ACCEL_ZOUT_H = 0x3F
    TEMP_OUT_H   = 0x41
    GYRO_XOUT_H  = 0x43
    GYRO_YOUT_H  = 0x45
    GYRO_ZOUT_H  = 0x47
    
    def __init__(self, sda, scl):
        self.sda, self.scl = sda, scl
        self.address = self.connect()

        self.wire.write(self.address, self.PWR_MGMT_1, 0x00)
        sleep(0.1)
        self.wire.write(self.address, self.SMPLRT_DIV, 0x07) # sample rate = 1 kHz

    def connect(self):
        self.wire = Wire(0, self.sda, self.scl, freq=400000) 

        if self.wire.address is None:
            print('no device found, scanning again...')
            sleep(1.5)
            return self.connect()

        print(f'new address: {hex(self.wire.address)}')
        return self.wire.address

    def read(self, registerAddress):
        raw_bytes = self.wire.read(self.address, registerAddress, 2)
        return struct.unpack('>h', raw_bytes)[0]

    def update(self):
        self.ax = self.read(self.ACCEL_XOUT_H) / self.ACCEL_SCALE_MODIFIER
        self.ay = self.read(self.ACCEL_YOUT_H) / self.ACCEL_SCALE_MODIFIER
        self.az = self.read(self.ACCEL_ZOUT_H) / self.ACCEL_SCALE_MODIFIER
        self.gx = self.read(self.GYRO_XOUT_H) / self.GYRO_SCALE_MODIFIER
        self.gy = self.read(self.GYRO_YOUT_H) / self.GYRO_SCALE_MODIFIER
        self.gz = self.read(self.GYRO_ZOUT_H) / self.GYRO_SCALE_MODIFIER
        
    def toJson(self):
        return ujson.dumps({
            'ax': self.ax,
            'ay': self.ay,
            'az': self.az,
            'gx': self.gx,
            'gy': self.gy,
            'gz': self.gz
        })
    
