from objects.sensors.KERNEL.analysis import Acceleration, Omega
from machine import UART, Pin
from time import sleep_ms as delay
from utime import ticks_ms as millis


class KernelSensor:
    CMD_ORIENTATION = bytes([0xAA, 0x55, 0x00, 0x00, 0x07, 0x00, 0x33, 0x3A, 0x00])
    PKT_LEN = 42
    KG = 10.0   # Fator de escala para giroscópio
    KA = 500.0  # Fator de escala para acelerômetro

    def __init__(self, tx_pin, rx_pin):
        print(f'Kernel Started at tx={tx_pin} and rx={rx_pin}')
        self.uart = UART(1, baudrate=9600, tx=Pin(tx_pin), rx=Pin(rx_pin))
        self.packet = bytearray(42)
        self.header = False
        self.index = 0
        self.lastUpdate = millis()

        self.a = Acceleration()
        self.w = Omega()
        self.temp = 0

    def setup(self):
        print('Activation CMD Sent')
        self.uart.write(self.CMD_ORIENTATION)
        delay(200)

    def reset(self):
        self.header = False
        self.index = 0

    def available(self):
        if self.header and millis() - self.lastUpdate > 100:
            self.reset()
            return False

        while self.uart.any():
            newByte = self.uart.read(1)[0]
            self.lastUpdate = millis()

            if not self.header:
                if newByte == 0xAA:
                    self.packet[0] = 0xAA
                    self.index = 1
                elif self.index == 1 and newByte == 0x55:
                    self.packet[1] = 0x55
                    self.header = True
                    self.index = 2
                continue
            
            if self.index < self.PKT_LEN:
                self.packet[self.index] = newByte
                self.index += 1
                
            if self.index >= self.PKT_LEN:
                return True
                
        return False

    def update(self):
        if not self.available():
            return None
        
        calc_checksum = sum(self.packet[2:40])
        recv_checksum = self.packet[40] | (self.packet[41] << 8)
        
        if calc_checksum != recv_checksum:
            print('Checksum inválido!')
            self.reset()
            return None
        
        heading = int.from_bytes(self.packet[7:9], 'little', True) / 100.0
        pitch = int.from_bytes(self.packet[9:11], 'little', True) / 100.0
        roll = int.from_bytes(self.packet[11:13], 'little', True) / 100.0
        
        wx = int.from_bytes(self.packet[13:15], 'little', True) / self.KG
        wy = int.from_bytes(self.packet[15:17], 'little', True) / self.KG
        wz = int.from_bytes(self.packet[17:19], 'little', True) / self.KG
        
        ax = int.from_bytes(self.packet[19:21], 'little', True) / self.KA
        ay = int.from_bytes(self.packet[21:23], 'little', True) / self.KA
        az = int.from_bytes(self.packet[23:25], 'little', True) / self.KA
        self.temp = int.from_bytes(self.packet[33:35], 'little', True) / 10.0

        self.a.update(ax, ay, az)
        self.w.update(wx, wy, wz)
        self.reset()
        return True

    def get(self, update=False):
        if update:
            self.update()
            
        return {
            'wx': self.w.x, 
            'wy': self.w.y, 
            'wz': self.w.z, 
            'ax': self.a.x, 
            'ay': self.a.y, 
            'az': self.a.z, 
        }