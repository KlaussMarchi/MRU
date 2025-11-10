from objects.sensors.KERNEL.analysis import Acceleration, Omega
from machine import UART, Pin
from time import sleep_ms as delay
from utime import ticks_ms as millis


# True = GA Data (bruto), False = Orientation (processado)
DEBUG = True


class KernelSensor:
    CMD_ORIENTATION = bytes([0xAA, 0x55, 0x00, 0x00, 0x07, 0x00, 0x33, 0x3A, 0x00])
    CMD_GA_DATA     = bytes([0xAA, 0x55, 0x00, 0x00, 0x07, 0x00, 0x8F, 0x96, 0x00])
    
    PKT_LEN = 40 if DEBUG else 42
    #PKT_LEN = 42 if DEBUG else 44      # (header+tipo/id+len+payload+CRC)
    KG = 100000.0  if DEBUG else 10.0  # - GA (bruto): gyro = deg/s * 1e5 ; acc = g * 1e6
    KA = 1000000.0 if DEBUG else 500.0 # - Orientation: gyro = deg/s * KG ; acc = g * KA (valores do ICD)

    def __init__(self, tx_pin, rx_pin):
        print(f'Kernel Started at tx={tx_pin} and rx={rx_pin}')
        delay(1000)
        self.uart   = UART(1, baudrate=115200, tx=Pin(tx_pin), rx=Pin(rx_pin))
        self.packet = bytearray(self.PKT_LEN)
        self.header = False
        self.index  = 0
        self.lastUpdate = millis()

        self.a = Acceleration()
        self.w = Omega()
        self.temp    = 0
        self.heading = 0.0
        self.pitch   = 0.0
        self.roll    = 0.0

    def setup(self):
        print('Modo de saída:', 'GA_DATA (raw)' if DEBUG else 'ORIENTATION (filtered)')
        delay(1000)

        self.uart.write(self.CMD_GA_DATA if DEBUG else self.CMD_ORIENTATION)
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
                if self.index == 0 and newByte == 0xAA:
                    self.packet[0] = 0xAA
                    self.index = 1
                    continue
                if self.index == 1 and newByte == 0x55:
                    self.packet[1] = 0x55
                    self.header = True
                    self.index  = 2
                else:
                    # perdeu sync; recomeça procurando 0xAA
                    self.index = 0
                continue
            
            if self.index < self.PKT_LEN:
                self.packet[self.index] = newByte
                self.index = (self.index + 1)

            if self.index >= self.PKT_LEN:
                return True

        return False

    def update(self):
        if not self.available():
            return None

        total = self.PKT_LEN
        ps    = 6 # payload start
        calc_checksum = sum(self.packet[2: total-2]) & 0xFFFF
        recv_checksum = self.packet[total-2] | (self.packet[total-1] << 8)

        if calc_checksum != recv_checksum:
            print('Checksum inválido!')
            self.reset()
            return None

        if DEBUG:
            wx = int.from_bytes(self.packet[ps+0 : ps+4 ], 'little', True) / self.KG  # deg/s
            wy = int.from_bytes(self.packet[ps+4 : ps+8 ], 'little', True) / self.KG
            wz = int.from_bytes(self.packet[ps+8 : ps+12], 'little', True) / self.KG

            ax = int.from_bytes(self.packet[ps+12: ps+16], 'little', True) / self.KA  # g
            ay = int.from_bytes(self.packet[ps+16: ps+20], 'little', True) / self.KA
            az = int.from_bytes(self.packet[ps+20: ps+24], 'little', True) / self.KA
            self.temp = int.from_bytes(self.packet[ps+30: ps+32], 'little', True) / 10.0

            self.a.update(ax, ay, az)
            self.w.update(wx, wy, wz)
            self.reset()
            return True

        self.heading = int.from_bytes(self.packet[ps+0: ps+2], 'little', False) / 100.0
        self.pitch   = int.from_bytes(self.packet[ps+2: ps+4], 'little', True ) / 100.0
        self.roll    = int.from_bytes(self.packet[ps+4: ps+6], 'little', True ) / 100.0

        wx = int.from_bytes(self.packet[ps+6:  ps+8 ], 'little', True) / self.KG
        wy = int.from_bytes(self.packet[ps+8:  ps+10], 'little', True) / self.KG
        wz = int.from_bytes(self.packet[ps+10: ps+12], 'little', True) / self.KG

        ax = int.from_bytes(self.packet[ps+12: ps+14], 'little', True) / self.KA
        ay = int.from_bytes(self.packet[ps+14: ps+16], 'little', True) / self.KA
        az = int.from_bytes(self.packet[ps+16: ps+18], 'little', True) / self.KA
        self.temp = int.from_bytes(self.packet[ps+32: ps+34], 'little', True) / 10.0

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
