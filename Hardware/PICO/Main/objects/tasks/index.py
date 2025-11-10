from utime import ticks_ms as millis
from objects.processing.index import processing
from globals.constants import DT_INTERVAL, RAW_DEBUG
from globals.functions import println
from objects.device.index import device
import gc, json


class Tasks:
    WORKING = (300, 300)
    FAIL    = (1000, 15000)
    WARNING = (1000, 5000)
    MAX_GARBAGE = -5*(1024)

    def __init__(self):
        self.lastMemory  = gc.mem_free()
        self.startMemory = millis()
        self.startBlink  = millis()
        self.startPrint  = millis()
        self.state = False

    def blink(self):
        onTime, offTime = device.status

        if self.state and millis() - self.startBlink > onTime:
            self.startBlink = millis()
            self.state = False
            device.led.value(self.state)

        if not self.state and millis() - self.startBlink > offTime:
            self.startBlink = millis()
            self.state = True
            device.led.value(self.state)

    def memory(self):
        if millis() - self.startMemory < 125000:
            return
        
        self.startMemory = millis()
        variation = (gc.mem_free() - self.lastMemory)
        
        if variation < self.MAX_GARBAGE:
            print('memory cleaning')
            gc.collect()
            self.lastMemory = gc.mem_free()

    def print(self):
        if millis() - self.startPrint < DT_INTERVAL:
            return
        
        self.startPrint = millis()

        if RAW_DEBUG:
            return println(json.dumps(processing.raw()))
        
        println(json.dumps(processing.get()))


tasks = Tasks()