from time import ticks_ms as millis
from time import sleep_ms as delay
from machine import Pin
import gc


class Device:
    startProg  = 0
    startTime  = 0
    lastMemory = 0
    
    def __init__(self):
        self.led = Pin(25, Pin.OUT)

    def setup(self):
        self.startProg  = millis()
        self.lastMemory = gc.mem_free()

        for i in range(5):
            self.led.toggle()
            delay(250)

        self.led.value(1)

    def handle(self):
        if millis() - self.startTime < 60000:
            return
        
        self.startTime = millis()
        variation = (gc.mem_free() - self.lastMemory)

        if variation < -5120: # 5kb
            gc.collect()
        
        self.lastMemory = gc.mem_free()

