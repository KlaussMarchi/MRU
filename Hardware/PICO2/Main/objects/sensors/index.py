from time import ticks_ms as millis
from objects.sensors.CRS0304S.index import CRS0304S
from objects.sensors.MPU6050.index import MPU6050
from globals.constants import DT_INTERVAL


class Sensors:
    def __init__(self):
        self.sensor1 = CRS0304S(28)
        self.sensor2 = MPU6050(16, 17)
        self.sensor3 = self.sensor1
        self.startTime = millis()

    def setup(self):
        self.sensor1.setup()
        self.sensor2.setup()

    def handle(self):
        if millis() - self.startTime < DT_INTERVAL:
            return
        
        self.startTime = millis()
        self.sensor1.update()
        self.sensor2.update()


sensors = Sensors()