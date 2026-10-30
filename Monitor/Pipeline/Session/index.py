import pandas as pd
import numpy as np
from scipy.interpolate import make_smoothing_spline
from scipy.signal import butter, filtfilt
import json, os, sys, shutil, datetime

JOURNAL   = sys.argv[1]    # PASTA DA GRAVAÇÃO, COM OS *.journal.csv DO APP
OUTPUT    = sys.argv[2]    # PASTA DA SESSÃO
META      = json.loads(open(sys.argv[3], 'r', encoding='utf-8').read())
TOLERANCE = 0.2            # s ENTRE A AMOSTRA DO MRU E A DA MESA NO CASAMENTO
STEADY    = 0.1            # graus DE EXCURSÃO DA MESA EM 1 s: ABAIXO DISSO A LINHA É static
POINTS    = 5              # A SPLINE SUAVIZADA PEDE CINCO PONTOS
CUTOFF    = 2.0            # Hz DO PASSA-BAIXA IDA E VOLTA DA REFERÊNCIA EM DEBUG: ACIMA DA ONDA E DA MESA, ABAIXO DO RUÍDO
FORMAT    = ['time', 'pitch', 'roll', 'yaw']
GAP       = 0.5            # s SEM PACOTE: OUTRO TRECHO DO RELÓGIO


def send(event, **data):
    print(json.dumps({'event': event, **data}, ensure_ascii=False), flush=True)


# O DIÁRIO NO RELÓGIO DO PC: O DO APARELHO DESLOCADO PELO MENOR ATRASO DE CHEGADA, UM DESLOCAMENTO POR REINÍCIO
def load(path):
    frame = pd.read_csv(path).dropna(axis=1, how='all')

    if frame.empty:
        return frame

    if 'time' not in frame:
        return frame.rename(columns={'host': 'time'})

    segment       = (frame.time.diff() < 0).cumsum()
    offset        = (frame.host - frame.time).groupby(segment).transform(lambda part: part.quantile(0.01))
    frame['time'] = (frame.time + offset).fillna(frame.host)
    return frame.drop(columns='host')


# O INSTANTE DE CADA PACOTE DO KERNEL: O CARIMBO TEM O JITTER DA LEITURA E O RELÓGIO DERIVA; A CONTAGEM DE PASSOS (PERDIDO CONTA DOIS) EM RETA, POR TRECHO, DÁ A GRADE DELE
def regularize(time):
    step    = np.median(np.diff(time))
    count   = np.r_[0, np.cumsum(np.maximum(np.round(np.diff(time) / step), 1))]
    segment = np.r_[0, np.cumsum(np.diff(time) > GAP)]
    fitted  = np.empty(len(time))

    for part in np.unique(segment):
        rows         = segment == part
        fitted[rows] = np.polyval(np.polyfit(count[rows], time[rows], 1), count[rows]) if rows.sum() > 1 else time[rows]

    return fitted


# REFERÊNCIA EM DEBUG: SEM A MESA, OS ÂNGULOS DO PRÓPRIO MRU FILTRADOS SEM ATRASO FAZEM O PAPEL DELA, NOS MESMOS INSTANTES
def getDebug(target):
    target = target[target.layout == 'scale'].sort_values('time')

    if len(target) <= 3 * POINTS:
        return pd.DataFrame(columns=FORMAT)

    b, a   = butter(2, CUTOFF, fs=1 / target.time.diff().median())
    angles = np.unwrap(np.radians(target[FORMAT[1:]].to_numpy()), axis=0)    # ROLL PERTO DE 180° E PROA PASSANDO POR 360° NÃO VIRAM DEGRAU
    return pd.DataFrame(np.c_[target.time, np.degrees(filtfilt(b, a, angles, axis=0))], columns=FORMAT)


# FORMATO DO Calibration: UMA LINHA POR AMOSTRA DO MRU NA ESCALA, COM A MESA SUAVIZADA NO INSTANTE DELA
def merge(target, reference, debug=False):
    target = target[target.layout == 'scale'].drop(columns='layout').dropna(axis=1, how='all')

    if target.empty or len(reference) < POINTS:
        return None

    names     = FORMAT[1:] if debug else ['pitch', 'roll']
    target    = target.sort_values('time').drop_duplicates('time')
    target    = target.assign(time=regularize(target.time.to_numpy()))    # A REFERÊNCIA NO INSTANTE DA AMOSTRA, NÃO NO DA LEITURA: SEM ISSO O Format DERIVA O JITTER
    target    = target.add_prefix('target_').rename(columns={'target_time': 'time'})
    reference = reference[['time'] + names].add_prefix('ref_').rename(columns={'ref_time': 'time'}).sort_values('time').drop_duplicates('time')
    angles    = [f'ref_{name}' for name in names]

    data = pd.merge_asof(target, reference, on='time', direction='nearest', tolerance=TOLERANCE)
    near = data[angles].notna()

    if not debug:
        data[angles] = np.c_[[make_smoothing_spline(reference.time, reference[angle])(data.time) for angle in angles]].T    # O Format E O 4 - Heave DERIVAM DUAS VEZES: PACOTE A 10 Hz EM DEGRAUS DE 0,025° VIRARIA PICO
        data['ref_yaw'] = 0.0    # A MESA SÓ TEM OS EIXOS DE ROLAGEM E ARFAGEM

    data[angles] = data[angles].where(near).bfill().ffill()    # ANTES DO PRIMEIRO PACOTE A MESA ESTÁ PARADA NA POSIÇÃO INICIAL

    window = max(int(round(1.0 / data.time.diff().median())), 1)
    swing  = data[angles].rolling(window, min_periods=1, center=True)    # PARADO ANTES E DEPOIS: A PARTIDA DA MESA TEM O PICO DO BRAÇO
    data['static'] = (swing.max() - swing.min()).max(axis=1) < STEADY

    columns = [column for column in data.columns if column.startswith(('target_', 'ref_'))]
    return data[['time', 'static'] + columns]


names  = [name for name in ['target', 'reference'] if os.path.exists(f'{JOURNAL}/{name}.journal.csv')]
frames = {}

for step, name in enumerate(names, 1):
    send('progress', step=step, steps=len(names) + 2, stage='Lendo os diários', message=f'lendo {name}.journal.csv')
    frames[name] = load(f'{JOURNAL}/{name}.journal.csv')

os.makedirs(OUTPUT, exist_ok=True)
start = min([frame.time.min() for frame in frames.values() if not frame.empty] or [0])
saved = {}

for name, frame in frames.items():
    if frame.empty:
        continue

    frame['time'] -= start
    frame.to_csv(f'{OUTPUT}/{name}.csv', index=False)
    saved[name] = len(frame)

send('progress', step=len(names) + 1, steps=len(names) + 2, stage='Casando MRU e plataforma', message=f'{saved} amostras salvas')
debug    = META.get('reference') == 'debug' and 'target' in saved and 'reference' not in saved
complete = all(name in saved for name in ['target', 'reference'])
data     = merge(frames['target'], getDebug(frames['target']), debug=True) if debug else merge(frames['target'], frames['reference']) if complete else None
warnings = META.pop('warnings', [])
META['reference'] = 'debug' if debug else 'table' if complete else None

if (complete or debug) and data is None:
    warnings.append('o MRU não estava na escala (SCALE) ou a referência tem poucos pontos: sem data.csv de calibração')

if debug and data is not None:
    warnings.append('referência em debug: os ângulos do próprio MRU filtrados fazem o papel da plataforma; a calibração e o relatório saem marcados e não valem como certificado')

info = {
    'description': 'target = MRU em teste, reference = plataforma de referência (Table)',
    'created': datetime.datetime.now().isoformat(timespec='seconds'),
    'samples': saved,
    'calibration': data is not None,
    'warnings': warnings,
    **META
}

if data is not None:
    send('progress', step=len(names) + 2, steps=len(names) + 2, stage='Gravando data.csv', message=f'{len(data)} linhas para o Calibration')
    data.to_csv(f'{OUTPUT}/data.csv', index=False)
    info |= {'data': len(data), 'static': int(data.static.sum()), 'rate': round(1 / data.time.diff().median(), 2), 'duration': round(float(data.time.iloc[-1] - data.time.iloc[0]), 1)}

with open(f'{OUTPUT}/info.json', 'w', encoding='utf-8') as file:
    file.write(json.dumps(info, indent=4, ensure_ascii=False))

if os.path.realpath(JOURNAL) != os.path.realpath(OUTPUT):
    shutil.rmtree(JOURNAL, ignore_errors=True)

send('result', data={'folder': OUTPUT, **info}, message=f'sessão salva em {OUTPUT}')
