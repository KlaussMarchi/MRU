from globals.constants import RAW_DEBUG, SERIAL_DEBUG
from machine import UART
import sys, uselect


class USB:
    def __init__(self):
        self.poller = uselect.poll()
        self.poller.register(sys.stdin, uselect.POLLIN)

    def any(self):
        return bool(self.poller.poll(0))
    
    def read(self):
        return sys.stdin.buffer.readline()
    
    def write(self, message):
        sys.stdout.write(message)
        sys.stdout.flush()


class Protocol:
    def __init__(self):
        self.serial  = USB() if SERIAL_DEBUG else UART(0, baudrate=115200)
        self.command = ""
    
    def available(self):
        return self.serial.any()
    
    def update(self):
        self.command = self.serial.read().decode('utf-8').strip()
    
    def send(self, message, breakLine=True):
        if breakLine:
            message += '\n'

        return self.serial.write(message)
        
    def process(self):
        global RAW_DEBUG

        if self.command == 'debug':
            RAW_DEBUG = not RAW_DEBUG
            self.send(f'state: {RAW_DEBUG}')
        else:
            print('nenhum')
    
    def handle(self):
        if not self.available():
            return
        
        self.update()
        self.process()


protocol = Protocol()
