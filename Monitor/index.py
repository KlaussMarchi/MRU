from Device.index import discover
from Plotter.index import Plotter
from Utils.functions import sendEvent
from collections import deque
from statistics import median
from time import time, sleep
import pandas as pd
import numpy as np
from scipy.interpolate import make_smoothing_spline
import os, json, datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))
MRU_PORT   = None        # None PROCURA SOZINHO EM TODAS AS PORTAS E BAUDS; OU '/dev/ttyACM0', '/dev/ttyUSB1', 'COM5'
TABLE_PORT = None        # None USA A PORTA MUDA QUE SOBRAR: A MESA SÓ FALA DEPOIS DE SOLTA
PLOT       = True        # False SÓ GRAVA E MOSTRA O STATUS NO TERMINAL, PARA SESSÕES LONGAS
OUTPUT     = 'output'    # UMA PASTA POR SESSÃO, NADA É SOBRESCRITO


# UM APARELHO NA GRAVAÇÃO: O DIÁRIO EM DISCO, A TAXA, AS PERDAS PELO TEMPO DA AMOSTRA E A JANELA QUE A TELA MOSTRA
class Stream:
    def __init__(self, name, device, folder, window):
        self.name     = name
        self.device   = device
        self.path     = f'{folder}/{name}.jsonl'
        self.window   = window
        self.buffer   = deque()
        self.arrivals = deque()
        self.steps    = deque(maxlen=50)
        self.layouts  = {}
        self.count    = 0
        self.lost     = 0
        self.first    = None
        self.previous = None

    def start(self):
        self.journal = open(self.path, 'a')
        self.flushed = time()
        self.device.start()

    def update(self):
        while self.device.packets:
            host, (kind, layout, values) = self.device.packets.popleft()

            if kind == 'text':
                sendEvent(self.name, values)
                continue

            self.journal.write(json.dumps({'host': host, 'layout': layout, **values}) + '\n')
            self.layouts[layout] = self.layouts.get(layout, 0) + 1
            self.first = self.first or host
            self.count += 1
            self.arrivals.append(host)
            self.buffer.append((host, values))
            self.check(values.get('time'))

        now = time()

        while self.arrivals and now - self.arrivals[0] > 1.0:
            self.arrivals.popleft()

        while self.buffer and now - self.buffer[0][0] > self.window:
            self.buffer.popleft()

        if now - self.flushed > 1.0:    # NO MÁXIMO UM SEGUNDO SE PERDE SE O PC CAIR
            self.journal.flush()
            self.flushed = now

    # PACOTE QUE FALTOU: SALTO NO TEMPO DA AMOSTRA MAIOR QUE 1,5 PERÍODO; TEMPO VOLTANDO É O APARELHO REINICIANDO
    def check(self, stamp):
        if stamp is None:
            return

        if self.previous is not None and stamp > self.previous:
            step    = stamp - self.previous
            nominal = median(self.steps) if self.steps else step

            if step > 1.5*nominal:
                self.lost += round(step/nominal) - 1
            else:
                self.steps.append(step)

        self.previous = stamp

    def getLayout(self):
        return max(self.layouts, key=self.layouts.get) if self.layouts else None

    def info(self):
        return {'port': self.device.port, 'baud': self.device.baud, 'samples': self.count, 'lost': self.lost, 'bad_lines': self.device.errors, 'layouts': self.layouts}

    def getStatus(self):
        return f'{self.name} {self.device.port} · {self.getLayout()} · {len(self.arrivals)} Hz · {self.count} amostras · {self.lost} perdidas'

    # O DIÁRIO NO RELÓGIO DO PC: O DO APARELHO DESLOCADO PELO MENOR ATRASO DE CHEGADA, UM DESLOCAMENTO POR REINÍCIO
    def load(self):
        frame = pd.read_json(self.path, lines=True)

        if frame.empty:
            return frame

        if 'time' not in frame:
            return frame.rename(columns={'host': 'time'})

        segment       = (frame.time.diff() < 0).cumsum()
        offset        = (frame.host - frame.time).groupby(segment).transform(lambda part: part.quantile(0.01))
        frame['time'] = (frame.time + offset).fillna(frame.host)
        return frame.drop(columns='host')

    def stop(self):
        self.device.stop()
        self.journal.close()


# O ENSAIO OU A MONITORAÇÃO: MRU SEMPRE, MESA QUANDO HÁ ENSAIO; SEGURA A MESA PARADA, SOLTA E NO FIM MONTA OS CSV DO Calibration
class Monitor:
    STILL     = 20.0    # s PARADO ANTES DE SOLTAR A MESA: O TRECHO static QUE A CALIBRAÇÃO MEDE
    TOLERANCE = 0.2     # s ENTRE A AMOSTRA DO MRU E A DA MESA NO CASAMENTO
    STEADY    = 0.1     # graus DE EXCURSÃO DA MESA EM 1 s: ABAIXO DISSO A LINHA É static
    WINDOW    = 20.0    # s NA TELA
    ANSWER    = 3.0     # s ESPERANDO A MESA FALAR DEPOIS DE SOLTA

    def __init__(self, mru, table, output):
        self.folder    = os.path.join(output, datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        self.target    = Stream('target', mru, self.folder, self.WINDOW)
        self.reference = Stream('reference', table, self.folder, self.WINDOW) if table else None
        self.streams   = [stream for stream in [self.target, self.reference] if stream]
        self.released  = None
        self.warnings  = []

    def start(self):
        os.makedirs(self.folder, exist_ok=True)
        self.startTime = time()

        for stream in self.streams:
            stream.start()

        sendEvent('event', f'gravando em {self.folder}')

    def update(self):
        for stream in self.streams:
            stream.update()

        if self.reference is None or self.target.first is None:
            return

        now = time()

        if self.released is None and now - self.target.first >= self.STILL:
            self.reference.device.send('start')    # QUALQUER BYTE SOLTA A MESA; 'reset' É O ÚNICO COMANDO QUE ELA TRATA
            self.released = now - self.startTime
            sendEvent('event', f'mesa solta em {self.released:.1f} s')

        if self.released is not None and self.reference.count == 0 and now - self.startTime > self.released + self.ANSWER:
            self.warn(f'a mesa em {self.reference.device.port} não respondeu depois de solta: a sessão segue só monitorando')

        if self.target.getLayout() not in [None, 'scale']:
            self.warn(f'o MRU está em {self.target.getLayout()}: para calibrar mande CF:device_mode$1! (ou CF:streamer_mode$2!) e grave de novo')

    def warn(self, message):
        if message in self.warnings:
            return

        self.warnings.append(message)
        sendEvent('error', message)

    def getStatus(self):
        status = [stream.getStatus() for stream in self.streams]

        if self.released is not None:
            status.append(f'mesa solta em {self.released:.0f} s')

        return '   |   '.join(status)

    def stop(self):
        for stream in self.streams:
            stream.stop()

    # FORMATO DO Calibration: UMA LINHA POR AMOSTRA DO MRU NA ESCALA, COM A MESA SUAVIZADA NO INSTANTE DELA
    def merge(self, target, reference):
        target = target[target.layout == 'scale'].drop(columns='layout').dropna(axis=1, how='all')

        if target.empty or len(reference) < 5:    # A SPLINE SUAVIZADA PEDE CINCO PONTOS
            return None

        target    = target.add_prefix('target_').rename(columns={'target_time': 'time'}).sort_values('time')
        reference = reference[['time', 'pitch', 'roll']].add_prefix('ref_').rename(columns={'ref_time': 'time'}).sort_values('time').drop_duplicates('time')
        angles    = ['ref_pitch', 'ref_roll']

        data            = pd.merge_asof(target, reference, on='time', direction='nearest', tolerance=self.TOLERANCE)
        near            = data[angles].notna()
        data[angles]    = np.c_[[make_smoothing_spline(reference.time, reference[angle])(data.time) for angle in angles]].T    # O Format E O 4 - Heave DERIVAM DUAS VEZES: PACOTE A 10 Hz EM DEGRAUS DE 0,025° VIRARIA PICO
        data[angles]    = data[angles].where(near).bfill().ffill()    # ANTES DO PRIMEIRO PACOTE A MESA ESTÁ PARADA NA POSIÇÃO INICIAL
        data['ref_yaw'] = 0.0                             # A MESA SÓ TEM OS EIXOS DE ROLAGEM E ARFAGEM

        window = max(int(round(1.0 / data.time.diff().median())), 1)
        swing  = data[angles].rolling(window, min_periods=1, center=True)    # PARADO ANTES E DEPOIS: A PARTIDA DA MESA TEM O PICO DO BRAÇO
        data['static'] = (swing.max() - swing.min()).max(axis=1) < self.STEADY

        columns = [column for column in data.columns if column.startswith(('target_', 'ref_'))]
        return data[['time', 'static'] + columns]

    def save(self):
        frames = {stream.name: stream.load() for stream in self.streams}
        start  = min([frame.time.min() for frame in frames.values() if not frame.empty] or [0])

        for name, frame in frames.items():
            if not frame.empty:
                frame['time'] -= start
                frame.to_csv(f'{self.folder}/{name}.csv', index=False)

        data = self.merge(frames['target'], frames['reference']) if self.reference and not frames['target'].empty else None

        info = {
            'description': 'target = MRU em teste, ref = mesa (TableMotor)',
            'devices': {stream.name: stream.info() for stream in self.streams},
            'still': self.STILL,
            'released': self.released,
            'calibration': data is not None,
            'warnings': self.warnings
        }

        if data is not None:
            data.to_csv(f'{self.folder}/data.csv', index=False)
            info |= {'data': len(data), 'static': int(data.static.sum()), 'rate': round(1 / data.time.diff().median(), 2)}

        with open(f'{self.folder}/info.json', 'w') as file:
            file.write(json.dumps(info, indent=4))

        for stream in self.streams:
            os.remove(stream.path)

        if data is None:
            return sendEvent('event', f'{self.target.count} amostras do MRU em {self.folder}/target.csv (sem data.csv: falta mesa ou o MRU não estava na escala)')

        return sendEvent('event', f'{len(data)} linhas, {int(data.static.sum())} paradas, em {self.folder}/data.csv')


monitor = Monitor(*discover(MRU_PORT, TABLE_PORT), OUTPUT)
monitor.start()

try:
    if PLOT:
        Plotter(monitor).start()

    while not PLOT:
        monitor.update()
        print(monitor.getStatus(), end='\r')
        sleep(0.2)
except KeyboardInterrupt:
    print()
finally:
    monitor.stop()
    monitor.save()
