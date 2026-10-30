import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation

PERIODS  = [0.5, 1.0, 1.5, 2.0, 3.0, 5.0]    # s
DAMPINGS = [0.5, 0.7, 1.0, 1.4]
SETTLE   = 20.0    # s DO TRANSITÓRIO DE PARTIDA FORA DA MÉTRICA
TREND    = 10.0    # s DA MÉDIA MÓVEL QUE SEPARA A OSCILAÇÃO DA TENDÊNCIA: VÁRIOS PERÍODOS DO HEAVE DO PÊNDULO
COLUMNS  = ['time', 'static', 'ax', 'ay', 'az', 'ref_roll', 'ref_pitch', 'ref_yaw', 'ref_wx', 'ref_wy', 'ref_wz']


# (R v)_z: A TERCEIRA LINHA DE R = Rz Ry Rx, QUE NÃO DEPENDE DA PROA
def vertical(v, pitch, roll):
    p, r = np.radians(pitch), np.radians(roll)
    return -np.sin(p)*v[..., 0] + np.sin(r)*np.cos(p)*v[..., 1] + np.cos(r)*np.cos(p)*v[..., 2]


# O BALANÇO DEPOIS DO TRANSITÓRIO DE PARTIDA; SEM BALANÇO (REFERÊNCIA EM DEBUG PARADA) OU ENSAIO CURTO, O QUE HOUVER
def getWindow(time, moving):
    rows   = moving if moving.any() else np.ones(len(time), bool)
    window = rows & (time > time[rows][0] + SETTLE)
    return window if window.any() else rows


def skew(v):
    return np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])


# SEÇÃO z'' = u - 2ζω z' - ω² z COM A ENTRADA LINEAR NO PASSO, ESPELHO DO Section DO FIRMWARE
class Section:
    GAP = 0.5    # s SEM AMOSTRA: A INTEGRAÇÃO NÃO ATRAVESSA O BURACO, RECOMEÇA EM REGIME

    def __init__(self, period, damping):
        self.w      = 2*np.pi/(10*period)
        self.zeta   = damping
        self.primed = False

    def update(self, u, dt):
        if not self.primed or dt > self.GAP:
            self.z0, self.z1, self.z2, self.u, self.primed = u/self.w**2, 0.0, 0.0, u, True
            return self

        e, w = self.zeta, self.w
        w0   = self.u - 2*e*w*self.z1 - w*w*self.z0
        w1   = u - 2*e*w*self.z1 - w*w*self.z0
        self.z0 += self.z1*dt + dt*dt*(2*w0 + w1)/6
        self.z1 += dt*(w0 + w1)/2
        self.z2  = u - 2*e*w*self.z1 - w*w*self.z0
        self.u   = u
        return self


# HEAVE: DUAS SEÇÕES EM CASCATA NA ACELERAÇÃO VERTICAL, SAÍDA z' DE CADA UMA
def getHeave(accel, time, period, damping):
    velocity, position = Section(period, damping), Section(period, damping)
    return np.array([position.update(velocity.update(a, dt).z1, dt).z1 for a, dt in zip(accel, np.diff(time, prepend=time[0]))])


# O MESMO FILTRO SOBRE UM DESLOCAMENTO: H(s)s² SÃO DUAS SEÇÕES PASSA-ALTA
def getBand(values, time, period, damping):
    first, second = Section(period, damping), Section(period, damping)
    return np.array([second.update(first.update(x, dt).z2, dt).z2 for x, dt in zip(values, np.diff(time, prepend=time[0]))])


# HEAVE NO SENSOR CONTRA A VERDADE GEOMÉTRICA DO PIVÔ DO ENSAIO, COM PERÍODO E AMORTECIMENTO PELA GRADE: ESPELHO DO Calibration/4 - Heave
class Heave:
    def __init__(self, corrected, attitude, gravity, report=lambda fraction, message, span=0: None):
        attitude     = attitude.drop(columns='static', errors='ignore')
        self.df      = corrected[COLUMNS].merge(attitude, on='time')
        self.gravity = gravity
        self.report  = report

    def update(self):
        df     = self.df
        time   = df.time.to_numpy()
        moving = ~df.static.to_numpy()
        df['accel'] = vertical(df[['ax', 'ay', 'az']].to_numpy(), df.pitch, df.roll) + self.gravity

        R       = Rotation.from_euler('xyz', df[['ref_roll', 'ref_pitch', 'ref_yaw']].to_numpy(), degrees=True).as_matrix()
        w       = np.radians(df[['ref_wx', 'ref_wy', 'ref_wz']].to_numpy())
        segment = np.cumsum(np.r_[0, np.diff(time) > Section.GAP])
        dw      = np.vstack([np.gradient(w[segment == k], time[segment == k], axis=0) for k in np.unique(segment)])
        K       = np.array([skew(a) + skew(o) @ skew(o) for a, o in zip(dw, w)])
        rest    = df[['ax', 'ay', 'az']].to_numpy() - np.einsum('nji,j->ni', R, [0, 0, -self.gravity])

        self.pivot = np.linalg.lstsq(K[moving].reshape(-1, 3), rest[moving].reshape(-1), rcond=None)[0]
        geo        = R[:, 2, :] @ self.pivot
        window     = int(round(TREND / np.median(np.diff(time))))
        self.truth = geo - pd.Series(geo).groupby(segment).transform(lambda part: part.rolling(window, center=True, min_periods=1).mean()).to_numpy()

        self.settled = getWindow(time, moving)
        cells        = [(period, damping) for period in PERIODS for damping in DAMPINGS]
        errors       = {}

        for index, (period, damping) in enumerate(cells):
            self.report(index / len(cells), f'Th = {period} s, ζ = {damping}', 1 / len(cells))
            error = getHeave(df.accel.to_numpy(), time, period, damping) - self.truth
            errors[(period, damping)] = float(np.sqrt(np.mean(error[self.settled]**2)))

        self.grid = pd.DataFrame([[errors[(period, damping)] for damping in DAMPINGS] for period in PERIODS], index=PERIODS, columns=DAMPINGS)
        self.period, self.damping = self.grid.stack().idxmin()
        self.heave = getHeave(df.accel.to_numpy(), time, self.period, self.damping)

    # heave, A VERDADE E AS BANDAS DE CADA EIXO, QUE O BRAÇO DE ALAVANCA SOMA
    def apply(self):
        time = self.df.time.to_numpy()
        rows = vertical(np.eye(3)[:, None, :], self.df.pitch.to_numpy(), self.df.roll.to_numpy())
        return self.df[['time', 'static']].assign(heave=self.heave, heave_ref=self.truth, **{f'band_{axis}': getBand(rows[j], time, self.period, self.damping) for j, axis in enumerate('xyz')})

    def getParams(self):
        return {'HEAVE_PERIOD': [float(self.period)], 'HEAVE_DAMPING': [float(self.damping)], 'HEAVE_GRAVITY': [self.gravity]}

    def info(self):
        error = (self.heave - self.truth)[self.settled]
        return {
            'period': float(self.period), 'damping': float(self.damping), 'gravity': self.gravity, 'pivot': self.pivot.tolist(), 'trend': TREND,
            'grid': self.grid.rename(index=str, columns=str).to_dict('index'),
            'metrics': {'rms': float(np.sqrt(np.mean(error**2))), 'amplitude': float(np.ptp(self.truth[self.settled])), 'corr': float(np.corrcoef(self.heave[self.settled], self.truth[self.settled])[0, 1])}
        }

    # A GRADE DE PERÍODO E AMORTECIMENTO E O HEAVE ESCOLHIDO CONTRA A VERDADE
    def plot(self, save=None):
        time = np.where(~self.df.static.to_numpy(), self.df.time.to_numpy(), np.nan)
        plt.figure(figsize=(18, 5))
        plt.subplot(1, 2, 1)

        for damping in DAMPINGS:
            plt.plot(PERIODS, 1000*self.grid[damping], marker='o', label=f'ζ = {damping}')

        plt.title(f'Erro do heave: Th = {self.period} s, ζ = {self.damping} ({1000*self.grid.loc[self.period, self.damping]:.1f} mm RMS)'); plt.xlabel('Th (s)'); plt.ylabel('RMS (mm)'); plt.yscale('log'); plt.grid(); plt.legend()

        plt.subplot(1, 2, 2)
        plt.plot(time, self.truth, label='verdadeiro', color='blue', linewidth=2)
        plt.plot(time, self.heave, label='heave', color='red', linewidth=1)
        plt.title('Heave no sensor no balanço'); plt.xlabel('tempo (s)'); plt.ylabel('m'); plt.grid(); plt.legend()
        plt.tight_layout()
        plt.savefig(save, dpi=110, bbox_inches='tight')
        plt.close()
