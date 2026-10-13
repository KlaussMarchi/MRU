import numpy as np
import pandas as pd

G0          = 9.80665    # m/s² POR g: O MODO HR DO KERNEL ENTREGA g·1e6
STILL_RATE  = 0.3        # °/s: A SEATEX PARADA MEDE 0,02 °/s DE RUÍDO
STILL_TIME  = 3.0        # s: MAIS QUE UM PERÍODO DO PÊNDULO, PARA A INVERSÃO NÃO CONTAR COMO REPOUSO


# GRAVAÇÃO BRUTA DO PÊNDULO (target = Kernel-120, reference = Seatex MRU 5) NO ESQUEMA DO data.csv
def loadRecording(path):
    target = pd.read_csv(f'{path}/target/data.csv')
    ref    = pd.read_csv(f'{path}/reference/data.csv')
    step   = np.diff(ref.sample_time.to_numpy(), prepend=ref.sample_time.iloc[0] - 1e8) % 1e9 / 1e9    # RELÓGIO DA SEATEX: ns DENTRO DO SEGUNDO
    df     = pd.DataFrame({'time': np.round(np.cumsum(step) - step[0], 6)})

    df[['target_ax', 'target_ay', 'target_az']]       = target[['ax', 'ay', 'az']].to_numpy() / 1e6 * G0
    df[['target_wx', 'target_wy', 'target_wz']]       = target[['wx', 'wy', 'wz']].to_numpy() / 1e5
    df[['target_roll', 'target_pitch', 'target_yaw']] = target[['roll', 'pitch', 'yaw']].to_numpy() / 1e3
    df[['ref_roll', 'ref_pitch', 'ref_yaw']]          = np.degrees(ref[['roll', 'pitch', 'yaw']].to_numpy())
    df['ref_heave']                                   = ref.la_pos_mon_d.to_numpy()
    df[['ref_q0', 'ref_q1', 'ref_q2', 'ref_q3']]      = ref[['q0', 'q1', 'q2', 'q3']].to_numpy()
    df[['ref_ax', 'ref_ay', 'ref_az']]                = ref[['ax', 'ay', 'az']].to_numpy()
    df[['ref_wx', 'ref_wy', 'ref_wz']]                = np.degrees(ref[['wx', 'wy', 'wz']].to_numpy())

    rate = pd.Series(np.linalg.norm(df[['ref_wx', 'ref_wy', 'ref_wz']], axis=1))
    size = int(round(STILL_TIME / np.median(step)))
    df.insert(1, 'static', rate.rolling(size, center=True, min_periods=1).max().to_numpy() < STILL_RATE)
    return df[np.diff(df.time, prepend=-1.0) > 1e-3].reset_index(drop=True)
