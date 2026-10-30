import os, math
import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation
from numba import njit
from Nature.index import NatureSelector

SENSORS = ['ax', 'ay', 'az', 'wx', 'wy', 'wz']
ANGLES  = ['pitch', 'roll', 'yaw']
SEARCH  = {'population': 15, 'generations': 200, 'seed': 42, 'workers': min(8, os.cpu_count() or 1), 'backend': 'process'}
RUNS    = 1
DATA    = 'MRU_KALMAN_DATA'    # VARIÁVEL DE AMBIENTE COM O ENSAIO: OS WORKERS HERDAM NO fork E NO spawn
CACHE   = {}

VARIABLES = {
    'gyroNoise':  {'bounds': (-12.0,  -2.0)},   # log10 (rad/s)^2/Hz   ARW do giro: 1e-12 a 1e-2
    'biasNoise':  {'bounds': (-18.0,  -8.0)},   # log10 (rad/s^2)^2/Hz random walk do bias
    'accelNoise': {'bounds': ( -8.0,   2.0)},   # log10 variancia do versor do acelerometro
    'zuptNoise':  {'bounds': (-14.0,   2.0)},   # log10 (rad/s)^2 do ZARU; o topo desliga a correcao
    'accelGateK': {'bounds': ( -4.0,   6.0)},   # log10 do ganho que infla R quando |a| foge de g
    'leverX':     {'bounds': ( -3.0,   3.0)},   # metros, do centro de rotacao ate o sensor, no corpo
    'leverY':     {'bounds': ( -3.0,   3.0)},
    'leverZ':     {'bounds': ( -3.0,   3.0)},
    'gyroPhase':  {'bounds': ( -1.0,   2.0)}    # fase da taxa integrada: 0 retangular, 0.5 trapezoidal
}


# PRODUTO DE HAMILTON ENTRE DOIS QUATERNIONS (w, x, y, z)
@njit(cache=True)
def quatMul(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return np.array([w1*w2 - x1*x2 - y1*y2 - z1*z2, w1*x2 + x1*w2 + y1*z2 - z1*y2, w1*y2 - x1*z2 + y1*w2 + z1*x2, w1*z2 + x1*y2 - y1*x2 + z1*w2])


# EXPONENCIAL EXATA DO VETOR DE ROTACAO: A 10 Hz O PASSO CHEGA A 7 graus, ONDE O SENO JA NAO E LINEAR
@njit(cache=True)
def quatFromRotVec(rotVec):
    angle = np.linalg.norm(rotVec)

    if angle < 1e-12:
        return np.array([1.0, rotVec[0]/2, rotVec[1]/2, rotVec[2]/2])

    axis = rotVec / angle * math.sin(angle/2)
    return np.array([math.cos(angle/2), axis[0], axis[1], axis[2]])


# CORPO -> NAVEGACAO NA CONVENCAO DE HAMILTON, v_nav = R @ v_corpo
@njit(cache=True)
def quatToDCM(q):
    w, x, y, z = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)], [2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x)], [2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)]])


@njit(cache=True)
def skew(v):
    return np.array([[0.0, -v[2], v[1]], [v[2], 0.0, -v[0]], [-v[1], v[0], 0.0]])


# PROPAGA ATITUDE E BIAS; dtQ E O TEMPO REAL DECORRIDO, dt O INTEGRADO (LIMITADO EM BURACOS), cone O TERMO DE DOIS INSTANTES
@njit(cache=True)
def predict(q, b, P, gyro, dt, dtQ, cone, sg, sb):
    w  = gyro - b
    dq = quatFromRotVec(w * dt + cone)
    q  = quatMul(q, dq)
    q /= np.linalg.norm(q)

    S = skew(w)
    I = np.eye(3)
    F = np.eye(6)
    F[:3, :3] = quatToDCM(dq).T
    F[:3, 3:] = -(I*dt - S*dt**2/2 + S@S*dt**3/6)

    Q = np.zeros((6, 6))
    Q[:3, :3] = I * (sg*dtQ + sb*dtQ**3/3)
    Q[:3, 3:] = I * (-sb*dtQ**2/2)
    Q[3:, :3] = I * (-sb*dtQ**2/2)
    Q[3:, 3:] = I * (sb*dtQ)
    return q, b, F @ P @ F.T + Q


# CORRECAO MULTIPLICATIVA (MEKF) COM A FORMA DE JOSEPH
@njit(cache=True)
def correct(q, b, P, H, innovation, R):
    K  = P @ H.T @ np.linalg.inv(H @ P @ H.T + R)
    dx = K @ innovation

    q  = quatMul(q, quatFromRotVec(dx[:3]))
    q /= np.linalg.norm(q)

    A = np.eye(6) - K @ H
    P = A @ P @ A.T + K @ R @ K.T
    return q, b + dx[3:], (P + P.T) / 2


# O LAÇO AMOSTRA A AMOSTRA COMPILADO PELO numba: A BUSCA RODA O FILTRO MILHARES DE VEZES E EM PYTHON CADA PASSADA A 200 Hz LEVAVA SEGUNDOS
@njit(cache=True)
def getQuats(q, P, rate, gyro, dt, dtQ, cone, gap, accel, norm, gate, static, gyroNoise, biasNoise, accelNoise, zuptNoise, tilt):
    b     = np.zeros(3)
    I     = np.eye(3)
    quats = np.zeros((len(rate), 4))

    for i in range(len(rate)):
        q, b, P = predict(q, b, P, rate[i], dt[i], dtQ[i], cone[i], gyroNoise, biasNoise)

        if gap[i]:
            P[:3, :3] = I * tilt

        if norm[i] > 1e-6:
            h = -quatToDCM(q)[2]
            H = np.zeros((3, 6))
            H[:, :3] = skew(h)
            q, b, P  = correct(q, b, P, H, accel[i]/norm[i] - h, accelNoise * gate[i] * I)

        if static[i]:
            H = np.zeros((3, 6))
            H[:, 3:] = I
            q, b, P  = correct(q, b, P, H, gyro[i] - b, zuptNoise * I)

        quats[i] = q

    return quats, b


# MEKF DE SEIS ESTADOS (ATITUDE E BIAS DO GIRO), ESPELHO DO KalmanFilter DO Calibration/3 - Attitude/KalmanFusion E DO KalmanModel DO FIRMWARE
class KalmanFilter:
    NAV_GRAVITY = np.array([0.0, 0.0, -1.0])   # FORCA ESPECIFICA EM REPOUSO, NORMALIZADA
    TILT_P0     = 1.0                          # (rad^2) ATITUDE INICIAL DESCONHECIDA: DEIXA O ACCEL PUXAR
    BIAS_P0     = 1e-4                         # (rad/s)^2 BIAS INICIAL TIPICO DE UM MEMS JA COMPENSADO
    GAP_FACTOR  = 3.0                          # ACIMA DISSO O INTERVALO E BURACO DE AQUISICAO, NAO AMOSTRA
    STILL_ACCEL = 0.20                         # (m/s^2) TOLERANCIA DE |a|-g NO DETECTOR DE REPOUSO
    STILL_GYRO  = math.radians(1.0)            # (rad/s) TOLERANCIA DE |w| NO DETECTOR DE REPOUSO

    def __init__(self, df, xCols, yCols, gravity, params=None):
        self.df     = df.reset_index(drop=True).copy()
        self.xCols  = xCols
        self.yCols  = yCols
        self.params = params or {}

        p = self.params
        self.g          = p.get('g', gravity)
        self.gyroNoise  = 10 ** p.get('gyroNoise',  -6.0)
        self.biasNoise  = 10 ** p.get('biasNoise', -12.0)
        self.accelNoise = 10 ** p.get('accelNoise', -3.0)
        self.zuptNoise  = 10 ** p.get('zuptNoise',  -6.0)
        self.accelGateK = 10 ** p.get('accelGateK',  1.0)
        self.lever      = np.array([p.get('leverX', 0.0), p.get('leverY', 0.0), p.get('leverZ', 0.0)])
        self.yaw0       = p.get('yaw0')
        self.gyroPhase  = p.get('gyroPhase', 0.5)

    # NIVELAMENTO PELO ACELEROMETRO: u = R.T @ [0,0,-1] DA ROLAGEM E ARFAGEM; A PROA VEM DE FORA
    def initQuat(self, u, yaw):
        roll  = math.atan2(-u[1], -u[2])
        pitch = math.atan2(u[0], math.hypot(u[1], u[2]))
        x, y, z, w = Rotation.from_euler('xyz', [roll, pitch, math.radians(yaw)]).as_quat()
        return np.array([w, x, y, z])

    # JANELAS PARADAS PELO MESMO DETECTOR DO FIRMWARE
    def ready(self, accel, gyro):
        quiet = np.abs(np.linalg.norm(accel, axis=1) - self.g) < self.STILL_ACCEL
        return quiet & (np.linalg.norm(gyro, axis=1) < self.STILL_GYRO)

    def update(self):
        ax, ay, az, wx, wy, wz = self.xCols
        accel = self.df[[ax, ay, az]].to_numpy()
        gyro  = np.radians(self.df[[wx, wy, wz]].to_numpy())

        time  = self.df.time.to_numpy()
        dtNom = float(np.median(np.diff(time))) if len(time) > 1 else 1.0
        dtQ = np.diff(time, prepend=time[0])
        gap = dtQ > self.GAP_FACTOR * dtNom
        dt  = np.minimum(dtQ, self.GAP_FACTOR * dtNom)

        alpha      = np.zeros_like(gyro)
        alpha[1:]  = np.diff(gyro, axis=0) / dtQ[1:, None]
        alpha[gap] = 0.0
        alpha[0]   = alpha[1] if len(alpha) > 1 else 0.0
        rate       = gyro.copy()
        rate[1:]   = gyro[1:] - self.gyroPhase * (gyro[1:] - gyro[:-1])
        rate[gap]  = gyro[gap]
        cone       = np.zeros_like(gyro)
        cone[1:]   = np.cross(gyro[:-1], gyro[1:]) * dt[1:, None]**2 / 12
        cone[gap]  = 0.0
        lever      = np.cross(gyro, np.cross(gyro, self.lever)) + np.cross(alpha, self.lever)    # w x (w x r) + w' x r
        accel  = accel - lever
        norm   = np.linalg.norm(accel, axis=1)
        gate   = 1 + self.accelGateK * ((norm - self.g) / self.g) ** 2
        static = self.ready(accel, gyro)

        yaw = self.yaw0 if self.yaw0 is not None else float(self.df[self.yCols[2]].iloc[0])
        up  = accel[0] / norm[0] if norm[0] > 1e-6 else self.NAV_GRAVITY
        q   = self.initQuat(up, yaw)
        P   = np.diag([self.TILT_P0]*3 + [self.BIAS_P0]*3)

        quats, b = getQuats(q, P, rate, gyro, dt, dtQ, cone, gap, accel, norm, gate, static, self.gyroNoise, self.biasNoise, self.accelNoise, self.zuptNoise, self.TILT_P0)

        euler = Rotation.from_quat(quats[:, [1, 2, 3, 0]]).as_euler('xyz', degrees=True)
        euler = np.degrees(np.unwrap(np.radians(euler), axis=0))

        self.quats  = quats
        self.bias   = np.degrees(b)
        self.euler  = euler
        self.result = self.df.copy()

        for k, name in enumerate(['roll', 'pitch', 'yaw']):
            self.result[f'kalman_{name}'] = euler[:, k]

    # DIFERENCA ANGULAR NO RAMO CURTO: SEM ISSO UM SALTO DE 360 VIRA ERRO DE 360
    def error(self, name, refCol):
        return (self.result[f'kalman_{name}'].to_numpy() - self.result[refCol].to_numpy() + 180) % 360 - 180

    def get(self):
        data = {}

        for name, refCol in zip(['pitch', 'roll', 'yaw'], self.yCols):
            err  = self.error(name, refCol)
            corr = np.corrcoef(self.result[f'kalman_{name}'], self.result[refCol])[0, 1]
            data[refCol] = {'rmse': float(np.sqrt(np.mean(err**2))), 'bias': float(np.mean(err)), 'corr': float(corr)}

        return data


# CADA WORKER LÊ O ENSAIO DO DISCO UMA VEZ: MANDAR O DataFrame A CADA AVALIAÇÃO CUSTAVA DEZENAS DE MB POR GERAÇÃO
def getData():
    path = os.environ[DATA]

    if path not in CACHE:
        CACHE[path] = pd.read_pickle(path)

    return CACHE[path]


# SOMA DOS RMSE DE PITCH E ROLL: FUNÇÃO DE MÓDULO, QUE O multiprocess SERIALIZA PELO NOME
def getError(params):
    df, gravity = getData()
    kf = KalmanFilter(df, SENSORS, ANGLES, gravity, params)
    kf.update()
    result = kf.get()
    return result['pitch']['rmse'] + result['roll']['rmse']


# A ATITUDE PELA FUSÃO, COM OS RUÍDOS, O BRAÇO E A FASE DO GIRO BUSCADOS PELA CMA-ES CONTRA A REFERÊNCIA
class KalmanFusion:
    name = 'kalman_fusion'

    def __init__(self, df, gravity, folder):
        self.df      = df[['time', 'static'] + SENSORS + [f'ref_{var}' for var in ANGLES]].rename(columns={f'ref_{var}': var for var in ANGLES})
        self.gravity = gravity
        self.path    = os.path.join(folder, 'kalman.pkl')

    def update(self):
        pd.to_pickle((self.df, self.gravity), self.path)
        os.environ[DATA] = self.path
        problem      = {'objective': getError, 'maximize': False, 'verbose': True, 'variables': VARIABLES, **SEARCH}
        self.search  = NatureSelector('genetic', problem, n_gaussian=RUNS)
        self.best, self.score = self.search.update()
        self.kf = KalmanFilter(self.df, SENSORS, ANGLES, self.gravity, self.best)
        self.kf.update()
        os.remove(self.path)

    def apply(self):
        attitude = self.kf.result[['time', 'static']].copy()

        for name in ANGLES:
            attitude[name]          = self.kf.result[f'kalman_{name}']
            attitude[f'{name}_ref'] = self.kf.result[name]

        return attitude

    def getParams(self):
        kf = self.kf
        return {
            'ATTITUDE_MODEL': [0],
            'KALMAN_GRAVITY': [kf.g], 'KALMAN_GYRO_NOISE': [kf.gyroNoise], 'KALMAN_BIAS_NOISE': [kf.biasNoise], 'KALMAN_ACCEL_NOISE': [kf.accelNoise],
            'KALMAN_ZUPT_NOISE': [kf.zuptNoise], 'KALMAN_ACCEL_GATE': [kf.accelGateK], 'KALMAN_GYRO_PHASE': [kf.gyroPhase],
            'KALMAN_HEADING': [np.nan if kf.yaw0 is None else kf.yaw0], 'KALMAN_LEVER': kf.lever.tolist()
        }

    def info(self):
        return {**self.search.getBest(), 'metrics': self.kf.get(), 'bias': self.kf.bias.round(6).tolist(), 'search': {**SEARCH, 'runs': RUNS, 'bounds': {key: value['bounds'] for key, value in VARIABLES.items()}}}
