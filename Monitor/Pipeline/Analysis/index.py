import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score

SENSORS = ['ax', 'ay', 'az', 'wx', 'wy', 'wz']
NORMAM  = ['heave', 'hr']    # ARFAGEM E VELOCIDADE DE ARFAGEM NO PONTO DE INTERESSE
PURPLE  = '#6A3CBC'
PINK    = '#E91E63'


# RUÍDO PARADO E ERRO CONTRA A REFERÊNCIA DE UMA VARIÁVEL, NO REPOUSO E NO BALANÇO
class CalibrationAnalysis:
    def __init__(self, df, var):
        self.df  = df
        self.var = var
        self.ref = f'{var}_ref' if f'{var}_ref' in df else None
        self.raw = f'{var}_raw' if f'{var}_raw' in df else None

    def rms(self, values):
        return float(np.sqrt(np.mean(np.square(values))))

    def update(self):
        static = self.df.loc[self.df.static]
        motion = self.df.loc[~self.df.static]
        self.metrics = {'std_stat': float(static[self.var].std(ddof=1))}

        if self.raw:
            self.metrics['std_raw'] = float(static[self.raw].std(ddof=1))

        if not self.ref:
            return

        error = self.df[self.var] - self.df[self.ref]
        self.metrics.update({
            'r2':   float(r2_score(self.df[self.ref], self.df[self.var])),
            'mae':  float(np.mean(np.abs(error))),
            'rmse': self.rms(error),
            'rms_stat': self.rms(static[self.var] - static[self.ref]),
            'rms_dyn':  self.rms(motion[self.var] - motion[self.ref])
        })

    def info(self):
        return self.metrics


# AS MÉTRICAS DE TODAS AS VARIÁVEIS E OS GRÁFICOS DOS ÂNGULOS QUE O CERTIFICADO DESENHA: ESPELHO DO Calibration/Analysis
class Analysis:
    def __init__(self, corrected, attitude, lever):
        sensors     = corrected[['time', 'static'] + SENSORS + [f'{var}_raw' for var in SENSORS]]
        attitude    = attitude.drop(columns='static', errors='ignore')
        self.df     = sensors.merge(attitude, on='time').merge(lever[['time', 'heave', 'heave_ref', 'hr', 'hr_ref']], on='time')
        self.angles = [var for var in ['pitch', 'roll', 'yaw'] if var in attitude]

    def update(self):
        self.metrics = {}

        for var in self.angles + NORMAM + SENSORS:
            analysis = CalibrationAnalysis(self.df, var)
            analysis.update()
            self.metrics[var] = analysis.info()

    def plotRef(self, var, limits=None):
        xmin, xmax = (self.df.time.min(), self.df.time.max()) if limits is None else limits
        window = self.df.loc[(self.df.time >= xmin) & (self.df.time <= xmax)]

        plt.plot(window.time, window[f'{var}_ref'], color=PURPLE, linewidth=0.8, label='Referência')
        plt.plot(window.time, window[var], color=PINK, linewidth=0.8, label='Medido')
        plt.title(f'{var.capitalize()}: Refer. vs. Medido ({self.metrics[var]["r2"]*100:.2f}%)', fontsize=8, fontweight='bold')
        plt.xlabel('Tempo (s)', fontsize=7); plt.ylabel('Amplitude', fontsize=7)
        plt.legend(fontsize=6, loc='lower right'); plt.tick_params(labelsize=6); plt.grid(alpha=0.3, linewidth=0.5)

    def plotError(self, var, limits=None):
        xmin, xmax = (self.df.time.min(), self.df.time.max()) if limits is None else limits
        window = self.df.loc[(self.df.time >= xmin) & (self.df.time <= xmax)]

        plt.plot(window.time, window[var] - window[f'{var}_ref'], color=PURPLE, linewidth=0.8)
        plt.title(f'Erro Temporal - {var.capitalize()}', fontsize=8, fontweight='bold')
        plt.xlabel('Tempo (s)', fontsize=7); plt.ylabel('Erro', fontsize=7)
        plt.ylim(-5, 5); plt.yticks(range(-5, 6)); plt.tick_params(labelsize=6); plt.grid(alpha=0.3, linewidth=0.5)

    # UM PNG POR PAINEL, QUE É COMO O CERTIFICADO LÊ
    def export(self, folder):
        plots = {}

        for var in self.angles:
            for name, draw in [('ref_vs_model', self.plotRef), ('error', self.plotError)]:
                figure = plt.figure(figsize=(250/72, 150/72), dpi=150)
                draw(var)
                plt.tight_layout(pad=0.5)
                plots[f'{var}_{name}'] = f'{folder}/{var}_{name}.png'
                figure.savefig(plots[f'{var}_{name}'], dpi=150, bbox_inches='tight')
                plt.close(figure)

        return plots

    def info(self):
        return self.metrics
