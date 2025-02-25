import smbus
import threading
from time import time, sleep
from Utils.functions import sendEvent
from Utils.variables import dt
from Utils.classes import AsyncThreading

PWR_MGMT_1   = 0x6B
SMPLRT_DIV   = 0x19
CONFIG       = 0x1A
GYRO_CONFIG  = 0x1B
INT_ENABLE   = 0x38
ACCEL_XOUT_H = 0x3B
ACCEL_YOUT_H = 0x3D
ACCEL_ZOUT_H = 0x3F
GYRO_XOUT_H  = 0x43
GYRO_YOUT_H  = 0x45
GYRO_ZOUT_H  = 0x47
DEVICE_ADDRESS = 0x68

class Sensor:
    variables = {}
    startTime = None
    stream    = False

    def __init__(self):
        self.bus = smbus.SMBus(1)

    def setup(self):
        self.bus.write_byte_data(DEVICE_ADDRESS, SMPLRT_DIV, 7)
        self.bus.write_byte_data(DEVICE_ADDRESS, PWR_MGMT_1, 1)
        self.bus.write_byte_data(DEVICE_ADDRESS, CONFIG, 0)
        self.bus.write_byte_data(DEVICE_ADDRESS, GYRO_CONFIG, 24)
        self.bus.write_byte_data(DEVICE_ADDRESS, INT_ENABLE, 1)
        self.startTime = time()
        
    def getRaw(self, addr):
        high  = self.bus.read_byte_data(DEVICE_ADDRESS, addr)
        low   = self.bus.read_byte_data(DEVICE_ADDRESS, addr+1)
        value = (high << 8) | low
        
        if value > 32768:
            value = value - 65536
        
        return value

    def startStream(self):
        sendEvent('success', 'sensor')
        thread = AsyncThreading(self.handleStream)
        self.startTime = time()

    def getVariables(self):
        return {
            't': (time() - self.startTime),
            'ax': self.getRaw(ACCEL_XOUT_H) / 16384.0,  
            'ay': self.getRaw(ACCEL_YOUT_H) / 16384.0,
            'az': self.getRaw(ACCEL_ZOUT_H) / 16384.0,
            'wx': self.getRaw(GYRO_XOUT_H) / 131.0,  
            'wy': self.getRaw(GYRO_YOUT_H) / 131.0,
            'wz': self.getRaw(GYRO_ZOUT_H) / 131.0,
        }
    
    def handleStream(self):
        self.variables = self.getVariables()
        sendEvent('event', f'variables: {self.variables}')
        sleep(0.05)


