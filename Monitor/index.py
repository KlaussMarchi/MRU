from Device.index import Device
from Plotter.index import TimeGraph
from Utils.classes import AsyncThreading, KeyboardListener
from Utils.functions import sendEvent
from time import time, sleep
import numpy as np
import pandas as pd
import os, shutil, json

script_path = os.path.abspath(__file__)
base_dir = os.path.dirname(script_path)
os.chdir(base_dir)

MRU   = ['tmp', 'pitch', 'roll', 'yaw', 'ax', 'ay', 'az', 'wx', 'wy', 'wz', 'h']    # printList() DO firmware EM HR/OR
TABLE = ['board', 'pitch', 'roll']                                                   # print() DO Table.ino: [t, pitch, roll]

MRU_PORT   = '/dev/ttyACM0'    # USB NATIVO DO ESP32-S3
MRU_RATE   = 115200            # NO USB-CDC O VALOR É IGNORADO; PELA RS232 O firmware USA 9600
TABLE_PORT = '/dev/ttyUSB0'    # CONVERSOR USB DO ESP32 DA MESA
TABLE_RATE = 115200            # Table.ino: Serial.begin(115200)

def setFolder(folder):
    if os.path.exists(folder):
        shutil.rmtree(folder)
    os.makedirs(folder)

class Monitor:
    INDEPENDENT = True
    NORMALIZE   = False
    STILL       = 20.0    # s PARADO ANTES DE SOLTAR A MESA: É O TRECHO static QUE A CALIBRAÇÃO MEDE
    TOLERANCE   = 0.2     # s: DISTÂNCIA MÁXIMA ENTRE A AMOSTRA DO MRU E A DA MESA NO CASAMENTO
    STEADY      = 0.1     # graus DE EXCURSÃO DA MESA EM 1 s: ABAIXO DISSO A LINHA É static

    def __init__(self, targets=['pitchM']):
        self.kb = KeyboardListener()
        self.kb.start()
        self.current = None
        self.valuesM = []
        self.valuesP = []
        self.targets = targets
        self.startProg = None
        self.released = None
        self.SAVE = True
        self.stats = {}

    def setup(self):
        self.deviceM = Device(port=MRU_PORT, rate=MRU_RATE, keys=MRU)
        self.deviceP = Device(port=TABLE_PORT, rate=TABLE_RATE, keys=TABLE)

        self.deviceM.connect()
        self.deviceP.connect()
        self.startTime = time()

        sleep(2.00)
        self.check()

        self.threadM = AsyncThreading(self.handleMeasure)
        self.threadP = AsyncThreading(self.handlePlate)

    # A MESA SÓ FALA DEPOIS DO PRIMEIRO BYTE, ENTÃO QUEM RESPONDE AO stream_start É O MRU
    def check(self):
        self.deviceM.send('$stream_start!')
        sleep(2.00)

        if self.deviceM.getList() is not None:
            return sendEvent('event', f'MRU em {self.deviceM.port}, mesa em {self.deviceP.port}')

        sendEvent('event', f'sem pacote de {len(MRU)} valores em {self.deviceM.port}: tentando a outra porta')
        self.deviceM, self.deviceP = self.deviceP, self.deviceM
        self.deviceM.keys, self.deviceP.keys = MRU, TABLE
        self.deviceP.send('reset')    # O stream_start JÁ SOLTOU A MESA: VOLTA PARA ZERO E ESPERA O BYTE DE NOVO

        self.deviceM.send('$stream_start!')
        sleep(2.00)

        if self.deviceM.getList() is None:
            return sendEvent('error', 'nenhuma das portas respondeu com o pacote do MRU')

        return sendEvent('event', f'cabos invertidos: MRU em {self.deviceM.port}, mesa em {self.deviceP.port}')

    def handleMeasure(self):
        if not self.deviceM.available():
            return
        
        self.deviceM.last = self.deviceM.getList()

    def handlePlate(self):
        if not self.deviceP.available():
            return
        
        self.deviceP.last = self.deviceP.getList()

    def handle(self):
        measure_working   = self.deviceM.last is not None
        plate_working     = self.deviceP.last is not None

        if self.INDEPENDENT and (not measure_working and not plate_working):
            return

        if not self.INDEPENDENT and (not measure_working or not plate_working):
            return
        
        if self.startProg is None:
            self.startProg = time()

        passed = time() - self.startProg

        if self.released is None and passed >= self.STILL:
            self.released = passed
            self.deviceP.send('start')    # QUALQUER BYTE SOLTA A MESA; 'reset' É O ÚNICO COMANDO QUE ELA TRATA
            sendEvent('event', f'mesa liberada em {passed:.1f} s')

        sendEvent('measure', ('working'   if measure_working else 'failed')   + f': {str(self.deviceM.last)[:100]}',   'green' if measure_working else 'red')
        sendEvent('plate', ('working' if plate_working else 'failed') + f': {str(self.deviceP.last)[:100]}', 'green' if plate_working else 'red')
        sendEvent('time', passed, 'blue')
        print()
        
        if measure_working:
            self.deviceM.last['time'] = passed

        if plate_working:
            self.deviceP.last['time'] = passed
            
        if self.current is None:
            self.current = {target: 0.5 for target in self.targets}
            
        for target in self.targets:
            val = None
            if target.endswith('M') and measure_working:
                val = self.deviceM.last.get(target[:-1])

            if target.endswith('P') and plate_working:
                val = self.deviceP.last.get(target[:-1])
                
            if val is not None:
                if target not in self.stats:
                    self.stats[target] = {'min': val, 'max': val}
                
                self.stats[target]['min'] = min(self.stats[target]['min'], val)
                self.stats[target]['max'] = max(self.stats[target]['max'], val)
                
                vmin = self.stats[target]['min']
                vmax = self.stats[target]['max']
                
                if self.NORMALIZE:
                    if vmax - vmin == 0:
                        norm_val = 0.5
                    else:
                        norm_val = (val - vmin) / (vmax - vmin)
                        
                    self.current[target] = norm_val
                else:
                    self.current[target] = val
            
        if measure_working:
            self.valuesM.append(self.deviceM.last)
            self.deviceM.last = None

        if plate_working:
            self.valuesP.append(self.deviceP.last)
            self.deviceP.last = None

    def get(self):
        if self.current is None:
            return

        if self.kb.is_pressed('n'):
            self.NORMALIZE = not self.NORMALIZE
            self.reset()
            print(f"\n[INFO] Normalization: {'ON' if self.NORMALIZE else 'OFF'}")

        if self.kb.is_pressed('p'):
            self.targets = ['pitchM']; self.reset()

        if self.kb.is_pressed('r'):
            self.targets = ['rollM']; self.reset()

        if self.kb.is_pressed('y'):
            self.targets = ['yawM']; self.reset()

        if self.kb.is_pressed('h'):
            self.targets = ['hM']; self.reset()

        if self.kb.is_pressed('k'):
            self.targets = ['pitchM']; self.reset()

        if self.kb.is_pressed('w'):
            self.targets = ['wxM']; self.reset()

        if self.kb.is_pressed('a'):
            self.targets = ['axM']; self.reset()

        if self.kb.is_pressed('o'):
            self.targets = ['q0M']; self.reset()
                    
        return (time() - self.startTime, self.current)

    def reset(self):
        self.stats = {} # Limpa os stats para re-normalizar com a nova variavel
        self.graph.need_reset = True
        self.startTime = time()
        self.current = None

    def saveDevice(self, data, device, folder):
        if not data:
            return pd.DataFrame().to_csv(os.path.join(folder, device, 'data.csv'), index=False)
        
        keys = set()
        for record in data:
            keys.update(record.keys())

        data = [{key: record.get(key, 0) for key in keys} for record in data]
        df = pd.DataFrame(data)
        df.to_csv(os.path.join(folder, device, 'data.csv'), index=False)
            
    # FORMATO QUE O Calibration ESPERA: UMA LINHA POR AMOSTRA DO MRU, COM A MESA SEGURADA NO INSTANTE MAIS PRÓXIMO
    def merge(self):
        if not self.valuesM or not self.valuesP:
            return None

        target = pd.DataFrame(self.valuesM).add_prefix('target_').rename(columns={'target_time': 'time'}).sort_values('time')
        plate  = pd.DataFrame(self.valuesP).drop(columns='board').add_prefix('ref_').rename(columns={'ref_time': 'time'}).sort_values('time')
        angles = ['ref_pitch', 'ref_roll']

        data = pd.merge_asof(target, plate, on='time', direction='nearest', tolerance=self.TOLERANCE)
        data[angles] = data[angles].bfill().ffill()    # ANTES DO PRIMEIRO PACOTE A MESA ESTÁ PARADA NA POSIÇÃO INICIAL
        data['ref_yaw'] = 0.0                          # A MESA SÓ TEM OS EIXOS DE ROLAGEM E ARFAGEM

        window = max(int(round(1.0 / data.time.diff().median())), 1)
        swing  = data[angles].rolling(window, min_periods=1)
        data['static'] = (swing.max() - swing.min()).max(axis=1) < self.STEADY

        columns = [column for column in data.columns if column.startswith(('target_', 'ref_'))]
        return data[['time', 'static'] + columns]

    def save(self, folder='output'):
        setFolder(os.path.join(folder, 'reference'))
        setFolder(os.path.join(folder, 'target'))

        self.saveDevice(self.valuesM, 'target', folder)
        self.saveDevice(self.valuesP, 'reference', folder)
        data = self.merge()

        if data is None:
            return sendEvent('error', 'faltou pacote de um dos aparelhos: data.csv não foi gerado')

        data.to_csv(os.path.join(folder, 'data.csv'), index=False)

        with open(os.path.join(folder, 'info.json'), 'w') as file:
            file.write(json.dumps({
                'description': 'target = MRU em teste, ref = mesa (TableMotor)',
                'samples': {'target': len(self.valuesM), 'reference': len(self.valuesP), 'data': len(data)},
                'static': int(data.static.sum()),
                'rate': round(1 / data.time.diff().median(), 2),
                'still': self.STILL
            }, indent=4))

        return sendEvent('event', f'{len(data)} linhas, {int(data.static.sum())} paradas, em {folder}/data.csv')


if __name__ == '__main__':
    monitor = Monitor()
    monitor.setup()
    thread = AsyncThreading(monitor.handle, interval=0.001)

    try:
        graph = TimeGraph(callback=monitor.get, xLim=[0, 20])
        monitor.graph = graph
        graph.start()
    except Exception as error:
        print('error: ', error)
    finally:      
        if monitor.SAVE:
            print('\nsalvando database')
            monitor.save()
