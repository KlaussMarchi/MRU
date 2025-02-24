import threading
import mpu6050
from time import time
from Utils.functions import sendEvent
from Utils.variables import dt


class Sensor:
    variables = {}
    sensor   = None
    addrress = (0x68)
    SDA_PIN  = 2
    SCL_PIN  = 3
    startTime = None
    stream    = False

    def __init__(self, address=None):
        if address is not None:
            self.addrress = address

    def setup(self):
        self.sensor = mpu6050.mpu6050(self.addrress)
        self.startTime = time()
        
    def startStream(self):
        sendEvent('success', 'sensor')
        self.startTime = time()
        thread = threading.Thread(target=self.handleStream)
        thread.daemon = True
        thread.start()
    
    def getVariables(self):
        acceleration = self.sensor.get_accel_data()
        gyroscope    = self.sensor.get_gyro_data()
        temperature  = self.sensor.get_temp()

        return {
            't': (time() - self.startTime),
            'ax': acceleration['x'],
            'ay': acceleration['y'],
            'az': acceleration['z'],
            'wx': gyroscope['x'],
            'wy': gyroscope['y'],
            'wz': gyroscope['z'],
            'T':  temperature
        }
    
    def handleStream(self):
        startTime = time()

        while True:
            if time() - startTime < dt:
                continue
            
            startTime = time()
            self.variables = self.getVariables()
            sendEvent('event', f'variables: {self.variables}')