import numpy as np


class KalmanFilter:
    def __init__(self, A, B, H, Q, R, P, x):
        self.A = A
        self.B = B
        self.H = H
        self.Q = Q
        self.R = R
        self.P = P
        self.x = x

    def predict(self, u=0):
        self.x = np.dot(self.A, self.x) + np.dot(self.B, u)
        self.P = np.dot(np.dot(self.A, self.P), self.A.T) + self.Q

    def update(self, z):
        y = z - np.dot(self.H, self.x)  # Inovação
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R  # Covariância da inovação
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))  # Ganho de Kalman
        self.x = self.x + np.dot(K, y)
        I = np.eye(self.A.shape[0])  # Matriz identidade
        self.P = np.dot(I - np.dot(K, self.H), self.P)


    def predictFuture(self, steps, U=None):
        original_x = self.x.copy()  # Salva o estado atual
        original_P = self.P.copy()  # Salva a covariância atual

        predictions = []
        u_index = 0

        for step in range(steps):
            if U is not None and u_index < len(U):
                u = np.array(U[u_index]).reshape(-1, 1)  # Transforma em vetor coluna
                u_index += 1
            else:
                u = np.zeros((self.B.shape[1], 1))  # Entrada padrão: zero

            self.predict(u)
            predictions.append(self.x.copy())  # Salva o estado predito

        self.x = original_x  # Restaura o estado original
        self.P = original_P  # Restaura a covariância original
        return predictions

    def getState(self):
        return self.x