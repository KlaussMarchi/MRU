import serial, serial.tools.list_ports, threading, json
from collections import deque
from time import time, sleep
from Utils.functions import sendEvent

SCALE = ['time', 'tmp', 'pitch', 'roll', 'yaw', 'ax', 'ay', 'az', 'wx', 'wy', 'wz', 'h']

# CAMPOS DE CADA LISTA PELO TAMANHO: OS LAYOUTS DO streamer DO firmware E O [t, pitch, roll] DO Table.ino
LAYOUTS = {
    3:  ['time', 'pitch', 'roll'],
    10: ['time', 'tmp', 'pitch', 'roll', 'yaw', 'q0', 'q1', 'q2', 'q3', 'h'],
    11: SCALE[1:],
    12: SCALE,
    20: SCALE + ['hr', 'inc', 'b_max', 'c_max', 'inc_max', 'arf', 'varf', 'svarf']
}

NMEA   = ['pitch', 'roll', 'yaw', 'h']    # $GPPASHR DO streamer
BAUDS  = [460800, 115200, 9600, 921600, 230400, 57600, 38400, 19200, 4800]    # AQUISIÇÃO, FÁBRICA E MODO NORMAL PRIMEIRO
LISTEN = 1.5    # s OUVINDO CADA PORTA E BAUD NA DESCOBERTA: CABE O STREAM MAIS LENTO DO MODO NORMAL


# O QUE O PACOTE É: SEM time É O FIRMWARE ANTIGO, ACELERAÇÃO NA CASA DE 1e6 É O g*1e6 DO RAW_MODE
def getLayout(values):
    if 'svarf' in values:
        return 'calibrated'

    if 'q0' in values:
        return 'quaternion'

    if 'ax' not in values:
        return 'nmea'

    if max(abs(values[key]) for key in ['ax', 'ay', 'az']) > 1000:
        return 'raw'

    return 'scale' if 'time' in values else 'legacy'


# UMA LINHA DO SERIAL NO PACOTE QUE ELA É: (tipo, layout, valores), COM TEXTO DE LOG COMO tipo 'text'
def parse(line):
    line = line.decode('ascii', errors='ignore').strip()

    if line.startswith('[') and line.endswith(']'):
        try:
            numbers = [float(value) for value in line[1:-1].split(',')]
        except ValueError:
            return None

        if len(numbers) not in LAYOUTS:
            return None

        values = dict(zip(LAYOUTS[len(numbers)], numbers))
        return ('table', 'table', values) if len(numbers) == 3 else ('mru', getLayout(values), values)

    if line.startswith('{') and line.endswith('}'):
        try:
            values = {key: float(value) for key, value in json.loads(line).items() if isinstance(value, (int, float))}
        except (json.JSONDecodeError, AttributeError):
            return None

        if set(values) == {'t', 'pitch', 'roll'}:    # O JSON DO Table2.ino, COM O TEMPO DA MESA
            return 'table', 'table', {'time': values['t'], 'pitch': values['pitch'], 'roll': values['roll']}

        return ('mru', getLayout(values), values) if 'pitch' in values else None

    if line.startswith('$GPPASHR') and '*' in line:
        content, checksum = line[1:].split('*', 1)
        parity = 0

        for char in content:
            parity ^= ord(char)

        if f'{parity:02X}' != checksum[:2].upper():
            return None

        try:
            values = dict(zip(NMEA, [float(value) for value in content.split(',')[1:]]))
        except ValueError:
            return None

        return 'mru', 'nmea', values

    return ('text', None, line) if line else None


# UMA PORTA SERIAL: LÊ NUMA THREAD PRÓPRIA, CARIMBA CADA PACOTE COM A HORA DE CHEGADA E VOLTA SOZINHA SE A PORTA CAIR
class Device:
    TIMEOUT = 0.05     # s DO read: A THREAD NUNCA FICA PRESA NEM GIRA EM VAZIO
    SPILL   = 4096     # bytes SEM FIM DE LINHA: É BAUD ERRADO, O RESTO VAI FORA

    def __init__(self, port, baud):
        self.port    = port
        self.baud    = baud
        self.serial  = None
        self.buffer  = b''
        self.packets = deque()
        self.errors  = 0
        self.running = False
        self.thread  = None

    def connect(self):
        try:
            self.serial = serial.Serial(self.port, self.baud, timeout=self.TIMEOUT)
            return True
        except (serial.SerialException, OSError):
            self.serial = None
            return False

    def start(self):
        self.running = True
        self.thread  = threading.Thread(target=self.listen, daemon=True)
        self.thread.start()

    def listen(self):
        while self.running:
            if self.serial is None and not self.connect():
                sleep(0.5)
                continue

            try:
                self.packets.extend(self.read())
            except (serial.SerialException, OSError):
                sendEvent('error', f'{self.port} caiu: reconectando')
                self.close()

    # O QUE CHEGOU, JÁ EM PACOTES COMPLETOS; A LINHA PELA METADE ESPERA O RESTO
    def read(self):
        chunk = self.serial.read(self.serial.in_waiting or 1)

        if not chunk:
            return []

        host = time()
        *lines, self.buffer = (self.buffer + chunk).split(b'\n')

        if len(self.buffer) > self.SPILL:
            self.buffer = b''

        packets = [parse(line) for line in lines]
        self.errors += sum(packet is None for packet in packets)
        return [(host, packet) for packet in packets if packet is not None]

    def collect(self, seconds):
        packets   = []
        startTime = time()

        while time() - startTime < seconds:
            packets.extend(self.read())

        return packets

    def send(self, message):
        try:
            self.serial.write(f'{message}\r\n'.encode())
            return True
        except (serial.SerialException, OSError, AttributeError):
            return False

    def close(self):
        if self.serial is not None:
            self.serial.close()

        self.serial = None
        self.buffer = b''

    def stop(self):
        self.running = False

        if self.thread is not None:
            self.thread.join(timeout=1.0)

        self.close()


# O USB NATIVO DO ESP32-S3 PRIMEIRO; NELE O BAUD É IGNORADO
def getPorts():
    ports = [port.device for port in serial.tools.list_ports.comports() if port.hwid != 'n/a']
    return sorted(ports, key=lambda port: 'ACM' not in port)


def getBauds(port):
    return [115200] if 'ACM' in port else BAUDS


# OUVE A PORTA NUM BAUD, MANDANDO ANTES O COMANDO SE HOUVER, E DIZ QUE APARELHO FALOU NELA
def probe(port, baud, command=None):
    device = Device(port, baud)

    if not device.connect():
        return None

    if command:
        device.send(command)

    kinds = [packet[0] for _, packet in device.collect(LISTEN) if packet[0] != 'text']
    device.close()
    return max(set(kinds), key=kinds.count) if kinds else None


# ACHA MRU E MESA: PRIMEIRO SÓ OUVINDO, PORQUE A MESA SAI ANDANDO NO PRIMEIRO BYTE; SÓ PEDE O STREAM SE O MRU ESTIVER MUDO
def discover(mruPort=None, tablePort=None):
    ports = [mruPort] if mruPort else [port for port in getPorts() if port != tablePort]
    found = {}

    for command in [None, '$stream_start!']:
        for port in ports:
            if port in found or any(kind == 'mru' for kind, _ in found.values()):
                continue

            for baud in getBauds(port):
                kind = probe(port, baud, command)

                if kind is not None:
                    found[port] = (kind, baud)
                    sendEvent('event', f'{kind} em {port} a {baud} bps')
                    break

    mru = next(((port, baud) for port, (kind, baud) in found.items() if kind == 'mru'), None)

    if mru is None:
        raise SystemExit('nenhum MRU respondeu: confira o cabo, a alimentação e o stream ($stream_start! ou autostream)')

    released = [port for port, (kind, _) in found.items() if kind == 'table']
    quiet    = [port for port in getPorts() if port not in found and port != mru[0]]
    port     = tablePort or (released + quiet + [None])[0]

    if port is None:
        sendEvent('event', 'sem mesa: só monitorando')
        return Device(*mru), None

    table = Device(port, 115200)    # Table.ino: Serial.begin(115200)

    if port in released:    # ELA JÁ ESTAVA ANDANDO: REINICIA PARA O TRECHO PARADO EXISTIR
        sendEvent('error', f'a mesa em {port} já estava andando: reiniciando, espere o homing antes do ensaio valer')
        table.connect()
        table.send('reset')
        table.close()

    sendEvent('event', f'mesa em {port}, parada até ser solta')
    return Device(*mru), table
