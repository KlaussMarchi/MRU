from sklearn.base import clone
import numpy as np
from scipy import stats
import matplotlib.pyplot as plt


class GaussianAnalyser:
    student = {
        1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306,9: 2.262, 10: 2.228, 11: 2.201,
        12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 21: 2.080,
        22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060, 26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042, 40: 2.021,
        60: 2.000, 80: 1.990, 100: 1.984, 120: 1.980, "infty": 1.960
    }

    def __init__(self, trainer, n=30):
        self.trainer = trainer
        self.n = n

    def update(self):
        self.metrics      = {}
        self.trainer.seed = None

        for i in range(self.n):
            self.trainer.update()

            for name, value in self.trainer.info().items():
                self.metrics.setdefault(name, []).append(value)

    def info(self):
        response = {}

        for metric, values in self.metrics.items():
            response[metric] = float(np.mean(values))

        return response

    def gaussian(self, metric):
        data  = np.array(self.metrics[metric])
        mu    = data.mean()
        sigma = data.std(ddof=1)

        x  = np.linspace(mu - 4*sigma, mu + 4*sigma, 400)
        y  = (1/(sigma*np.sqrt(2*np.pi))) * np.exp(-0.5*((x - mu)/sigma)**2)
        dx = (x[1] - x[0])
        p  = (y * dx)

        t = self.student[self.n-1] if self.n < 120 else self.student["infty"]
        x_crit = t * sigma / np.sqrt(self.n)

        plt.title(f'Distribuição em {metric.title()}')
        plt.hist(data, density=True, alpha=0.75)
        plt.plot(x, y)
        plt.plot([(mu - x_crit) for i in x], np.linspace(0, max(y), len(x)), '--', color='red', label='$+t_{crit}$ (95%)')
        plt.plot([(mu + x_crit) for i in x], np.linspace(0, max(y), len(x)), '--', color='red', label='$-t_{crit}$ (95%)')
        
        text = f'média: {mu:.3f}\nmediana: {np.median(data):.3f}\nstd: {np.std(data):.3f}'
        opts = dict(boxstyle='round', facecolor='white', alpha=0.8)
        
        plt.text(0.05, 0.95, text, transform=plt.gca().transAxes, verticalalignment='top', bbox=opts)
        plt.xlabel('x'); plt.ylabel('frequência'); plt.grid(); plt.legend()

    def qqplot(self, key):
        data = np.array(self.metrics[key])
        stats.probplot(data, dist="norm", plot=plt)
        stat, p = stats.shapiro(data)
        plt.title(f"Q-Q Plot em {key} - Shapiro-Wilk p = {p:.4f}")
        plt.grid()

    def plot(self):
        count = len(self.metrics)

        for show in [self.gaussian, self.qqplot]:
            plt.figure(figsize=(6*count, 5))

            for i, metric in enumerate(self.metrics):
                plt.subplot(1, count, i+1); show(metric)

            plt.show()