from objects.sensors.BNO85.analysis import Omega, Acceleration
from objects.wire.index import Wire
from time import sleep
import struct


class BNO085:
    def __init__(self, sda, scl):
        self.sda, self.scl = sda, scl
        self.a = Acceleration()
        self.w = Omega()
        self._seq_control = 0
        self.frequency    = 50

    def setup(self):
        report_interval = self.frequency * 100  
        self.address    = self.connect()
        sleep(0.1)

        def build(report_id, interval_us):
            period = interval_us
            period_bytes = period.to_bytes(4, 'little')
            payload = bytearray(17)
            payload[0]  = 0xFD          # Report ID do comando Set Feature
            payload[1]  = report_id     # ID do sensor/feature a configurar (ex.: 0x01 accel, 0x12 raw accel)
            payload[2]  = 0x00          # Feature flags (0 = normal)
            payload[3]  = 0x00          # Change sensitivity LSB (0 = desabilitado)
            payload[4]  = 0x00                    # Change sensitivity MSB
            payload[5:9]   = period_bytes         # Report interval (little-endian bytes)
            payload[9:13]  = b'\x00\x00\x00\x00'  # Batch interval (0 = sem batch, enviar imediatamente)
            payload[13:17] = b'\x00\x00\x00\x00'  # Sensor-specific config (não usado, preencher 0)
            
            # Monta cabeçalho SHTP (4 bytes: Length, Length, Channel, Sequence)
            packet_len = len(payload) + 2           # comprimento total incluindo canal+seq (2 bytes) 
            header = bytearray(4)                   # bytearray de 4 espaços
            header[0] = packet_len & 0xFF           # Length LSB
            header[1] = (packet_len >> 8) & 0xFF    # Length MSB (geralmente 0x00 aqui)
            header[2] = 0x02                        # Channel = 2 (SH-2 Control Channel)
            header[3] = self._seq_control & 0xFF    # Sequence number (incrementa a cada envio no canal)
            
            self._seq_control = (self._seq_control + 1) & 0xFF
            return header + payload

        packets = [
            build(0x01, report_interval),  # habilita acelerômetro calibrado
            build(0x02, report_interval),  # habilita giroscópio calibrado
            build(0x12, report_interval),  # habilita acelerômetro bruto
            build(0x13, report_interval),  # habilita giroscópio bruto
        ]

        for pkt in packets:
            try:
                self.wire._i2c.writeto(self.address, pkt)
            except Exception as e:
                print("Falha ao enviar comando SetFeature:", e)
            
            sleep(0.1)

    def update(self):
        try:
            header = self.wire._i2c.readfrom(self.address, 4)
        except Exception:
            return
        
        if not header or len(header) < 4:
            return

        packet_len = header[0] | (header[1] << 8)
        channel    = header[2]
        
        if packet_len == 0 or channel != 0x03:
            if packet_len > 2:
                try:
                    _ = self.wire._i2c.readfrom(self.address, packet_len - 2)
                except Exception:
                    pass
            return

        try:
            remaining_bytes = (packet_len - 2)
            data = self.wire._i2c.readfrom(self.address, remaining_bytes)
        except Exception:
            return
        
        if not data or len(data) < 1:
            return

        idx = 5 if data[0] == 0xFB else 0

        while idx < len(data):
            report_id = data[idx]
            
            if report_id == 0x12:  # Raw accel
                ax = struct.unpack('<h', data[idx+4:idx+6])[0]
                ay = struct.unpack('<h', data[idx+6:idx+8])[0]
                az = struct.unpack('<h', data[idx+8:idx+10])[0]
                self.a.update(ax, ay, az)
          
            elif report_id == 0x13:  # Raw Gyroscope
                wx = struct.unpack('<h', data[idx+4:idx+6])[0]
                wy = struct.unpack('<h', data[idx+6:idx+8])[0]
                wz = struct.unpack('<h', data[idx+8:idx+10])[0]
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

    def connect(self, retries=3):
        self.wire = Wire(0, self.sda, self.scl, freq=400000)

        for i in range(retries):
            if self.wire.address is not None:
                return self.wire.address
            
            print('Endereço não encontrado, tent', i+1, 'de', retries)
            sleep(1.0)

        if self.wire.address is not None:
            print(f'new address: {hex(self.wire.address)}')
        
        return self.wire.address
