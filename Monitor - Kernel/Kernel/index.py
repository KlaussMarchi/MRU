import serial, time, struct, math
from Kernel.variables import BAUD_RATES
from time import sleep


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
# KERNEL SENSOR RAW!!!
G_TO_MS2 = 9.8106          # fator g→m/s²
DEG_TO_RAD = math.pi / 180


class KernelSensor:
    # —— Comandos (tabela A.1) ——
    CMD_ORIENTATION = bytes.fromhex('AA 55 00 00 07 00 33 3A 00')
    CMD_GA          = bytes.fromhex('AA 55 00 00 07 00 8F 96 00')
    CMD_GAM         = bytes.fromhex('AA 55 00 00 07 00 9B A2 00')

    MSG_HEADER = b'\xAA\x55'

    def __init__(self, port='COM5'):
        self.port      = port
        self.cmd_start = self.CMD_GA
        self.msg_total_len = 40

        self.buffer  = bytearray()
        self.packet  = None
        self.last    = None

    # ————————————————————————————————————
    # Conexão e ativação do modo escolhido
    def connect(self, baud=115200):
        self.device = serial.Serial(self.port, baud, timeout=5.0)
        self.device.write(self.cmd_start)
        time.sleep(0.1)

    # ————————————————————————————————————
    # Parsing de acordo com o formato ativo
    def parse_orientation(self):
        p = self.packet[6:]                 # pula header+len
        heading, pitch, roll = struct.unpack_from('<Hhh', p, 0)
        wx, wy, wz           = struct.unpack_from('<hhh', p, 6)
        ax, ay, az           = struct.unpack_from('<hhh', p, 12)

        return {
            'yaw' : heading / 100.0,
            'pitch': pitch  / 100.0,
            'roll' : roll   / 100.0,
            'wx_dps': wx, 'wy_dps': wy, 'wz_dps': wz,      # deg/s * KG
            'ax_g' : ax, 'ay_g' : ay, 'az_g' : az          # g * KA
        }

    def parse_ga(self):
        p = self.packet[6:]
        wx, wy, wz = struct.unpack_from('<iii', p, 0)      # deg/s * 1e5
        ax, ay, az = struct.unpack_from('<iii', p, 12)     # g     * 1e6

        return {
            'wx' : wx / 1e5 * DEG_TO_RAD,   # rad/s
            'wy' : wy / 1e5 * DEG_TO_RAD,
            'wz' : wz / 1e5 * DEG_TO_RAD,
            'ax' : ax / 1e6 * G_TO_MS2,     # m/s²
            'ay' : ay / 1e6 * G_TO_MS2,
            'az' : az / 1e6 * G_TO_MS2
        }
    
    def getJson(self):
        return self.parse_ga()              # GA ou GAm

    def raw(self):
        return self.packet.hex(' ')

    # ————————————————————————————————————
    # Leitura de novos frames
    def available(self):
        size = self.device.in_waiting
        if not size:
            return False

        self.buffer += self.device.read(size)

        while True:
            idx = self.buffer.find(self.MSG_HEADER)
            if idx == -1:
                return False

            if len(self.buffer) < idx + self.msg_total_len:
                return False

            self.packet = self.buffer[idx : idx + self.msg_total_len]
            # descarta o frame que acabou de pegar
            del self.buffer[:idx + self.msg_total_len]
            return True

    # ————————————————————————————————————
    # Exemplo de alteração de parâmetros (permaneceu igual)
    def set(self, key, value):
        header = b'\xAA\x55\x00\x00'
        cmd    = bytearray([0xB2, 0xFF])

        if key == 'baudRate':
            code = BAUD_RATES[value]
            cmd += b'\xB2\x00' + b'\x01\x00' + bytes([code])

        elif key == 'frequency':
            cmd += b'\x12\x00' + b'\x02\x00' + struct.pack('<H', value)

        else:
            raise ValueError('parâmetro desconhecido')

        pkt_len = len(cmd) + 6
        packet  = header + struct.pack('<H', pkt_len) + cmd
        cs      = struct.pack('<H', sum(packet[2:]) & 0xFFFF)
        self.device.write(packet + cs)
        sleep(0.2)

    def stream(self):
        if not self.available():
            return
        
        self.last = self.getJson()  
"""