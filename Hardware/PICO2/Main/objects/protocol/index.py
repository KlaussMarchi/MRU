from globals.constants import RAW_DEBUG
from machine import UART


class Protocol:
    def __init__(self):
        self.serial  = UART(0, baudrate=115200)
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
