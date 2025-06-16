from time import ticks_ms as millis
from time import sleep_ms as delay
from machine import Pin
import uos, gc


def ramPercent():
    gc.collect()
    total = gc.mem_alloc() + gc.mem_free()
    used  = gc.mem_alloc()
    return (used / total) * 100

def flashPercent():
    stats = uos.statvfs('/')
    total = stats[0] * stats[2]
    free = stats[0]  * stats[3]
    used = total - free
    return (used / total) * 100

class Device:
    def __init__(self):
        self.startProg = 0
        self.led    = Pin(25, Pin.OUT)
        self.status = (0, 0)
        self.FLASH = flashPercent()
        self.RAM   = ramPercent()

        
        self.settings = {
            'timeout': 0.5,
            'enabled': True,
            'newThing': True,
            'debug': True,
            'serial': 0
        }

    def setup(self):
        self.startProg = millis()
        print('MRU Program - V0.1.0')
        print(f'{self.FLASH:.2f}% FLASH memory used')
        print(f'{self.RAM:.2f}% RAM memory used')

        for i in range(5):
            self.led.toggle()
            delay(100)

        print('programa iniciado!')
        self.led.value(1)


device = Device()