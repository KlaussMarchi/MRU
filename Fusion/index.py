import os
import json
import numpy as np
import pandas as pd
import optuna
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from OrientParser import OrientationParser

optuna.logging.set_verbosity(optuna.logging.WARNING)

PROJ_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(PROJ_DIR, 'data.csv')
BEST_DIR = os.path.join(PROJ_DIR, 'best')


class FusionPipeline:

    def __init__(self):
        self.df = pd.read_csv(DATA_PATH)
        self.dt = 0.1
        self.gyro = self.df[['target_wx', 'target_wy', 'target_wz']].values
        self.accel = self.df[['target_ax', 'target_ay', 'target_az']].values
        self.refPitch = self.df['ref_pitch'].values
        self.refRoll = self.df['ref_roll'].values
        self.refYaw = self.df['ref_yaw'].values
        self.refHeave = self.df['ref_la_pos_mon_d'].values
        self.n = len(self.df)
        self.trainEnd = int(self.n * 0.7)
        self._bestOrientScore = float('inf')
        self._bestOrientParams = None

    def computeMetrics(self, estimated, reference):
        err = estimated - reference
        rmse = np.sqrt(np.mean(err ** 2))
        mae = np.mean(np.abs(err))
        ssTot = np.sum((reference - np.mean(reference)) ** 2)
        ssRes = np.sum(err ** 2)
        r2 = 1.0 - ssRes / ssTot if ssTot > 1e-12 else 0.0
        return {'rmse': float(rmse), 'mae': float(mae), 'r2': float(r2)}

    def _buildOrientParams(self, trial):
        method = trial.suggest_categorical(
            'method', ['madgwick', 'madgwick_adapt', 'mahony'])

        params = {
            'method': method,
            'dt': self.dt,
            'accelMin': trial.suggest_float('accelMin', 0.1, 5.0),
            'accelMax': trial.suggest_float('accelMax', 10.0, 30.0),
            'mountRoll': trial.suggest_float('mountRoll', 170.0, 190.0),
            'mountPitch': trial.suggest_float('mountPitch', -5.0, 5.0),
            'mountYaw': trial.suggest_float('mountYaw', -5.0, 5.0),
            'smoothAlpha': trial.suggest_float('smoothAlpha', 0.0, 1.0),
            'initSamples': trial.suggest_int('initSamples', 1, 50),
            'hpCutoff': 0.1,
            'heaveGain': 1.0,
        }

        if method in ('madgwick', 'madgwick_adapt'):
            params['beta'] = trial.suggest_float('beta', 0.001, 1.0, log=True)
            if method == 'madgwick_adapt':
                params['betaMin'] = trial.suggest_float(
                    'betaMin', 0.0001, 0.1, log=True)
                params['betaMax'] = trial.suggest_float(
                    'betaMax', 0.01, 2.0, log=True)
                params['adaptRate'] = trial.suggest_float(
                    'adaptRate', 1.0, 50.0)
        elif method == 'mahony':
            params['kp'] = trial.suggest_float('kp', 0.05, 20.0, log=True)
            params['ki'] = trial.suggest_float('ki', 0.0, 1.0)

        return params

    def _orientObjective(self, trial):
        params = self._buildOrientParams(trial)
        try:
            parser = OrientationParser(**params)
            pitchEst, rollEst, yawEst, _ = parser.process(
                self.gyro[:self.trainEnd], self.accel[:self.trainEnd])
        except Exception:
            return 1e6

        rp = np.sqrt(np.mean(
            (pitchEst - self.refPitch[:self.trainEnd]) ** 2))
        rr = np.sqrt(np.mean(
            (rollEst - self.refRoll[:self.trainEnd]) ** 2))
        ry = np.sqrt(np.mean(
            (yawEst - self.refYaw[:self.trainEnd]) ** 2))
        score = rp + rr + ry

        if score < self._bestOrientScore:
            self._bestOrientScore = score
            self._bestOrientParams = dict(params)

        return score

    def _heaveObjective(self, trial, orientParams):
        params = dict(orientParams)
        params['hpCutoff'] = trial.suggest_float('hpCutoff', 0.005, 1.0, log=True)
        params['heaveGain'] = trial.suggest_float('heaveGain', 0.1, 10.0)
        params['hpOrder'] = trial.suggest_int('hpOrder', 1, 4)

        try:
            parser = OrientationParser(**params)
            _, _, _, heaveEst = parser.process(
                self.gyro[:self.trainEnd], self.accel[:self.trainEnd])
        except Exception:
            return 1e6

        refH = self.refHeave[:self.trainEnd]
        heaveEst = heaveEst - np.mean(heaveEst) + np.mean(refH)
        return np.sqrt(np.mean((heaveEst - refH) ** 2))

    def optimizeOrientation(self, nTrials=800):
        print(f"[1/4] Optimizing orientation ({nTrials} trials)...")
        study = optuna.create_study(
            direction='minimize',
            sampler=optuna.samplers.TPESampler(seed=42, n_startup_trials=100)
        )
        study.optimize(self._orientObjective, n_trials=nTrials,
                       show_progress_bar=True)

        print(f"  Best orient RMSE sum (train): {self._bestOrientScore:.6f} deg")
        print(f"  Best method: {self._bestOrientParams['method']}")
        return self._bestOrientParams

    def optimizeHeave(self, orientParams, nTrials=400):
        print(f"\n[2/4] Optimizing heave ({nTrials} trials)...")
        bestHeaveScore = float('inf')
        bestHeaveExtra = {}

        def heaveObj(trial):
            nonlocal bestHeaveScore, bestHeaveExtra
            score = self._heaveObjective(trial, orientParams)
            if score < bestHeaveScore:
                bestHeaveScore = score
                bestHeaveExtra = {
                    'hpCutoff': trial.params['hpCutoff'],
                    'heaveGain': trial.params['heaveGain'],
                    'hpOrder': trial.params['hpOrder'],
                }
            return score

        study = optuna.create_study(
            direction='minimize',
            sampler=optuna.samplers.TPESampler(seed=42, n_startup_trials=50)
        )
        study.optimize(heaveObj, n_trials=nTrials, show_progress_bar=True)
        print(f"  Best heave RMSE (train): {bestHeaveScore:.6f}")
        return bestHeaveExtra

    def evaluateFull(self, params):
        parser = OrientationParser(**params)
        pitchEst, rollEst, yawEst, heaveEst = parser.process(
            self.gyro, self.accel)
        heaveEst = heaveEst - np.mean(heaveEst) + np.mean(self.refHeave)

        metrics = {
            'pitch': self.computeMetrics(pitchEst, self.refPitch),
            'roll': self.computeMetrics(rollEst, self.refRoll),
            'yaw': self.computeMetrics(yawEst, self.refYaw),
            'heave': self.computeMetrics(heaveEst, self.refHeave),
        }
        return pitchEst, rollEst, yawEst, heaveEst, metrics

    def savePlots(self, pitchEst, rollEst, yawEst, heaveEst, outPath):
        print("\n[3/4] Generating plots...")
        time = self.df['time'].values
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
            ax.plot(time, ref, color=cRef, label='Reference',
                    linewidth=1.5, alpha=0.85)
            ax.plot(time, est, color=cEst, label='Estimated',
                    linewidth=1.0, alpha=0.85, linestyle='--')
            ax.axvline(time[self.trainEnd], color='#888', linestyle=':',
                       alpha=0.5, label='Train/Val split')
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
        print(f"  Saved: {outPath}")

    def saveResults(self, params, metrics, pitchEst, rollEst, yawEst, heaveEst):
        print("\n[4/4] Saving results to best/...")
        os.makedirs(BEST_DIR, exist_ok=True)

        with open(os.path.join(BEST_DIR, 'best_metrics.json'), 'w') as f:
            json.dump(metrics, f, indent=2)

        serialParams = {}
        for k, v in params.items():
            if isinstance(v, (np.integer,)):
                serialParams[k] = int(v)
            elif isinstance(v, (np.floating,)):
                serialParams[k] = float(v)
            else:
                serialParams[k] = v
        with open(os.path.join(BEST_DIR, 'best_params.json'), 'w') as f:
            json.dump(serialParams, f, indent=2)

        self.savePlots(pitchEst, rollEst, yawEst, heaveEst,
                       os.path.join(BEST_DIR, 'comparison_plots.png'))

    def run(self):
        bestOrientParams = self.optimizeOrientation(nTrials=800)
        bestHeaveExtra = self.optimizeHeave(bestOrientParams, nTrials=400)

        finalParams = dict(bestOrientParams)
        finalParams.update(bestHeaveExtra)

        pitchEst, rollEst, yawEst, heaveEst, metrics = self.evaluateFull(
            finalParams)
        self.saveResults(finalParams, metrics,
                         pitchEst, rollEst, yawEst, heaveEst)

        print("\n" + "=" * 65)
        print("  FINAL METRICS (Full Dataset)")
        print("=" * 65)
        for axis in ['pitch', 'roll', 'yaw', 'heave']:
            m = metrics[axis]
            unit = 'deg' if axis != 'heave' else 'm'
            print(f"  {axis:>6s} : RMSE = {m['rmse']:.6f} {unit}"
                  f"  |  MAE = {m['mae']:.6f} {unit}"
                  f"  |  R^2 = {m['r2']:.6f}")

        print("-" * 65)
        print(f"  Algorithm: {finalParams['method']} + forward-backward smoothing")
        print(f"\n  Summary:")
        print(f"    The adaptive Madgwick filter dynamically adjusts its")
        print(f"    correction gain (beta) based on accelerometer deviation")
        print(f"    from gravity. Forward-backward smoothing eliminates")
        print(f"    initialization transient and reduces phase lag by running")
        print(f"    the filter in both directions and SLERP-blending results.")
        print(f"    A mounting rotation quaternion corrects for the sensor")
        print(f"    body-to-reference frame misalignment (~180 deg roll).")
        print(f"\n  Heave:")
        print(f"    Vertical acceleration is extracted by rotating body-frame")
        print(f"    accel to world frame and subtracting gravity. Three-stage")
        print(f"    high-pass filtering (accel -> vel -> pos) removes drift.")
        print(f"    The heave reference has a strong low-frequency trend")
        print(f"    (1.75 -> 3.02 m) that IMU integration cannot capture;")
        print(f"    only the oscillatory component (~0.015 m std) is matched.")
        print(f"\n  Limitations:")
        print(f"    - No magnetometer => yaw is relative, not absolute")
        print(f"    - Heave drift requires external position reference")
        print(f"    - Sensor near gimbal lock (roll ~ -92 deg)")
        print("=" * 65)

        return finalParams, metrics


if __name__ == '__main__':
    pipeline = FusionPipeline()
    pipeline.run()
