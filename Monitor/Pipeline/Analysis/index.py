import os, glob
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter
from sklearn.metrics import r2_score

SENSORS = ['ax', 'ay', 'az', 'wx', 'wy', 'wz']
NORMAM  = ['heave', 'hr']    # ARFAGEM E VELOCIDADE DE ARFAGEM NO PONTO DE INTERESSE
FONTS   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Certificate', 'fonts')
PANEL   = (3.42, 1.62)        # in: METADE DA LARGURA ÚTIL DO CERTIFICADO, ENTÃO O TEXTO SAI NO CORPO QUE O PDF USA
ZOOM    = 20                 # s DO DETALHE NO MEIO DO BALANÇO
DEEP    = '#3c0f78'
PURPLE  = '#6b39bd'
TEAL    = '#2a9d8f'
SOFT    = '#f1ecf9'
INK     = '#1f1a2e'
MUTED   = '#615b70'
LINE    = '#ddd6ea'

STYLE = {
    'font.family': 'Source Sans 3', 'font.size': 6.5, 'axes.titlesize': 7.5, 'axes.titleweight': 'semibold', 'axes.titlecolor': INK,
    'axes.titlelocation': 'left', 'axes.titlepad': 4, 'axes.labelsize': 6.5, 'axes.labelcolor': MUTED, 'axes.edgecolor': LINE,
    'axes.linewidth': 0.6, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True, 'grid.color': LINE,
    'grid.linewidth': 0.4, 'xtick.color': MUTED, 'ytick.color': MUTED, 'xtick.major.size': 0, 'ytick.major.size': 0,
    'xtick.major.pad': 2.5, 'ytick.major.pad': 2.5, 'legend.frameon': False, 'legend.fontsize': 6.5, 'legend.handlelength': 1.8,
    'axes.unicode_minus': True, 'savefig.dpi': 300
}

for path in glob.glob(f'{FONTS}/*.ttf'):
    font_manager.fontManager.addfont(path)


# NÚMERO COMO SE ESCREVE NO BRASIL: VÍRGULA DECIMAL E O SINAL DE MENOS TIPOGRÁFICO
def formatTick(value, position):
    return f'{value:g}'.replace('.', ',').replace('-', '−')


def formatValue(value, digits=4):
    return f'{value:.{digits}f}'.replace('.', ',')


def formatAxes():
    plt.gca().xaxis.set_major_formatter(FuncFormatter(formatTick)); plt.gca().yaxis.set_major_formatter(FuncFormatter(formatTick))


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

    # ZOOM s NO MEIO DO TRECHO EM QUE A REFERÊNCIA DESTE ÂNGULO SE AFASTA DO REPOUSO: NA SÉRIE INTEIRA O SENO VIRA UM BLOCO
    def getWindow(self, var):
        ref    = self.df[f'{var}_ref']
        moving = self.df.time[(ref - ref.median()).abs() > 0.25 * np.ptp(ref)]
        center = moving.median() if len(moving) else self.df.time.median()
        return self.df.loc[(self.df.time - center).abs() <= ZOOM / 2]

    # OS TRECHOS PARADOS, DO PRIMEIRO AO ÚLTIMO INSTANTE DE CADA UM
    def getRests(self):
        static = self.df.static.to_numpy()
        runs   = np.split(np.arange(len(static)), np.flatnonzero(np.diff(static.astype(int))) + 1)
        return [(self.df.time.iloc[run[0]], self.df.time.iloc[run[-1]]) for run in runs if len(run) and static[run[0]]]

    def plotRef(self, var):
        window = self.getWindow(var)
        plt.plot(window.time, window[f'{var}_ref'], color=DEEP, linewidth=1.4, label='Referência')
        plt.plot(window.time, window[var], color=TEAL, linewidth=0.9, dashes=(3, 1.6), label='Medido')
        plt.title(f'{var.capitalize()} · detalhe de {ZOOM} s em movimento')
        plt.xlabel('Tempo (s)'); plt.ylabel('Ângulo (°)')
        plt.legend(loc='lower right', bbox_to_anchor=(1, 0.99), ncols=2, borderaxespad=0, columnspacing=1.2)

    # A SÉRIE INTEIRA, COM O REPOUSO SOMBREADO; A ESCALA SEGUE O MAIOR ERRO, SEM CORTAR NADA, COM FOLGA EM CIMA PARA OS RMS
    def plotError(self, var):
        error  = self.df[var] - self.df[f'{var}_ref']
        bound  = max(float(error.abs().max()) * 1.5, 1e-3)
        values = self.metrics[var]

        for index, (start, end) in enumerate(self.getRests()):
            plt.axvspan(start, end, color=SOFT, linewidth=0, label='Repouso' if index == 0 else None)

        plt.plot(self.df.time, error, color=PURPLE, linewidth=0.6, label='Erro')
        plt.ylim(-bound, bound); plt.xlim(self.df.time.min(), self.df.time.max())
        plt.title(f'{var.capitalize()} · erro ao longo do ensaio')
        plt.xlabel('Tempo (s)'); plt.ylabel('Medido − referência (°)')
        plt.text(0.01, 0.95, f'RMS em movimento {formatValue(values["rms_dyn"])}° · em repouso {formatValue(values["rms_stat"])}°', transform=plt.gca().transAxes, ha='left', va='top', fontsize=6, color=MUTED, bbox={'facecolor': 'white', 'edgecolor': 'none', 'pad': 1.5, 'alpha': 0.85})
        plt.legend(loc='lower right', bbox_to_anchor=(1, 0.99), ncols=2, borderaxespad=0, columnspacing=1.2)

    # UM PNG POR PAINEL NO TAMANHO EXATO EM QUE O CERTIFICADO O DESENHA, QUE É COMO ELE OS LÊ
    def export(self, folder):
        plots = {}

        with plt.rc_context(STYLE):
            for var in self.angles:
                for name, draw in [('ref_vs_model', self.plotRef), ('error', self.plotError)]:
                    figure = plt.figure(figsize=PANEL)
                    draw(var)
                    formatAxes()
                    figure.tight_layout(pad=0.2)
                    plots[f'{var}_{name}'] = f'{folder}/{var}_{name}.png'
                    figure.savefig(plots[f'{var}_{name}'])
                    plt.close(figure)

        return plots

    def info(self):
        return self.metrics
