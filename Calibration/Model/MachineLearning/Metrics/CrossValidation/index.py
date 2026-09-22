import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.model_selection import PredefinedSplit, cross_validate, KFold
from sklearn.base import clone
from sklearn.metrics import make_scorer, r2_score

BLOCKS = 4  # TRECHOS CONTÍGUOS POR DOBRA: TODO TESTE PEGA BALANÇO E REPOUSO


# BLOCOS CONTÍGUOS INTERCALADOS: O TimeSeriesSplit DEIXAVA AS ÚLTIMAS DOBRAS SÓ NO REPOUSO, ONDE O ROLL É CONSTANTE E O R2 EXPLODE
def getSplitter(n, k, temporal=True, seed=42):
    if not temporal:
        return KFold(n_splits=k, shuffle=True, random_state=seed)

    return PredefinedSplit(np.arange(n) * BLOCKS * k // n % k)


class CrossValidation:
    def __init__(self, model, xData, yData, k=4, temporal=True, seed=42):
        self.model = clone(model)
        self.xData = xData
        self.yData = yData
        self.k     = k
        self.scores = {}
        self.df     = None
        self.temporal = temporal
        self.seed = seed
        self.targets  = list(yData.columns) if hasattr(yData, 'columns') else []    # y COMO DataFrame: UMA COLUNA POR SAÍDA

        self.scoring = {
            'r2': 'r2',    # uniform_average: MÉDIA DO R2 DE CADA SAÍDA
            'r2_adj': self.getScorer(),
            'rmse': 'neg_root_mean_squared_error',
            'mae':  'neg_mean_absolute_error',
            **{f'r2_{target}': self.getTargetScorer(i) for i, target in enumerate(self.targets)}
        }

    # R2 AJUSTADO PENALIZA AS p FEATURES: COM 60 ESTADOS E FOLD DE 200 AMOSTRAS A DIFERENÇA PARA O R2 CRU É GRANDE
    def getScorer(self):
        def adj_r2(y_true, y_pred):
            r2 = r2_score(y_true, y_pred)
            n  = len(y_true)
            p  = self.xData.shape[1]
            if n > p + 1:
                return 1 - (1 - r2) * (n - 1) / (n - p - 1)
            else:
                return r2
        return make_scorer(adj_r2)

    # R2 DE UMA SAÍDA SÓ: A MÉDIA ESCONDE O ÂNGULO RUIM QUANDO O OUTRO VAI BEM
    def getTargetScorer(self, index):
        def target_r2(y_true, y_pred):
            return r2_score(y_true, y_pred, multioutput='raw_values')[index]
        return make_scorer(target_r2)

    def update(self):
        self.cv = getSplitter(len(self.yData), self.k, self.temporal, self.seed)

        result = cross_validate(**{
            'estimator': self.model,
            'X':  self.xData, 
            'y':  self.yData,
            'cv': self.cv,
            'scoring': self.scoring,
            'return_train_score': False
        })

        self.score_data = [self.process(result, metric) for metric in self.scoring]
        self.metrics    = {key: float(metric['mean']) for key, metric in zip(self.scoring, self.score_data)}

        data = []
        for metric in self.score_data:
            row = metric.copy()
            row.update({f'split_{i+1}': value for i, value in enumerate(metric.get('values'))})
            data.append(row)
        
        self.df = pd.DataFrame(data)

    def process(self, result, key):
        values = result[f'test_{key}']

        if 'neg_' in str(self.scoring.get(key, '')):
            values = -values
            
        return {
            'name': key.upper(),
            'values': values,
            'mean': np.mean(values),
            'std': np.std(values),
            'min': np.min(values),
            'max': np.max(values)
        }
    
    def info(self):
        return self.metrics

    def print(self):        
        for metric in self.score_data:
            name = metric.get('name')
            mean = metric.get('mean')
            std  = metric.get('std')
            
            if 'R2' in name:
                print(f'{name}: {mean:.4f} (±{std:.4f})')
            else:
                print(f'{name}: {mean:.4f} (±{std:.4f}) [Erro Absoluto]')

        return self.df

    def plot(self):
        n_metrics = len(self.df)
        plt.figure(figsize=(5*n_metrics, 5))

        for i, (idx, row) in enumerate(self.df.iterrows()):
            metric_name = row['name'] #
            values = row['values']
            kData = [j+1 for j in range(self.k)]

            plt.subplot(1, n_metrics, i+1)
            plt.plot(kData, values, marker='o', linestyle='-', linewidth=2)
            plt.axhline(y=row['mean'], color='r', linestyle='--', alpha=0.5, label=f"Média: {row['mean']:.3f}")
            
            plt.title(f'{metric_name}')
            plt.xlabel('Split Temporal (K)')
            plt.ylabel(metric_name)
            plt.grid(True, alpha=0.3)
            plt.legend()
            
            if 'R2' in metric_name and np.min(values) > 0:
                plt.ylim(bottom=0, top=1.1)

        plt.tight_layout()
        plt.show()