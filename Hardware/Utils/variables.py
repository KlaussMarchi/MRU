import numpy as np


# ------------------ KALMAN FILTER ---------------------------------
n  = 3
P  = np.eye(n) # Covariância inicial do estado
dt = 0.2

A = np.array([
    [1, dt, 0],     # Posição depende da velocidade
    [0, 1, 0],      # Velocidade permanece constante
    [0, 0, 0],
])

B = np.array([
    [0.5*dt**2],  # Contribuição da aceleração para a posição
    [dt],         # Contribuição da aceleração para a velocidade
    [0]           # Contribuição da aceleração para a aceleração    
])

H = np.array([
    [1, 0, 0],     # queremos posição
    [0, 1, 0],     # queremos velocidade
    [0, 0, 1]      # queremos aceleração
])

Q = np.array([
    [0.001, 0, 0],  # variância na posição (velocidade de reação a mudanças)
    [0, 0.001, 0],  # variância na posição (velocidade de reação a mudanças)
    [0, 0, 0.1]
])

R = np.array([
    [0.1, 0, 0],  # Ruído na posição     (quanto menor, o kalman confia nos dados)
    [0, 0.1, 0],  # Ruído na velocidade  (quanto menor, o kalman confia nos dados)
    [0, 0, 0.1]
])

x = np.array([
    [0],        # Posição inicial
    [0],        # Velocidade inicial
    [0]
])