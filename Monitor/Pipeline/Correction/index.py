import numpy as np
import matplotlib.pyplot as plt
from scipy.spatial.transform import Rotation

TRIADS     = {'accel': ['ax', 'ay', 'az'], 'gyro': ['wx', 'wy', 'wz']}
EXCITATION = {'accel': 0.5, 'gyro': 2.0}    # m/s², graus/s: ABAIXO DISSO O EIXO FICA COM A MONTAGEM
THERMAL    = 10.0                           # °C DE EXCURSÃO MÍNIMA: O KERNEL JÁ COMPENSA DE FÁBRICA DE -40 A 85 °C
WHOLE      = 0.2                            # MONTAGEM A MENOS DE ~11 GRAUS DE EIXOS INTEIROS: O ALIGN PODE GIRAR A CORREÇÃO
STILL      = 50                             # AMOSTRAS PARADAS MÍNIMAS: ABAIXO DISSO (REFERÊNCIA EM DEBUG NO MAR) O ACELERÔMETRO USA O ENSAIO INTEIRO


# ROTAÇÃO QUE MELHOR LEVA OS VETORES MEDIDOS AOS PREVISTOS (WAHBA PELA SVD)
def getMount(pairs):
    H        = sum(v.T @ u / np.sum(u*u) for u, v in pairs)
    U, _, Vt = np.linalg.svd(H)
    return U @ np.diag([1, 1, np.linalg.det(U @ Vt)]) @ Vt


# CORREÇÃO AFIM DE UM TRIEDRO POR MÍNIMOS QUADRADOS COM RIDGE PUXANDO M PARA A MONTAGEM
class Triad:
    def __init__(self, u, v, temperature, prior, sigma, T0):
        self.u           = u
        self.v           = v
        self.temperature = temperature
        self.prior       = prior
        self.sigma       = sigma
        self.T0          = T0

    def update(self):
        delta = self.temperature - self.T0 if np.ptp(self.temperature) >= THERMAL else np.zeros(len(self.u))
        X     = np.c_[self.u, np.ones(len(self.u)), delta]
        lam   = len(self.u) * self.sigma**2
        A     = np.vstack([X, np.sqrt(lam) * np.eye(3, X.shape[1])])
        B     = np.vstack([self.v, np.sqrt(lam) * self.prior.T])
        W     = np.linalg.lstsq(A, B, rcond=None)[0]
        self.M, self.c, self.k = W[:3].T, W[3], W[4]

    def get(self):
        before = self.u @ self.prior.T - self.v
        after  = self.apply(self.u, self.temperature) - self.v
        return {'antes': np.sqrt(np.mean(before**2, axis=0)).tolist(), 'depois': np.sqrt(np.mean(after**2, axis=0)).tolist()}

    def info(self):
        return {'M': self.M.tolist(), 'c': self.c.tolist(), 'k': self.k.tolist()}

    def apply(self, u, temperature):
        return u @ self.M.T + self.c + np.outer(temperature - self.T0, self.k)


# MONTAGEM, ESCALA, VIÉS E TEMPERATURA DOS DOIS TRIEDROS CONTRA A REFERÊNCIA: ESPELHO DO Calibration/2 - Correction
class Correction:
    def __init__(self, df, gravity, align=None):
        self.df      = df
        self.gravity = gravity
        self.align   = align
        self.T0      = float(df.tmp.mean())

    def update(self):
        df       = self.df
        static   = df.static.to_numpy()
        R        = Rotation.from_euler('xyz', df[['ref_roll', 'ref_pitch', 'ref_yaw']].to_numpy(), degrees=True)
        samples  = {'accel': static if static.sum() >= STILL else np.ones(len(df), bool), 'gyro': np.ones(len(df), bool)}
        expected = {'accel': R.inv().apply([0, 0, -self.gravity]), 'gyro': df[['ref_wx', 'ref_wy', 'ref_wz']].to_numpy()}
        measured = {name: df[[f'{var}_raw' for var in axes]].to_numpy() for name, axes in TRIADS.items()}

        self.C      = getMount([(measured[name][samples[name]], expected[name][samples[name]]) for name in TRIADS])
        self.triads = {name: Triad(measured[name][samples[name]], expected[name][samples[name]], df.tmp.to_numpy()[samples[name]], self.C, EXCITATION[name], self.T0) for name in TRIADS}

        for triad in self.triads.values():
            triad.update()

        self.expected = expected

    # O CORRIGIDO NOS EIXOS DO NAVIO, NO FILTRADO E NO _raw
    def apply(self, df):
        df = df.copy()

        for name, axes in TRIADS.items():
            for suffix in ['', '_raw']:
                columns     = [f'{var}{suffix}' for var in axes]
                df[columns] = self.triads[name].apply(df[columns].to_numpy(), df.tmp.to_numpy())

        return df

    # O ALIGN DO ENSAIO SÓ VALE SE A MONTAGEM FOR UMA TROCA DE EIXOS COM SINAL
    def getFrame(self):
        P     = np.round(self.C) + 0.0
        whole = np.allclose(np.abs(P).sum(axis=0), 1) and np.allclose(np.abs(P).sum(axis=1), 1) and np.abs(self.C - P).max() < WHOLE
        return P, (self.align if self.align is not None and whole else [np.nan]*3)

    def getParams(self):
        accel, gyro  = self.triads['accel'], self.triads['gyro']
        frame, angles = self.getFrame()
        return {
            'CORRECTION_T0': [self.T0],
            'CORRECTION_M': [*accel.M.ravel(), *gyro.M.ravel()],
            'CORRECTION_C': [*accel.c, *gyro.c],
            'CORRECTION_K': [*accel.k, *gyro.k],
            'ALIGN_CALIBRATION': list(angles),
            'ALIGN_FRAME': frame.ravel().tolist()
        }

    def info(self):
        return {'mount': Rotation.from_matrix(self.C).as_euler('xyz', degrees=True).tolist(), 'align': self.align, 'T0': self.T0, 'triads': {name: triad.info() for name, triad in self.triads.items()}, 'metrics': {name: triad.get() for name, triad in self.triads.items()}}

    # GIRO CORRIGIDO NO BALANÇO E ACELERAÇÃO CORRIGIDA NO REPOUSO CONTRA O QUE A REFERÊNCIA PREVÊ
    def plot(self, corrected, save=None):
        time   = corrected.time.to_numpy()
        static = corrected.static.to_numpy()
        moving = np.flatnonzero(~static)
        middle = time[moving[len(moving) // 2]] if len(moving) else time[0]
        window = (time >= middle) & (time <= middle + 20)
        rest   = static & (time >= time[static][0] + 10) if static.any() else static
        plt.figure(figsize=(18, 8))

        for i, var in enumerate(TRIADS['gyro']):
            plt.subplot(2, 3, i + 1)
            plt.plot(time[window], self.expected['gyro'][window, i], label='referência', color='blue', linewidth=2)
            plt.plot(time[window], corrected[f'{var}_raw'].to_numpy()[window], label='corrigido', color='red', linewidth=1)
            plt.title(f'{var} no balanço'); plt.xlabel('tempo (s)'); plt.ylabel('graus/s'); plt.grid(alpha=0.3); plt.legend()

        for i, var in enumerate(TRIADS['accel']):
            plt.subplot(2, 3, i + 4)
            plt.plot(time[rest], self.expected['accel'][rest, i], label='gravidade prevista', color='blue', linewidth=2)
            plt.plot(time[rest], corrected[f'{var}_raw'].to_numpy()[rest], label='corrigido', color='red', linewidth=1)
            plt.title(f'{var} no repouso'); plt.xlabel('tempo (s)'); plt.ylabel('m/s²'); plt.grid(alpha=0.3); plt.legend()

        plt.tight_layout()
        plt.savefig(save, dpi=110, bbox_inches='tight')
        plt.close()
