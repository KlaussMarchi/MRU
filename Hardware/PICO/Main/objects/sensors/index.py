from time import ticks_ms as millis
from objects.sensors.CRS0304S.index import CRS0304S
from globals.constants import DT_INTERVAL


class Sensors:
    def __init__(self):
        self.sensor1   = CRS0304S()
        self.startTime = millis()

    def setup(self):
        self.sensor1.setup()

    def handle(self):
        if millis() - self.startTime < DT_INTERVAL:
            return
        
        self.startTime = millis()
        self.sensor1.update()


sensors = Sensors()