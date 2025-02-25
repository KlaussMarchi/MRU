from Utils.variables import A, B, H, Q, R, P, x, dt
from Filter.kalman import KalmanFilter
from Utils.functions import sendEvent
from Utils.variables import dt
from time import time


class Filter:
    variables = {}
    kalman = None
    startTime = None

    def __init__(self):
        pass

    def setup(self):
        self.kalman = KalmanFilter(A, B, H, Q, R, P, x)
        self.startTime = time()

    def update(self, variables):
        if time() - self.startTime < dt:
            return variables
        
        self.startTime = time()
        return variables


