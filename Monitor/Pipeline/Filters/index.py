import numpy as np
import pandas as pd
import math
import matplotlib.pyplot as plt
from scipy import signal
from Nature.index import NatureSelector

SENSORS = ['ax', 'ay', 'az', 'wx', 'wy', 'wz']
LOWEST  = math.log10(0.05)    # Hz: PERÍODO DE 20 s, O LIMITE DE ONDA QUE NENHUM FILTRO PODE CORTAR
SEGMENT = 12.8                # s DO TRECHO DO WELCH: RAIAS DE 0,08 Hz, FINAS O BASTANTE PARA O PERÍODO DE ONDA
SEARCH  = {'population': 8, 'generations': 40, 'seed': 42, 'patience': 10}    # BUSCA DE UMA DIMENSÃO: BATE A VARREDURA DENSA NAS 18 BUSCAS (test1 E 200 Hz) COM 1/50 DAS AVALIAÇÕES
RUNS    = 2                   # CORRIDAS INDEPENDENTES, SEMENTES 42 E 43: FICA A MELHOR
TYPES   = {'butterworth': 0, 'low_pass': 1, 'exponential': 2}    # FILTER_BUTTERWORTH, FILTER_LOW_PASS E FILTER_EXPONENTIAL DO FIRMWARE


# QUATRO POLOS REAIS EM Fc POR TUSTIN, ESPELHO DO FIRMWARE
class LowPassFilter:
    def __init__(self, Fc, dt):
        self.dt = dt
        self.Fc = Fc

        Wc = (2 * np.pi * Fc)
        C  = signal.cont2discrete(([Wc**4], [1, 4*Wc, 6*(Wc**2), 4*(Wc**3), Wc**4]), dt, method='bilinear')
        num, den = np.squeeze(C[0]), np.squeeze(C[1])
        self.num, self.den = (num / den[0]).tolist(), (den / den[0]).tolist()

    # O update() DO FIRMWARE EM C, PARTINDO EM REGIME NO PRIMEIRO VALOR
    def apply(self, yData):
        yData = np.asarray(yData, dtype=float)
        return signal.lfilter(self.num, self.den, yData, zi=signal.lfilter_zi(self.num, self.den) * (yData[0] if len(yData) else 0.0))[0]


# BUTTERWORTH DE SEGUNDA ORDEM COM PRÉ-DISTORÇÃO, ESPELHO DO FIRMWARE
class ButterworthFilter:
    def __init__(self, f_c):
        self.f_c = f_c / 2.0
        wc   = math.tan(math.pi * self.f_c)
        c2   = wc*wc
        norm = 1 + math.sqrt(2)*wc + c2
        self.b, self.a = [c2/norm, 2*c2/norm, c2/norm], [1.0, -2*(c2 - 1)/norm, -(1 - math.sqrt(2)*wc + c2)/norm]

    # y + a1 y1 + a2 y2 = b x, PARTINDO EM REGIME NO PRIMEIRO VALOR
    def apply(self, data):
        data = np.asarray(data, dtype=float)
        den  = [1.0, -self.a[1], -self.a[2]]
        return signal.lfilter(self.b, den, data, zi=signal.lfilter_zi(self.b, den) * (data[0] if len(data) else 0.0))[0]


# PRIMEIRA ORDEM y = αx + (1 − α)y₋₁
class ExponentialFilter:
    def __init__(self, alpha):
        self.alpha = alpha

    def apply(self, data):
        return pd.Series(np.asarray(data, dtype=float)).ewm(alpha=self.alpha, adjust=False).mean().to_numpy()


# OS TRÊS FILTROS CAUSAIS DO FIRMWARE EM CADA EIXO, CADA UM COM O CORTE DE MENOR ε: ESPELHO DO Calibration/1 - Filters
class Filters:
    def __init__(self, df, report=lambda fraction, message, span=0: None):
        self.df      = df
        self.report  = report
        self.dt      = round(float(df.time.diff().median()), 4)
        self.size    = int(round(SEGMENT / self.dt))
        self.impulse = signal.unit_impulse(8*self.size, 'mid')    # 8 JANELAS DE COMPRIMENTO: O FILTRO MAIS LENTO DECAI
        nyquist      = 0.5 / self.dt

        self.options = {
            'low_pass': {'filter': lambda log_fc: LowPassFilter(10**log_fc, self.dt), 'variables': {'log_fc': {'bounds': (LOWEST, math.log10(1/(math.pi*self.dt)))}}},
            'butterworth': {'filter': lambda log_fc: ButterworthFilter(10**log_fc / nyquist), 'variables': {'log_fc': {'bounds': (LOWEST, math.log10(0.99*nyquist))}}},
            'exponential': {'filter': lambda log_fc: ExponentialFilter(1 - math.exp(-2*math.pi*10**log_fc*self.dt)), 'variables': {'log_fc': {'bounds': (LOWEST, math.log10(10*nyquist))}}}    # 10 NYQUIST JÁ É α ≈ 1
        }

    # O BALANÇO S E O PISO DE RUÍDO N DO WELCH SÓ DEPENDEM DO EIXO: UMA VEZ POR EIXO, NÃO A CADA AVALIAÇÃO DA BUSCA
    def getSpectrum(self, data):
        P = signal.welch(np.asarray(data, dtype=float), nperseg=self.size)[1]
        N = np.median(P)    # O MOVIMENTO OCUPA POUCAS RAIAS: A MEDIANA É O PISO DE RUÍDO
        return np.clip(P - N, 0, None), N

    # ε: ERRO DO FILTRADO CONTRA O MOVIMENTO VERDADEIRO NO MESMO INSTANTE, DIVIDIDO PELO ERRO DO SINAL CRU
    def objective(self, filter, params, spectrum):
        S, N = spectrum
        h = self.options[filter]['filter'](**params).apply(self.impulse)
        H = np.fft.rfft(np.roll(h, -4*self.size))[::8]    # IMPULSO DE VOLTA EM n = 0, LIDO NAS RAIAS DO WELCH
        return np.sqrt(np.sum(np.abs(1 - H)**2*S + np.abs(H)**2*N) / (N*len(S)))

    def update(self):
        motion        = ~self.df.static.to_numpy()
        motion        = motion if motion.sum() >= SEGMENT / self.dt else np.ones(len(motion), bool)    # SEM BALANÇO (REFERÊNCIA EM DEBUG PARADA) O ENSAIO INTEIRO
        self.rankings = {}
        searches      = [(var, filter) for var in SENSORS for filter in self.options]
        spectra       = {var: self.getSpectrum(self.df.loc[motion, var]) for var in SENSORS}

        for index, (var, filter) in enumerate(searches):
            self.report(index / len(searches), f'{var} · {filter}', 1 / len(searches))
            model = NatureSelector('genetic', {'objective': lambda params, filter=filter, spectrum=spectra[var]: self.objective(filter, params, spectrum), 'maximize': False, 'verbose': True, 'variables': self.options[filter]['variables'], **SEARCH}, n_gaussian=RUNS)
            model.update()
            self.rankings.setdefault(var, {})[filter] = {'error': float(model.score), 'params': model.best}

        self.chosen = {var: min(ranking.items(), key=lambda item: item[1]['error']) for var, ranking in self.rankings.items()}

    # x FILTRADO E x_raw COM O ORIGINAL, COMO O filtered.csv
    def apply(self, df):
        df = df.rename(columns={col: f'{col}_raw' for col in SENSORS})

        for var, (filter, best) in self.chosen.items():
            df[var] = self.options[filter]['filter'](**best['params']).apply(df[f'{var}_raw'])

        return df

    def getParams(self):
        return {'FILTERS_TYPE': [TYPES[self.chosen[var][0]] for var in SENSORS], 'FILTERS_FC': [10**self.chosen[var][1]['params']['log_fc'] for var in SENSORS]}

    def info(self):
        return {'filters': {var: {'name': filter, 'error': best['error'], 'fc': 10**best['params']['log_fc']} for var, (filter, best) in self.chosen.items()}, 'ranking': self.rankings, 'search': {**SEARCH, 'runs': RUNS}}

    # CRU E FILTRADO NUM TRECHO DO BALANÇO, UM PAINEL POR EIXO
    def plot(self, filtered, save=None):
        moving = filtered.loc[~filtered.static] if (~filtered.static).any() else filtered
        start  = moving.time.iloc[len(moving) // 2]
        window = moving.loc[(moving.time >= start) & (moving.time <= start + 10)]
        plt.figure(figsize=(18, 8))

        for i, var in enumerate(SENSORS):
            filter, best = self.chosen[var]
            plt.subplot(2, 3, i + 1)
            plt.scatter(window.time, window[f'{var}_raw'], s=4, color='orange', label='bruto')
            plt.plot(window.time, window[var], linewidth=1.6, label=f'{filter} · {10**best["params"]["log_fc"]:.3g} Hz')
            plt.title(f'{var}: ε = {best["error"]:.3f}'); plt.xlabel('tempo (s)'); plt.grid(alpha=0.3); plt.legend()

        plt.tight_layout()
        plt.savefig(save, dpi=110, bbox_inches='tight')
        plt.close()
