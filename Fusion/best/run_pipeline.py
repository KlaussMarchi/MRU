import os
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from OrientParser import OrientationParser


PROJ_DIR = os.path.dirname(os.path.abspath(__file__))
BEST_DIR = os.path.join(PROJ_DIR, 'best')


class RunPipeline:
    """
    Loads data.csv, runs the optimized OrientationParser with best params,
    computes metrics, generates comparison plots, and prints results.
    """

    def __init__(self, dataPath=None, paramsPath=None):
        self.dataPath = dataPath or os.path.join(PROJ_DIR, 'data.csv')
        self.paramsPath = paramsPath or os.path.join(BEST_DIR, 'best_params.json')
        self.df = pd.read_csv(self.dataPath)
        self.dt = 0.1
        self.gyro = self.df[['target_wx', 'target_wy', 'target_wz']].values
        self.accel = self.df[['target_ax', 'target_ay', 'target_az']].values
        self.refPitch = self.df['ref_pitch'].values
        self.refRoll = self.df['ref_roll'].values
        self.refYaw = self.df['ref_yaw'].values
        self.refHeave = self.df['ref_la_pos_mon_d'].values
        self.time = self.df['time'].values

        with open(self.paramsPath) as f:
            self.params = json.load(f)

    def computeMetrics(self, estimated, reference):
        err = estimated - reference
        rmse = np.sqrt(np.mean(err ** 2))
        mae = np.mean(np.abs(err))
        ssTot = np.sum((reference - np.mean(reference)) ** 2)
        ssRes = np.sum(err ** 2)
        r2 = 1.0 - ssRes / ssTot if ssTot > 1e-12 else 0.0
        return {'rmse': float(rmse), 'mae': float(mae), 'r2': float(r2)}

    def run(self):
        parser = OrientationParser(**self.params)
        pitchEst, rollEst, yawEst, heaveEst = parser.process(
            self.gyro, self.accel)
        heaveEst = heaveEst - np.mean(heaveEst) + np.mean(self.refHeave)

        metrics = {
            'pitch': self.computeMetrics(pitchEst, self.refPitch),
            'roll': self.computeMetrics(rollEst, self.refRoll),
            'yaw': self.computeMetrics(yawEst, self.refYaw),
            'heave': self.computeMetrics(heaveEst, self.refHeave),
        }

        self._printMetrics(metrics)
        self._savePlots(pitchEst, rollEst, yawEst, heaveEst)
        self._saveMetrics(metrics)

        return pitchEst, rollEst, yawEst, heaveEst, metrics

    def _printMetrics(self, metrics):
        print("=" * 65)
        print("  ORIENTATION & HEAVE ESTIMATION RESULTS")
        print("=" * 65)
        for axis in ['pitch', 'roll', 'yaw', 'heave']:
            m = metrics[axis]
            unit = 'deg' if axis != 'heave' else 'm'
            print(f"  {axis:>6s} : RMSE = {m['rmse']:.6f} {unit}"
                  f"  |  MAE = {m['mae']:.6f} {unit}"
                  f"  |  R^2 = {m['r2']:.6f}")
        print("-" * 65)
        print(f"  Algorithm: {self.params.get('method', 'unknown')}"
              f" + forward-backward smoothing")
        print("=" * 65)

    def _savePlots(self, pitchEst, rollEst, yawEst, heaveEst):
        outPath = os.path.join(BEST_DIR, 'comparison_plots.png')
        fig, axes = plt.subplots(4, 2, figsize=(18, 22))
        fig.suptitle(
            'IMU Fusion — Estimated vs Reference\n'
            '(Adaptive Madgwick + Forward-Backward Smoothing)',
            fontsize=15, fontweight='bold')

        signals = [
            ('Pitch (deg)', pitchEst, self.refPitch),
            ('Roll (deg)', rollEst, self.refRoll),
            ('Yaw (deg)', yawEst, self.refYaw),
            ('Heave (m)', heaveEst, self.refHeave),
        ]
        colors = [('#2196F3', '#F44336'), ('#4CAF50', '#FF9800'),
                  ('#9C27B0', '#E91E63'), ('#00BCD4', '#FF5722')]

        for idx, (label, est, ref) in enumerate(signals):
            cRef, cEst = colors[idx]

            ax = axes[idx, 0]
            ax.plot(self.time, ref, color=cRef, label='Reference',
                    linewidth=1.5, alpha=0.85)
            ax.plot(self.time, est, color=cEst, label='Estimated',
                    linewidth=1.0, alpha=0.85, linestyle='--')
            ax.set_xlabel('Time (s)')
            ax.set_ylabel(label)
            ax.set_title(f'{label} — Time Series')
            ax.legend(fontsize=8, loc='best')
            ax.grid(True, alpha=0.25)

            ax2 = axes[idx, 1]
            error = est - ref
            rmse = np.sqrt(np.mean(error ** 2))
            ax2.hist(error, bins=60, color=cEst, alpha=0.7,
                     edgecolor='white', linewidth=0.5)
            ax2.axvline(0, color='black', linestyle='--', alpha=0.4)
            ax2.set_xlabel('Error')
            ax2.set_ylabel('Count')
            ax2.set_title(f'{label} — Error (RMSE = {rmse:.4f})')
            ax2.grid(True, alpha=0.25)

        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig(outPath, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"  Plots saved: {outPath}")

    def _saveMetrics(self, metrics):
        outPath = os.path.join(BEST_DIR, 'best_metrics.json')
        with open(outPath, 'w') as f:
            json.dump(metrics, f, indent=2)
        print(f"  Metrics saved: {outPath}")


if __name__ == '__main__':
    pipeline = RunPipeline()
    pipeline.run()
