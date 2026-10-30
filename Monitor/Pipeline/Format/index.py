import numpy as np
import pandas as pd
from scipy.interpolate import CubicSpline
from scipy.signal import correlate

SENSORS = ['ax', 'ay', 'az', 'wx', 'wy', 'wz']
ANGLES  = ['pitch', 'roll', 'yaw']


# GRADE E LEITURAS ARREDONDADAS NA MESMA CASA: SEM ISSO O RUÍDO DE FLOAT (1e-14) FAZ O merge_asof SEGURAR A AMOSTRA ANTERIOR
def normalizePeriod(df, key, dt=0.15):
    df = df.copy().sort_values(key)
    df[key] = (df[key] - df[key].iloc[0]).round(10)

    n = int(np.floor(df[key].iloc[-1] / dt)) + 1
    newAxis = np.round(np.linspace(0, dt*(n-1), n), 10)
    target  = pd.DataFrame({key: newAxis})
    return pd.merge_asof(target, df, on=key, direction='nearest', tolerance=dt/2).dropna().reset_index(drop=True)


# O data.csv DO MONITOR NOS EIXOS CRUS DO KERNEL, NUMA GRADE REGULAR, COM A TAXA DA REFERÊNCIA E SEM A DEFASAGEM: ESPELHO DO Calibration/Dataset/Format
class Format:
    def __init__(self, df, axes=None):
        self.source = df
        self.axes   = axes or {}

    def update(self):
        df        = self.source
        target    = {var: self.getAxis(df, var) for var in SENSORS + ANGLES}
        reference = {f'ref_{var}': df[f'ref_{var}'] for var in ANGLES}
        df        = pd.DataFrame({'time': df.time, 'static': df.static, 'tmp': df.target_tmp, **target, **reference})

        time    = df.time.diff()[1:].to_numpy()
        self.dt = round(float(np.median(time)), 4)
        df      = normalizePeriod(df, 'time', self.dt).astype({'static': bool})

        df[['ref_wx', 'ref_wy', 'ref_wz']] = self.getRates(df)
        columns  = ['tmp'] + SENSORS + ANGLES
        self.lag = self.getLag(df[~df.static], ['wx', 'wy', 'wz'], ['ref_wx', 'ref_wy', 'ref_wz'])

        block     = (df.time.diff() > 1.5*self.dt).cumsum()    # O DESLOCAMENTO NÃO ATRAVESSA O BURACO DA GRAVAÇÃO
        df[columns] = df.groupby(block)[columns].shift(self.lag)
        self.data = df.dropna(subset=columns).reset_index(drop=True)

    def getAxis(self, df, var):
        source = self.axes.get(var, var)
        return -df[f'target_{source[1:]}'] if source.startswith('-') else df[f'target_{source}']

    # TAXA DO CORPO PELA DERIVADA DOS ÂNGULOS DE EULER xyz EM SPLINE CÚBICA, SEM ATRAVESSAR O BURACO ENTRE TRECHOS
    def getRates(self, df):
        segment = (df.time.diff() > 1.5*self.dt).cumsum()
        rates   = []

        for _, part in df.groupby(segment):
            if len(part) < 2:    # UMA AMOSTRA ENTRE DOIS PACOTES PERDIDOS: SEM DERIVADA
                rates.append(np.zeros((len(part), 3)))
                continue

            angles             = np.unwrap(np.radians(part[['ref_roll', 'ref_pitch', 'ref_yaw']].to_numpy()), axis=0)
            phi, theta, _      = angles.T
            dphi, dtheta, dpsi = CubicSpline(part.time, angles)(part.time, 1).T
            rates.append(np.c_[dphi - dpsi*np.sin(theta), dtheta*np.cos(phi) + dpsi*np.sin(phi)*np.cos(theta), -dtheta*np.sin(phi) + dpsi*np.cos(phi)*np.cos(theta)])

        return np.degrees(np.vstack(rates))

    # ATRASO DO MRU CONTRA A REFERÊNCIA PELO PICO DA CORRELAÇÃO CRUZADA DOS MÓDULOS DA TAXA (PELA FFT: A DIRETA É N²)
    def getLag(self, df, target, reference):
        if df.empty:
            return 0

        x = np.linalg.norm(df[target], axis=1)
        y = np.linalg.norm(df[reference], axis=1)

        correlation = correlate(y - y.mean(), x - x.mean(), mode='full')
        lags = np.arange(-len(df) + 1, len(df))
        return int(lags[np.argmax(correlation)])

    def info(self):
        return {'dt': self.dt, 'lag': self.lag, 'samples': len(self.data), 'static': int(self.data.static.sum()), 'axes': self.axes}
