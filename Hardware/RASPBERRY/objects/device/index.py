from time import ticks_ms as millis
from time import sleep_ms as delay
from machine import Pin



class Device:
    def __init__(self):
        self.startProg = 0
        self.led    = Pin(25, Pin.OUT)
        self.status = (0, 0)
        self.settings = {
            'timeout': 0.5,
            'enabled': True,
            'newThing': True,
            'debug': True,
            'serial': 0
        }

    def setup(self):
        self.startProg = millis()
        self.start()
    
    def start(self):
        print('programa iniciado!')

        for i in range(5):
            self.led.toggle()
            delay(100)

        self.led.value(1)


device = Device()