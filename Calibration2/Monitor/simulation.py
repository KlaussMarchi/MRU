import numpy as np
import pandas as pd
import os
import json

script_path = os.path.abspath(__file__)
base_dir = os.path.dirname(script_path)
os.chdir(base_dir)

# Criar pastas
folders = ['output/reference', 'output/mru', 'output/target']
for f in folders:
    os.makedirs(f, exist_ok=True)

# Tempo: 1335 segundos com amostragem de 10 Hz (dt = 0.1)
# Com as folgas de 10s, o tempo total aumentou.
dt = 0.1
time = np.arange(0, 1335, dt)

# Inicializar ângulos
pitch_deg = np.zeros_like(time)
roll_deg = np.zeros_like(time)

# 0 a 15s: Aquecimento + folga pré-pitch (none)
# 15 a 315s: Varia pitch
mask_pitch = (time >= 15) & (time < 315)
pitch_deg[mask_pitch] = 5 * np.sin(2 * np.pi * 0.1 * (time[mask_pitch] - 15))

# 315 a 325s: Folga entre pitch e roll (none)
# 325 a 625s: Varia roll
mask_roll = (time >= 325) & (time < 625)
roll_deg[mask_roll] = 5 * np.sin(2 * np.pi * 0.1 * (time[mask_roll] - 325))

# Estimativa de Giroscópio (deg/s) - Derivada do ângulo
wy_deg_s = np.zeros_like(time)
wy_deg_s[mask_pitch] = 5 * (2 * np.pi * 0.1) * np.cos(2 * np.pi * 0.1 * (time[mask_pitch] - 15))

wx_deg_s = np.zeros_like(time)
wx_deg_s[mask_roll] = 5 * (2 * np.pi * 0.1) * np.cos(2 * np.pi * 0.1 * (time[mask_roll] - 325))

wz_deg_s = np.zeros_like(time)

# Estimativa de Acelerômetro (g) - Projeção da gravidade
pitch_rad = np.radians(pitch_deg)
roll_rad = np.radians(roll_deg)

ax_g = np.sin(pitch_rad)
ay_g = -np.sin(roll_rad) * np.cos(pitch_rad)
az_g = np.cos(roll_rad) * np.cos(pitch_rad)

# Função auxiliar para gerar DataFrame com ruído
def generate_dataframe(noise_level_angles, noise_level_gyro, noise_level_accel):
    pitch_noisy = pitch_deg + np.random.normal(0, noise_level_angles, len(time))
    roll_noisy = roll_deg + np.random.normal(0, noise_level_angles, len(time))
    
    wx_noisy = wx_deg_s + np.random.normal(0, noise_level_gyro, len(time))
    wy_noisy = wy_deg_s + np.random.normal(0, noise_level_gyro, len(time))
    wz_noisy = wz_deg_s + np.random.normal(0, noise_level_gyro, len(time))
    
    ax_noisy = ax_g + np.random.normal(0, noise_level_accel, len(time))
    ay_noisy = ay_g + np.random.normal(0, noise_level_accel, len(time))
    az_noisy = az_g + np.random.normal(0, noise_level_accel, len(time))
    
    # Escalar para corresponder aos dados reais (inteiros grandes)
    df = pd.DataFrame({
        'ay': (ay_noisy * 1000000).astype(int),
        'roll': (roll_noisy * 100).astype(int),
        'wz': (wz_noisy * 10000).astype(int),
        'tmp': 56.5 + np.random.normal(0, 0.5, len(time)),
        'wy': (wy_noisy * 10000).astype(int),
        'pitch': (pitch_noisy * 100).astype(int),
        'e': 0.288,
        'wx': (wx_noisy * 10000).astype(int),
        'az': (az_noisy * 1000000).astype(int),
        'time': time,
        'ax': (ax_noisy * 1000000).astype(int),
        'yaw': 10800 + np.random.normal(0, 50, len(time)).astype(int)
    })
    
    return df

# Plate (Reference) - Apenas o movimento ideal, sem ruído
df_plate = generate_dataframe(noise_level_angles=0.0, noise_level_gyro=0.0, noise_level_accel=0.0)

# MRU (Kongsberg) - Um pouco de ruído
df_mru = generate_dataframe(noise_level_angles=0.05, noise_level_gyro=0.1, noise_level_accel=0.01)

# Target (Measure) - Um pouco mais de ruído
df_target = generate_dataframe(noise_level_angles=0.2, noise_level_gyro=0.5, noise_level_accel=0.05)

# Salvar em CSV
df_plate.to_csv('output/reference/data.csv', index=False)
df_mru.to_csv('output/mru/data.csv', index=False)
df_target.to_csv('output/target/data.csv', index=False)

# Criar arquivo info.json
info = {
    "description": "Simulation generated data: Plate (reference), MRU (Kongsberg), and Target (Measure)",
    "limits": {
        "dynamic": [15, 600],
        "static":  [700, 999999999]
    }
}
with open('output/info.json', 'w') as f:
    json.dump(info, f, indent=4)

print("Simulação concluída. Os arquivos foram salvos na pasta 'output/'.")
