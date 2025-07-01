from machine import UART, Pin
import time, struct
from time import sleep_ms as delay
from objects.sensors.MPU6050.analysis import Omega, Acceleration


class KernelSensor:
    CMD_ORIENTATION = bytes.fromhex('AA 55 00 00 07 00 33 3A 00')
    HDR     = b'\xAA\x55\x01'
    PKT_LEN = 42

    def __init__(self, tx_pin, rx_pin):
        self.uart   = UART(1, baudrate=115200, tx=Pin(tx_pin), rx=Pin(rx_pin))
        self.buffer = bytearray()
        self.packet = None
        self.a = Acceleration()
        self.w = Omega()

    def setup(self):
        self.uart.write(self.CMD_ORIENTATION)
        delay(200)

    def _read_into_buffer(self):
        n = self.uart.any()
        
        if n:
            self.buffer += self.uart.read(n)

    def available(self):
        self._read_into_buffer()
        idx = self.buffer.find(self.HDR)

        if idx < 0:
            if len(self.buffer) > 100:  
                self.buffer = bytearray()
            
            return False
        
        if len(self.buffer) < idx + self.PKT_LEN:
            return False
        
        self.packet = self.buffer[idx : idx + self.PKT_LEN]
        self.buffer = self.buffer[idx + self.PKT_LEN :]
        return True

    def update(self):
        if not self.available():
            return None
        
        p = self.packet[6:]  # pula 6 bytes de header+length+cmd
        heading, pitch, roll = struct.unpack_from('<Hhh', p, 0)
        wx, wy, wz = struct.unpack_from('<hhh', p, 6)
        ax, ay, az = struct.unpack_from('<hhh', p, 12)
        self.a.update(ax, ay, az)
        self.w.update(wx, wy, wz)

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
