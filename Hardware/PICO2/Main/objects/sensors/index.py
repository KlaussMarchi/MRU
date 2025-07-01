from utime import ticks_ms as millis
from objects.sensors.KERNEL.index   import KernelSensor
from objects.sensors.CRS0304S.index import CRS0304S
from objects.sensors.MPU6050.index  import MPU6050
from objects.sensors.MPU9250.index  import MPU9250
from globals.constants import DT_INTERVAL


class Sensors:
    def __init__(self):
        self.sensor1 = MPU6050(16, 17)
        self.sensor2 = MPU9250(20, 21)
        #self.sensor3 = KernelSensor(4, 5)
        #self.sensor4 = CRS0304S(28)
        self.startTime = millis()

    def setup(self):
        self.sensor1.setup()
        self.sensor2.setup()
        #self.sensor3.setup()
        #self.sensor4.setup()

    def handle(self):
        if millis() - self.startTime < DT_INTERVAL:
            return
        
        self.startTime = millis()
        self.sensor1.update()
        self.sensor2.update()
        #self.sensor3.update()
        #self.sensor4.update()


sensors = Sensors()