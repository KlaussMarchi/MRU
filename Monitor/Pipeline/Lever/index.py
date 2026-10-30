import numpy as np
import pandas as pd
from scipy.spatial.transform import Rotation
from Heave.index import getWindow

GAP    = 0.5     # s, O MESMO BURACO DO Section DO HEAVE


# O HEAVE TRANSPORTADO DO SENSOR AO PONTO DE INTERESSE PELAS BANDAS, VALIDADO NO PIVÔ, NO SENSOR E NO DOBRO DO BRAÇO: ESPELHO DO Calibration/5 - Lever
class Lever:
    def __init__(self, heave, corrected, pivot, trend, point=None):
        self.df    = heave.merge(corrected[['time', 'ref_roll', 'ref_pitch', 'ref_yaw']], on='time')
        self.pivot = np.asarray(pivot)
        self.point = np.asarray(point if point is not None else [0.0, 0.0, 0.0], dtype=float)

        time         = self.df.time.to_numpy()
        moving       = ~self.df.static.to_numpy()
        self.time    = time
        self.window  = getWindow(time, moving)
        self.segment = np.cumsum(np.r_[0, np.diff(time) > GAP])
        self.length  = int(round(trend / np.median(np.diff(time))))
        self.R       = Rotation.from_euler('xyz', self.df[['ref_roll', 'ref_pitch', 'ref_yaw']].to_numpy(), degrees=True).as_matrix()

    # HEAVE NO PONTO d PELAS BANDAS E A VERDADE DELE PELO PIVÔ DO ENSAIO
    def translate(self, d):
        geo   = self.R[:, 2, :] @ (self.pivot + d)
        truth = geo - pd.Series(geo).groupby(self.segment).transform(lambda part: part.rolling(self.length, center=True, min_periods=1).mean()).to_numpy()
        return self.df.heave.to_numpy() + self.df[['band_x', 'band_y', 'band_z']].to_numpy() @ d, truth

    # VELOCIDADE DE ARFAGEM COMO O FIRMWARE: DIFERENÇA ENTRE AMOSTRAS, ZERO NA PARTIDA E DEPOIS DE BURACO
    def getRate(self, values):
        step = np.diff(self.time, prepend=self.time[0])
        return np.where((step > 0) & (step <= GAP), np.diff(values, prepend=values[0]) / np.where(step > 0, step, 1), 0.0)

    def update(self):
        points          = {'pivô': -self.pivot, 'sensor': np.zeros(3), 'dobro do braço': self.pivot}
        self.validation = {}

        for name, d in points.items():
            estimate, truth = self.translate(d)
            self.validation[name] = {'rms (mm)': 1000*np.sqrt(np.mean((estimate - truth)[self.window]**2)), 'amplitude (mm)': 1000*np.ptp(truth[self.window])}

        estimate, truth = self.translate(self.point)
        self.result     = self.df[['time', 'static']].assign(heave=estimate, heave_ref=truth, hr=self.getRate(estimate), hr_ref=self.getRate(truth))

    def apply(self):
        return self.result

    def getParams(self):
        return {'LEVER_POINT': self.point.tolist()}

    def info(self):
        error = (self.result.heave - self.result.heave_ref)[self.window]
        rate  = (self.result.hr - self.result.hr_ref)[self.window]
        return {'point': self.point.tolist(), 'pivot': self.pivot.tolist(), 'validation': self.validation, 'metrics': {'rms': float(np.sqrt(np.mean(error**2))), 'rms_rate': float(np.sqrt(np.mean(rate**2)))}}
