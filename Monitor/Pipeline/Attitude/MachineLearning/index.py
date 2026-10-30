import numpy as np
import pandas as pd
from Format.index import normalizePeriod
from Metrics.CrossValidation.index import CrossValidation
from Attitude.MachineLearning.Selector.index import ModelSelector
from Attitude.MachineLearning.RandomSearch.index import RandomSearch

SENSORS = ['ax', 'ay', 'az', 'wx', 'wy', 'wz']
ANGLES  = ['pitch', 'roll', 'yaw']
WINDOW  = ['wx', 'wy', 'wz', 'ax', 'ay', 'az']    # ORDEM DOS BLOCOS DE ESTADOS NA LINHA DO MODELO

OPTIONS = {'target_var': ['pitch', 'roll'], 'n_states': 30, 'k_cv': 5, 'model': 'linear_regression', 'n_iter': 15000, 'dt': 0.1}


# JANELA DESLIZANTE: y(n), y(n-1) ... y(n-N+1) COMO COLUNAS, SEM ATRAVESSAR O BURACO ENTRE TRECHOS
def getStates(df, key, dt, var='y', n=10):
    table   = df.copy()
    segment = (table.time.diff() > 1.5*dt).cumsum()
    table[f'{var}'] = table[key]

    for i in range(1, n):
        table[f'{var}(n-{i})'] = table[key].groupby(segment).shift(i)

    columns = [f'{var}'] + [f'{var}(n-{i})' for i in range(1, n)]
    return table[columns]


# REGRESSÃO DA REFERÊNCIA SOBRE UMA JANELA DE SENSORES CORRIGIDOS: ESPELHO DOS TRÊS NOTEBOOKS DO Calibration/3 - Attitude/MachineLearning
class MachineLearning:
    name = 'machine_learning'

    def __init__(self, df, options=None):
        self.options = {**OPTIONS, **(options or {})}
        self.targets = self.options['target_var']
        self.dt      = self.options['dt']
        self.df      = df[['time', 'static'] + SENSORS + [f'ref_{var}' for var in ANGLES]].rename(columns={f'ref_{var}': var for var in ANGLES})

    def update(self):
        df    = normalizePeriod(self.df, 'time', self.dt).astype({'static': bool})
        xData = pd.concat([getStates(df, var, self.dt, var=var, n=self.options['n_states']) for var in WINDOW], axis=1)
        self.data = pd.concat([df.time, xData, df[self.targets]], axis=1).dropna().reset_index(drop=True)

        xData = self.data.drop(columns=['time'] + self.targets)
        yData = self.data[self.targets]

        self.selector = ModelSelector(self.options['model'], len(self.targets))
        model, params = self.selector.get()
        search = RandomSearch(model, params, xData, yData, self.options['k_cv'], temporal=True, n_iter=self.options['n_iter'])
        search.update()
        self.model, self.r2_adj = search.evaluate()

        self.cross = CrossValidation(self.model, xData, yData, self.options['k_cv'], temporal=True)
        self.cross.update()
        self.model.fit(xData, yData)
        self.variables = xData.columns.tolist()

    def apply(self):
        result   = pd.DataFrame(self.model.predict(self.data[self.variables]), columns=self.targets)
        attitude = pd.DataFrame({'time': self.data.time})

        for target in self.targets:
            attitude[target]          = result[target]
            attitude[f'{target}_ref'] = self.data[target]

        return attitude

    # A REGRESSÃO PADRONIZADA NA ORDEM DO FIRMWARE: BLOCO POR SENSOR EM ['ax'...'wz'], ATRASO 0 PRIMEIRO
    def getParams(self):
        scaler, machine = self.model.named_steps['scaler'], self.model.named_steps['model']
        inputs  = [var for var in SENSORS if var in self.variables]
        states  = len(self.variables) // len(inputs)
        columns = [self.variables.index(var if lag == 0 else f'{var}(n-{lag})') for var in inputs for lag in range(states)]

        return {
            'ATTITUDE_MODEL': [2],
            'MACHINE_PERIOD': [self.dt],
            'MACHINE_SENSOR': [SENSORS.index(var) for var in inputs],
            'MACHINE_TARGET': [self.targets.index(name) if name in self.targets else -1 for name in ANGLES],
            'MACHINE_MEAN': scaler.mean_[columns].tolist(),
            'MACHINE_SCALE': scaler.scale_[columns].tolist(),
            'MACHINE_COEF': np.asarray(machine.coef_)[:, columns].ravel().tolist(),
            'MACHINE_BIAS': np.atleast_1d(machine.intercept_).tolist(),
            'MACHINE_SHAPE': [len(inputs), states, len(machine.coef_)],
            'MACHINE_MODEL': self.selector.chosen
        }

    def info(self):
        return {'model': self.selector.chosen, 'params': {key: str(value) for key, value in self.model.get_params().items()}, 'r2_adj_holdout': float(self.r2_adj), 'metrics': self.cross.info(), 'targets': self.targets, 'options': self.options, 'samples': len(self.data)}
