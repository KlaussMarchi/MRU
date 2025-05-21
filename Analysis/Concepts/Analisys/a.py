import numpy as np

def normalize(v):
    norm = np.linalg.norm(v)
    return v / norm if norm != 0 else v

# Estima o quaternion a partir da aceleração (apenas roll e pitch).
def get_q_a(ax, ay, az):
    # Normaliza vetor de aceleração
    ax, ay, az = normalize(np.array([ax, ay, az]))

    # Calcula ângulos
    pitch = np.arctan2(-ax, np.sqrt(ay**2 + az**2))
    roll  = np.arctan2(ay, az)
    yaw   = 0  # sem magnetômetro

    # Metade dos ângulos
    cy, sy = np.cos(yaw / 2), np.sin(yaw / 2)
    cp, sp = np.cos(pitch / 2), np.sin(pitch / 2)
    cr, sr = np.cos(roll / 2), np.sin(roll / 2)

    # Quaternion ZYX
    q0 = cr * cp * cy + sr * sp * sy
    q1 = sr * cp * cy - cr * sp * sy
    q2 = cr * sp * cy + sr * cp * sy
    q3 = cr * cp * sy - sr * sp * cy

    return np.array([q0, q1, q2, q3])  # [w, x, y, z]


# Atualiza o quaternion a partir da velocidade angular em rad/s
def get_q_omega(q, wx, wy, wz, dt):
    q = np.array(q)
    omega = np.array([0.0, wx, wy, wz])
    q_dot = 0.5 * quaternion_product(q, omega)
    q_new = q + q_dot * dt
    return normalize(q_new)


# Produto de quaternions: q1 ⊗ q2
def quaternion_product(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2

    w = w1*w2 - x1*x2 - y1*y2 - z1*z2
    x = w1*x2 + x1*w2 + y1*z2 - z1*y2
    y = w1*y2 - x1*z2 + y1*w2 + z1*x2
    z = w1*z2 + x1*y2 - y1*x2 + z1*w2

    return np.array([w, x, y, z])


# ─────────────────────────────────────────────
# Exemplo de uso

# Dados simulados
ax, ay, az = 0.0, 0.0, 9.81  # vetor aceleração (m/s²)
wx, wy, wz = 0.1, 0.2, 0.05  # velocidade angular (rad/s)
dt = 0.01  # tempo em segundos

# Estima q_a
q_a = get_q_a(ax, ay, az)

# Inicializa quaternion com q_a
q = q_a.copy()

# Atualiza com velocidade angular
q_w = get_q_omega(q, wx, wy, wz, dt)

print("q_a (aceleração):", q_a)
print("q_w (gyro):      ", q_w)
