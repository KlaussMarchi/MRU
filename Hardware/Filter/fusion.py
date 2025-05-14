import numpy as np

class KalmanFusion:
    def __init__(self, x0=0.0, P0=1e3, Q=1e-2, R=np.array([[1.0]])):
        self.x = float(x0)
        self.P = float(P0)
        self.Q = float(Q)
        self.R = np.array(R, dtype=float)
        self.H = np.ones((self.R.shape[0], 1))

    def predict(self):
        self.P += self.Q

    def update(self, z):
        z = np.asarray(z, dtype=float).ravel()
        S = self.P * (self.H @ self.H.T) + self.R  
        invS = np.linalg.inv(S)                    
        K = (self.P * (self.H.T @ invS)).ravel()   

        y = z - (self.H[:, 0] * self.x)   
        self.x += K.dot(y)

        self.P *= (1.0 - float(K.dot(self.H[:, 0])))
        return self.x


def joinData(data1, data2, w=0.5):
    (x1, p1) = data1
    (x2, p2) = data2

    p1_inv = 1.0 / p1
    p2_inv = 1.0 / p2

    pf_inv = w * p1_inv + (1.0 - w) * p2_inv
    pf = 1.0 / pf_inv
    
    xf = pf * ( w * p1_inv * x1 + (1.0 - w) * p2_inv * x2 )
    return xf, pf