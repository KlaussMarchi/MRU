import numpy as np
from sklearn.linear_model import LinearRegression
from Metrics.CrossValidation.index import CrossValidation

ANGLES = ['pitch', 'roll', 'yaw']
K_CV   = 5


# CADA ÂNGULO DO KERNEL AJUSTADO À REFERÊNCIA POR MÍNIMOS QUADRADOS SÓ NO BALANÇO, POR EIXO (fuse=False): ESPELHO DO Calibration/3 - Attitude/LinearFit
class LinearFit:
    name = 'linear_fit'

    def __init__(self, df, fuse=False):
        self.full  = df[['time', 'static'] + ANGLES + [f'ref_{var}' for var in ANGLES]]
        self.df    = self.full.loc[~self.full.static] if (~self.full.static).sum() >= 2*K_CV else self.full    # O AJUSTE SÓ VÊ O BALANÇO; O REPOUSO VOLTA NA HORA DE SALVAR
        self.xCols = ANGLES
        self.yCols = [f'ref_{var}' for var in ANGLES]
        self.fuse  = fuse

    def update(self):
        size   = len(self.xCols)
        self.M = np.zeros((size, size))
        self.B = np.zeros(size)
        self.cross = {}

        for i, yCol in enumerate(self.yCols):
            inputs = list(range(size)) if self.fuse else [i]
            xData  = self.df[[self.xCols[j] for j in inputs]]
            yData  = self.df[yCol].to_numpy()

            model = LinearRegression().fit(xData, yData)
            self.M[i, inputs] = model.coef_
            self.B[i]         = model.intercept_

            self.cross[yCol] = CrossValidation(model, xData, yData, K_CV)
            self.cross[yCol].update()

    # O AJUSTE APLICADO TAMBÉM AO REPOUSO, QUE A ANÁLISE PRECISA
    def apply(self):
        attitude = self.full[['time', 'static']].copy()
        yModel   = self.full[self.xCols].to_numpy() @ self.M.T + self.B

        for i, xCol in enumerate(self.xCols):
            attitude[xCol]          = yModel[:, i]
            attitude[f'{xCol}_ref'] = self.full[self.yCols[i]]

        return attitude

    def getParams(self):
        return {'ATTITUDE_MODEL': [1], 'LINEAR_M': self.M.ravel().tolist(), 'LINEAR_B': self.B.tolist()}

    def info(self):
        params = {yCol: {**dict(zip(self.xCols, self.M[i].round(6).tolist())), 'bias': round(float(self.B[i]), 6)} for i, yCol in enumerate(self.yCols)}
        return {'fuse': self.fuse, 'params': params, 'metrics': {yCol: cross.info() for yCol, cross in self.cross.items()}, 'K_CV': K_CV}
