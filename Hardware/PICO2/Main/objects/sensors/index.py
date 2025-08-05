from utime import ticks_ms as millis
from objects.sensors.KERNEL.index   import KernelSensor
from objects.sensors.CRS0304S.index import CRS0304S
from objects.sensors.MPU6050.index  import MPU6050
from objects.sensors.MPU9250.index  import MPU9250
from objects.sensors.BNO85.index    import BNO085
from globals.constants import DT_INTERVAL


class Sensors:
    def __init__(self):
        self.sensor1 = MPU6050(16, 17)
        self.sensor2 = MPU9250(20, 21)
        self.sensor3 = CRS0304S(28)
        #self.sensor3 = KernelSensor(4, 5)
        #self.sensor1 = BNO085(16, 17)
        self.startTime = millis()

    def setup(self):
        for s in self.get():
            s.setup()

    def handle(self):
        if millis() - self.startTime < DT_INTERVAL:
            return
        
        self.startTime = millis()
    
        for s in self.get():
            s.update()
    
    def get(self):
        return (self.sensor1, self.sensor2, self.sensor3)


sensors = Sensors()