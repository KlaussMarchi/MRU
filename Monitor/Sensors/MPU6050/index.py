from time import sleep
from Utils.functions import sendEvent
from Utils.classes import AsyncThreading
import matplotlib.pyplot as plt
import smbus

PWR_MGMT_1   = 0x6B
SMPLRT_DIV   = 0x19
CONFIG       = 0x1A
GYRO_CONFIG  = 0x1B
INT_ENABLE   = 0x38
ACCEL_XOUT_H = 0x43
ACCEL_YOUT_H = 0x3B
ACCEL_ZOUT_H = 0x47
GYRO_XOUT_H  = 0x3D
GYRO_YOUT_H  = 0x45
GYRO_ZOUT_H  = 0x3F
DEVICE_ADDRESS = 0x68

# SDA - PINO GPIO2
# SCL - PINO GPIO3

class MPU6050:
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
        
    def getRaw(self, addr):
        high  = self.bus.read_byte_data(DEVICE_ADDRESS, addr)
        low   = self.bus.read_byte_data(DEVICE_ADDRESS, addr+1)
        value = (high << 8) | low
        
        if value > 32768:
            value = value - 65536
        
        return value

    def startStream(self):
        sendEvent('success', 'sensor stream started')
        thread = AsyncThreading(self.handleStream)

    def getVariables(self):
        return {
            'ax': self.getRaw(ACCEL_XOUT_H),  
            'ay': self.getRaw(ACCEL_YOUT_H),
            'az': self.getRaw(ACCEL_ZOUT_H),
            'wx': self.getRaw(GYRO_XOUT_H), 
            'wy': self.getRaw(GYRO_YOUT_H),
            'wz': self.getRaw(GYRO_ZOUT_H),
        }
    
    def handleStream(self):
        self.variables = self.getVariables()
        sendEvent('event', f'variables: {self.variables}')
        sleep(0.05)


