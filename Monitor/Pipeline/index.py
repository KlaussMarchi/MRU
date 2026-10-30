import os
os.environ.update({'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'})    # ANTES DO numpy: OS WORKERS DO Nature NÃO DISPUTAM NÚCLEOS

import sys, json, time, shutil, datetime, traceback
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import Nature.index as nature
from Format.index import Format
from Filters.index import Filters
from Correction.index import Correction
from Attitude.KalmanFusion.index import KalmanFusion
from Attitude.LinearFit.index import LinearFit
from Attitude.MachineLearning.index import MachineLearning
from Heave.index import Heave
from Lever.index import Lever
from Analysis.index import Analysis
from Certificate.index import Certificate
from Firmware.index import Firmware

STAGES  = [('format', 'Format', 1), ('filters', 'Filtros', 7), ('correction', 'Correção', 1), ('attitude', 'Atitude', 0), ('heave', 'Heave', 4), ('lever', 'Braço de alavanca', 1), ('analysis', 'Análise', 1), ('certificate', 'Certificado', 3)]    # s TÍPICOS A 200 Hz
ATTITUDE = {'KalmanFusion': 200, 'LinearFit': 1, 'MachineLearning': 3}    # s TÍPICOS DA ATITUDE DE CADA ESTRATÉGIA, NO LUGAR DO 0 DE CIMA
GRAVITY = 9.785    # m/s² LOCAL DO LABORATÓRIO QUANDO O PEDIDO NÃO TRAZ
EVERY   = 0.5      # s ENTRE DOIS EVENTOS DE PROGRESSO
EVENTS  = None


def send(event, **data):
    EVENTS.write(json.dumps({'event': event, **data}, ensure_ascii=False, default=float) + '\n')
    EVENTS.flush()


# O ANDAMENTO DO PIPELINE NUMA ESCALA SÓ: CADA ETAPA PESA O SEU TEMPO TÍPICO, CADA BUSCA DO Nature ANDA DENTRO DO PEDAÇO DELA
class Progress:
    def __init__(self, strategy):
        self.weights = [ATTITUDE[strategy] if key == 'attitude' else weight for key, _, weight in STAGES]
        self.total   = sum(self.weights)
        self.offset  = 0
        self.weight  = 0
        self.label   = ''
        self.base    = 0
        self.span    = 0
        self.sent    = 0
        self.message = ''

    def stage(self, key):
        index        = [name for name, _, _ in STAGES].index(key)
        self.offset  = sum(self.weights[:index])
        self.weight  = self.weights[index]
        self.label   = STAGES[index][1]
        self.report(0, 'começando', 0)

    def report(self, fraction, message, span=0):
        self.base, self.span, self.message = fraction, span, message
        self.update(0, force=True)

    def update(self, inside, force=False):
        if not force and time.time() - self.sent < EVERY:
            return

        self.sent = time.time()
        send('progress', step=self.offset + self.weight*(self.base + self.span*inside), steps=self.total, stage=self.label, message=self.message)


# A BARRA DO Nature (tqdm NO stdout) VIRA EVENTO DE PROGRESSO DO APP
class Bar:
    def __init__(self, iterable=None, total=None, **kw):
        self.total = total or 1
        self.n     = 0

    def update(self, n=1):
        self.n += n
        PROGRESS.update(min(1.0, self.n / self.total))

    def set_postfix_str(self, *args, **kw):
        return

    def set_description(self, *args, **kw):
        return

    def close(self):
        return


def readJson(path):
    return json.loads(open(path, 'r', encoding='utf-8').read()) if os.path.exists(path) else {}


# A ATITUDE DE CADA ESTRATÉGIA CONTRA A REFERÊNCIA, UM PAINEL POR ÂNGULO
def plotAttitude(attitude, save):
    angles = [var for var in ['pitch', 'roll', 'yaw'] if var in attitude]
    plt.figure(figsize=(6*len(angles), 5))

    for i, var in enumerate(angles):
        plt.subplot(1, len(angles), i + 1)
        plt.plot(attitude.time, attitude[f'{var}_ref'], label='referência', color='orange')
        plt.plot(attitude.time, attitude[var], label='estimado', color='blue', linewidth=1)
        plt.title(var); plt.xlabel('tempo (s)'); plt.ylabel('graus'); plt.grid(alpha=0.3); plt.legend()

    plt.tight_layout()
    plt.savefig(save, dpi=110, bbox_inches='tight')
    plt.close()


PROGRESS = None


# NO WINDOWS OS WORKERS DO Nature REIMPORTAM ESTE ARQUIVO: SEM A GUARDA O PIPELINE RECOMEÇARIA DENTRO DE CADA UM
if __name__ == '__main__':
    EVENTS = os.fdopen(os.dup(1), 'w', encoding='utf-8')    # O stdout ORIGINAL SÓ PARA OS EVENTOS DO APP
    os.dup2(2, 1)                                           # print DE BIBLIOTECA E DE PROCESSO FILHO VAI PARA O LOG
    sys.stdout   = sys.stderr
    nature.progress = Bar

    job      = readJson(sys.argv[1])
    session  = job['session']
    info     = readJson(f'{session}/info.json')
    strategy = job.get('strategy', 'KalmanFusion')
    PROGRESS = Progress(strategy)
    gravity  = float(job.get('gravity') or GRAVITY)
    align    = job.get('align') or info.get('align')
    serial   = job.get('id') or (info.get('mru') or {}).get('id') or 'MRU'
    debug    = info.get('reference') == 'debug'
    created  = datetime.datetime.now()
    bundle   = os.path.join(job['output'], f'{created:%Y-%m-%d_%H-%M-%S}_{serial}')
    timings  = {}

    try:
        for folder in ['results', 'figures', 'firmware']:
            os.makedirs(os.path.join(bundle, folder), exist_ok=True)

        started = time.time()
        PROGRESS.stage('format')
        formatted = Format(pd.read_csv(os.path.join(session, 'data.csv')), job.get('axes') or info.get('axes'))
        formatted.update()
        dataset = formatted.data
        timings['format'] = time.time() - started

        started = time.time()
        PROGRESS.stage('filters')
        filters = Filters(dataset, PROGRESS.report)
        filters.update()
        filtered = filters.apply(dataset)
        filters.plot(filtered, os.path.join(bundle, 'figures', 'filters.png'))
        timings['filters'] = time.time() - started

        started = time.time()
        PROGRESS.stage('correction')
        correction = Correction(filtered, gravity, align)
        correction.update()
        corrected = correction.apply(filtered)
        correction.plot(corrected, os.path.join(bundle, 'figures', 'correction.png'))
        timings['correction'] = time.time() - started

        started = time.time()
        PROGRESS.stage('attitude')
        PROGRESS.report(0, strategy, 1)
        model = {'KalmanFusion': lambda: KalmanFusion(corrected, gravity, bundle), 'LinearFit': lambda: LinearFit(corrected), 'MachineLearning': lambda: MachineLearning(corrected)}[strategy]()
        model.update()
        attitude = model.apply()
        plotAttitude(attitude, os.path.join(bundle, 'figures', 'attitude.png'))
        timings['attitude'] = time.time() - started

        started = time.time()
        PROGRESS.stage('heave')
        heave = Heave(corrected, attitude, gravity, PROGRESS.report)
        heave.update()
        heaved = heave.apply()
        heave.plot(os.path.join(bundle, 'figures', 'heave.png'))
        timings['heave'] = time.time() - started

        started = time.time()
        PROGRESS.stage('lever')
        lever = Lever(heaved, corrected, heave.pivot, heave.info()['trend'], job.get('point'))
        lever.update()
        levered = lever.apply()
        timings['lever'] = time.time() - started

        started = time.time()
        PROGRESS.stage('analysis')
        analysis = Analysis(corrected, attitude, levered)
        analysis.update()
        plots = analysis.export(os.path.join(bundle, 'figures'))
        timings['analysis'] = time.time() - started

        started = time.time()
        PROGRESS.stage('certificate')
        details = {
            'Modelo do MRU': 'Measure MRU',
            'Número de Série': serial,
            'Nº do Certificado': f'MO-{created:%Y%m%d-%H%M}',
            'Data da Calibração': created.strftime('%d/%m/%Y'),
            'Estratégia': f'{model.name} (filters)',
            'Referência': 'DEBUG · o próprio MRU filtrado' if debug else 'Plataforma de referência',
            'Técnico': 'Measure Offshore'
        }

        Certificate(analysis.info(), plots, details, os.path.join(bundle, 'certificate.pdf'), debug).export()
        timings['certificate'] = time.time() - started

        params   = {**filters.getParams(), **correction.getParams(), **model.getParams(), **heave.getParams(), **lever.getParams()}
        firmware = Firmware(params, strategy)
        firmware.update()
        firmware.save(os.path.join(bundle, 'firmware'))

        for name, frame in {'corrected': corrected, 'attitude': attitude, 'heave': heaved, 'lever': levered}.items():
            frame.to_csv(os.path.join(bundle, 'results', f'{name}.csv'), index=False)

        if job.get('copy_data', True):
            shutil.copy(os.path.join(session, 'data.csv'), os.path.join(bundle, 'data.csv'))

        records = {'format': formatted.info(), 'filters': filters.info(), 'correction': correction.info(), 'attitude': model.info(), 'heave': heave.info(), 'lever': lever.info()}

        calibration = {
            'id': serial,
            'created': created.isoformat(timespec='seconds'),
            'session': session,
            'strategy': strategy,
            'reference': 'debug' if debug else 'table',
            'gravity': gravity,
            'align': align,
            'point': lever.point.tolist(),
            'timings': {key: round(value, 1) for key, value in timings.items()},
            'metrics': analysis.info(),
            'records': records,
            'files': {'certificate': True, 'data': job.get('copy_data', True), 'figures': sorted(os.listdir(os.path.join(bundle, 'figures')))},
            'firmware': firmware.keys
        }

        open(os.path.join(bundle, 'calibration.json'), 'w', encoding='utf-8').write(json.dumps(calibration, indent=4, ensure_ascii=False, default=float).replace('NaN', 'null'))
        send('result', data={'folder': bundle}, message=f'calibração salva em {bundle}')
    except Exception as error:
        traceback.print_exc()
        send('error', message=f'{type(error).__name__}: {error}')
        sys.exit(1)
