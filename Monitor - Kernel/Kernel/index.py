import serial, time, struct
from Kernel.variables import BAUD_RATES
from time import sleep


"""
class KernelSensor:
    CONFIG_ORIENTATION = bytes.fromhex('AA 55 00 00 07 00 33 3A 00')
    MSG_HEADER = b'\xAA\x55'  # início de qualquer mensagem
    MSG_TOTAL_LEN = 42   
    
    def __init__(self):
        self.buffer = bytearray()
        self.packet = None
        self.last   = None
        self.port = 'COM5'

    def connect(self):
        self.device = serial.Serial(self.port, 115200, timeout=5.0)
        self.device.write(self.CONFIG_ORIENTATION)
        time.sleep(0.1)

    def stream(self):
        self.streaming = True

    def getJson(self):
        payload = self.packet[6:]
        heading, pitch, roll = struct.unpack_from('<Hhh', payload, 0)
        wx, wy, wz = struct.unpack_from('<hhh', payload, 6)
        ax, ay, az = struct.unpack_from('<hhh', payload, 12)

        return {
            'pitch': pitch/100.0,
            'roll': roll/100.0,
            'yaw': heading/100.0,
            'wx': wx , 
            'wy': wy, 
            'wz': wz,
            'ax': ax, 
            'ay': ay, 
            'az': az
        }
    
    def raw(self):
        return self.packet.hex(' ')

    def available(self):
        size = self.device.in_waiting

        if size == 0:
            return False
        
        self.buffer += self.device.read(size)

        while True:
            index = self.buffer.find(self.MSG_HEADER)

            if index == -1:
                return False

            if len(self.buffer) < index + self.MSG_TOTAL_LEN:
                return False

            start = index
            end   = index + self.MSG_TOTAL_LEN
            self.packet = self.buffer[start:end]
            self.buffer = self.buffer[start + self.MSG_TOTAL_LEN:]          
            return True
    
    def set(self, key, value):
        header = bytes.fromhex('AA 55 00 00')
        cmd    = bytearray([0xB2, 0xFF])

        if key == 'baudRate':
            code = BAUD_RATES.get(value)
            cmd += b'\xB2\x00'   
            cmd += b'\x01\x00'
            cmd += bytes([code])

        if key == 'frequency':
            cmd += b'\x12\x00' 
            cmd += b'\x02\x00' 
            cmd += struct.pack('<H', value)

        # Calcula length = payload + 6 bytes de overhea
        length = len(cmd) + 6
        length_bytes = struct.pack('<H', length)

        # Monta pacote sem checksum
        packet_wo_cs = header + length_bytes + cmd

        # Calcula e anexa checksum
        cs = struct.pack('<H', sum(packet_wo_cs[2:]) & 0xFFFF)
        packet = packet_wo_cs + cs

        # Envia ao dispositivo
        self.device.write(packet)
        sleep(0.2)

    def stream(self):
        if not self.available():
            return
        
        self.last = self.getJson()   
"""


class KernelSensor:
    # Comando para Calibrated HR Data
    CONFIG_CALIBHR = bytes.fromhex('AA 55 00 00 07 00 91 98 00')
    MSG_HEADER = b'\xAA\x55'  # Início de qualquer mensagem
    MSG_TOTAL_LEN = 61  # Tamanho total da mensagem Calibrated HR Data
    
    def __init__(self):
        self.buffer = bytearray()
        self.packet = None
        self.last = None
        self.port = 'COM5'

    def connect(self):
        self.device = serial.Serial(self.port, 115200, timeout=5.0)
        self.device.write(self.CONFIG_CALIBHR)  # Usa Calibrated HR Data
        time.sleep(0.1)

    def stream(self):
        self.streaming = True

    def getJson(self):
        payload = self.packet[7:]  # Pula header (2), reserved (2), length (2), code (1)
        # Desempacota giroscópios e acelerômetros como floats
        wx, wy, wz = struct.unpack_from('<fff', payload, 0)  # Bytes 0-11
        ax, ay, az = struct.unpack_from('<fff', payload, 12)  # Bytes 12-23

        return {
            'wx': wx,  # deg/s
            'wy': wy,  # deg/s
            'wz': wz,  # deg/s
            'ax': ax,  # g
            'ay': ay,  # g
            'az': az   # g
        }
    
    def raw(self):
        return self.packet.hex(' ')

    def available(self):
        size = self.device.in_waiting

        if size == 0:
            return False
        
        self.buffer += self.device.read(size)

        while True:
            index = self.buffer.find(self.MSG_HEADER)

            if index == -1:
                return False

            if len(self.buffer) < index + self.MSG_TOTAL_LEN:
                return False

            start = index
            end = index + self.MSG_TOTAL_LEN
            self.packet = self.buffer[start:end]
            self.buffer = self.buffer[start + self.MSG_TOTAL_LEN:]          
            return True
    
    def set(self, key, value):
        header = bytes.fromhex('AA 55 00 00')
        cmd = bytearray([0xB2, 0xFF])

        if key == 'baudRate':
            code = BAUD_RATES.get(value)
            cmd += b'\xB2\x00'   
            cmd += b'\x01\x00'
            cmd += bytes([code])

        if key == 'frequency':
            cmd += b'\x12\x00' 
            cmd += b'\x02\x00' 
            cmd += struct.pack('<H', value)

        length = len(cmd) + 6
        length_bytes = struct.pack('<H', length)
        packet_wo_cs = header + length_bytes + cmd
        cs = struct.pack('<H', sum(packet_wo_cs[2:]) & 0xFFFF)
        packet = packet_wo_cs + cs
        self.device.write(packet)
        sleep(0.2)

    def stream(self):
        if not self.available():
            return
        
        self.last = self.getJson()