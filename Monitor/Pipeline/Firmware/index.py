import os, re, math, datetime

# AS CHAVES DO CL: NA ORDEM DA CalibrationData DO FIRMWARE: SÃO OS NOMES DAS CONSTANTES DOS config.h
KEYS = [
    'ATTITUDE_MODEL', 'FILTERS_TYPE', 'FILTERS_FC', 'CORRECTION_T0', 'CORRECTION_M', 'CORRECTION_C', 'CORRECTION_K', 'ALIGN_CALIBRATION', 'ALIGN_FRAME',
    'KALMAN_GRAVITY', 'KALMAN_GYRO_NOISE', 'KALMAN_BIAS_NOISE', 'KALMAN_ACCEL_NOISE', 'KALMAN_ZUPT_NOISE', 'KALMAN_ACCEL_GATE', 'KALMAN_GYRO_PHASE', 'KALMAN_HEADING', 'KALMAN_LEVER',
    'LINEAR_M', 'LINEAR_B', 'MACHINE_PERIOD', 'MACHINE_SENSOR', 'MACHINE_TARGET', 'MACHINE_MEAN', 'MACHINE_SCALE', 'MACHINE_COEF', 'MACHINE_BIAS',
    'HEAVE_PERIOD', 'HEAVE_DAMPING', 'HEAVE_GRAVITY', 'LEVER_POINT'
]

FILTERS = ['FILTER_BUTTERWORTH', 'FILTER_LOW_PASS', 'FILTER_EXPONENTIAL']
MODELS  = ['KalmanModel', 'LinearModel', 'MachineModel']
FOLDERS = ['kalman', 'linear', 'machine']
NAMES   = ['kalman_fusion', 'linear_fit', 'machine_learning']
SYMBOLS = {'NAN': math.nan, **{name: index for index, name in enumerate(FILTERS)}}
NUMBER  = r'NAN|FILTER_\w+|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'


def toNumber(text):
    return SYMBOLS[text] if text in SYMBOLS else float(text)


def toFloat(value, spec):
    return 'NAN' if value is None or math.isnan(value) else f'{value:{spec}}f'


def toArray(values, spec):
    return ', '.join(toFloat(value, spec) for value in values)


def toMatrix(values, columns, spec, separator=', '):
    rows = [values[i:i + columns] for i in range(0, len(values), columns)]
    return separator.join('{' + toArray(row, spec) + '}' for row in rows)


# OS PARÂMETROS QUE O FIRMWARE COMPILARIA DE UM config.h: OS #define E OS static const
def readHeader(text):
    values = {}

    for name, value in re.findall(rf'#define\s+(\w+)\s+({NUMBER})f?\b', text):
        values[name] = [toNumber(value)]

    for name, body in re.findall(r'static const (?:int|float) (\w+)(?:\[\w*\])+\s*=\s*(\{.*?\});', text, re.S):
        values[name] = [toNumber(value) for value in re.findall(NUMBER, body)]

    return values


# OS config.h DE CADA ESTÁGIO DO FIRMWARE NO FORMATO DOS NOTEBOOKS E, LIDOS DE VOLTA, OS VALORES DE CADA CHAVE DO CL:
class Firmware:
    def __init__(self, params, strategy):
        self.params   = params
        self.strategy = strategy
        self.stamp    = f'// GERADO PELO MRU Monitor ({strategy}) EM {datetime.date.today():%d/%m/%Y}'

    def update(self):
        p, model = self.params, int(self.params['ATTITUDE_MODEL'][0])

        self.headers = {
            'filters/config.h': f'''#ifndef FILTERS_CONFIG_H
#define FILTERS_CONFIG_H

{self.stamp}
static const int FILTERS_TYPE[6] = {{{', '.join(FILTERS[int(value)] for value in p['FILTERS_TYPE'])}}};    // ax, ay, az, wx, wy, wz
static const float FILTERS_FC[6] = {{{toArray(p['FILTERS_FC'], '.6f')}}};    // Hz: -3 dB no butterworth, polo no low_pass, 1/(2 pi tau) na exponencial

#endif
''',
            'correction/config.h': f'''#ifndef CORRECTION_CONFIG_H
#define CORRECTION_CONFIG_H

{self.stamp}
#define CORRECTION_T0 {p['CORRECTION_T0'][0]:.3f}f    // graus C de referencia do termo termico

static const float CORRECTION_M[2][3][3] = {{
\t{{{toMatrix(p['CORRECTION_M'][:9], 3, '.8f')}}},    // acelerometro: linha = eixo do navio, coluna = eixo do Kernel
\t{{{toMatrix(p['CORRECTION_M'][9:], 3, '.8f')}}}     // giroscopio
}};

static const float CORRECTION_C[2][3] = {{{{{toArray(p['CORRECTION_C'][:3], '.8e')}}}, {{{toArray(p['CORRECTION_C'][3:], '.8e')}}}}};    // vies em m/s^2 e graus/s
static const float CORRECTION_K[2][3] = {{{{{toArray(p['CORRECTION_K'][:3], '.8e')}}}, {{{toArray(p['CORRECTION_K'][3:], '.8e')}}}}};    // por graus C

#endif
''',
            'align/config.h': f'''#ifndef ALIGN_CONFIG_H
#define ALIGN_CONFIG_H

{self.stamp}
static const float ALIGN_CALIBRATION[3] = {{{toArray(p['ALIGN_CALIBRATION'], '.4f')}}};    // proa, pitch e roll do Kernel no ensaio; NAN desliga a rotacao
static const float ALIGN_FRAME[3][3]    = {{{toMatrix(p['ALIGN_FRAME'], 3, '.8f')}}};    // eixos do navio do ensaio nos eixos do Kernel: a montagem arredondada

#endif
''',
            'attitude/config.h': f'''#ifndef ATTITUDE_CONFIG_H
#define ATTITUDE_CONFIG_H
#include "{FOLDERS[model]}/index.h"

{self.stamp}
using AttitudeModel = {MODELS[model]};

#endif
''',
            'heave/config.h': f'''#ifndef HEAVE_CONFIG_H
#define HEAVE_CONFIG_H

{self.stamp}
#define HEAVE_PERIOD  {p['HEAVE_PERIOD'][0]:.6f}f    // s, Th: o filtro passa periodos ate 10 Th
#define HEAVE_DAMPING {p['HEAVE_DAMPING'][0]:.6f}f    // zeta das secoes
#define HEAVE_GRAVITY {p['HEAVE_GRAVITY'][0]:.6f}f    // m/s^2 local, a mesma da correcao

#endif
''',
            'lever/config.h': f'''#ifndef LEVER_CONFIG_H
#define LEVER_CONFIG_H

{self.stamp}
static const float LEVER_POINT[3] = {{{toArray(p['LEVER_POINT'], '.6f')}}};    // m, do MRU ate o ponto de interesse nos eixos do navio (z para baixo)

#endif
''',
            f'attitude/{FOLDERS[model]}/config.h': [self.getKalman, self.getLinear, self.getMachine][model]()
        }

        values = {}

        for text in self.headers.values():
            values.update(readHeader(text))

        values['ATTITUDE_MODEL'] = [model]
        self.keys = {key: [None if math.isnan(value) else value for value in values[key]] for key in KEYS if key in values}

    def getKalman(self):
        p = self.params
        return f'''#ifndef KALMAN_CONFIG_H
#define KALMAN_CONFIG_H

{self.stamp}
#define KALMAN_NAME        "{NAMES[0]}"
#define KALMAN_GRAVITY     {p['KALMAN_GRAVITY'][0]:.6f}f
#define KALMAN_GYRO_NOISE  {p['KALMAN_GYRO_NOISE'][0]:.8e}f     // (rad/s)^2/Hz do ARW do giro
#define KALMAN_BIAS_NOISE  {p['KALMAN_BIAS_NOISE'][0]:.8e}f     // (rad/s^2)^2/Hz do random walk do bias
#define KALMAN_ACCEL_NOISE {p['KALMAN_ACCEL_NOISE'][0]:.8e}f    // variancia do versor do acelerometro
#define KALMAN_ZUPT_NOISE  {p['KALMAN_ZUPT_NOISE'][0]:.8e}f     // (rad/s)^2 do ZARU
#define KALMAN_ACCEL_GATE  {p['KALMAN_ACCEL_GATE'][0]:.8e}f    // ganho que infla R quando |a| foge de g
#define KALMAN_GYRO_PHASE  {p['KALMAN_GYRO_PHASE'][0]:.6f}f     // fase da taxa integrada: 0 retangular, 0.5 trapezoidal
#define KALMAN_HEADING     {toFloat(p['KALMAN_HEADING'][0], '.6f')}    // proa inicial em graus; NAN pega a do sensor

static const float KALMAN_LEVER[3] = {{{toArray(p['KALMAN_LEVER'], '.8f')}}};    // metros, do centro de rotacao ate o sensor, no corpo

#endif
'''

    def getLinear(self):
        return f'''#ifndef LINEAR_CONFIG_H
#define LINEAR_CONFIG_H

{self.stamp}
#define LINEAR_NAME "{NAMES[1]}"

static const float LINEAR_M[3][3] = {{
\t{toMatrix(self.params['LINEAR_M'], 3, '.8f', ',' + chr(10) + chr(9))}
}};    // linha = angulo calibrado, coluna = angulo do sensor: pitch, roll, yaw

static const float LINEAR_B[3] = {{{toArray(self.params['LINEAR_B'], '.8f')}}};

#endif
'''

    def getMachine(self):
        p = self.params
        inputs, states, outputs = p['MACHINE_SHAPE']
        features = inputs * states
        return f'''#ifndef MACHINE_CONFIG_H
#define MACHINE_CONFIG_H

{self.stamp}
#define MACHINE_NAME    "{NAMES[2]} ({p['MACHINE_MODEL']})"
#define MACHINE_INPUTS  {inputs}
#define MACHINE_STATES  {states}
#define MACHINE_OUTPUTS {outputs}
#define MACHINE_PERIOD  {p['MACHINE_PERIOD'][0]:.6f}f

static const int MACHINE_SENSOR[{inputs}] = {{{', '.join(str(value) for value in p['MACHINE_SENSOR'])}}};    // de onde cada bloco le em ['ax', 'ay', 'az', 'wx', 'wy', 'wz']
static const int MACHINE_TARGET[3] = {{{', '.join(str(value) for value in p['MACHINE_TARGET'])}}};    // saida de pitch, roll e yaw (-1 fica com o angulo do sensor)

static const float MACHINE_MEAN[{features}] = {{{toArray(p['MACHINE_MEAN'], '.8e')}}};

static const float MACHINE_SCALE[{features}] = {{{toArray(p['MACHINE_SCALE'], '.8e')}}};

static const float MACHINE_COEF[{outputs}][{features}] = {{
\t{toMatrix(p['MACHINE_COEF'], features, '.8e', ',' + chr(10) + chr(9))}
}};

static const float MACHINE_BIAS[{outputs}] = {{{toArray(p['MACHINE_BIAS'], '.8e')}}};

#endif
'''

    def save(self, folder):
        for path, text in self.headers.items():
            os.makedirs(os.path.dirname(f'{folder}/{path}'), exist_ok=True)
            open(f'{folder}/{path}', 'w', encoding='utf-8').write(text)
