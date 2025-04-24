#from Sensor.index import Sensor, sensorTest
from Filter.laplace import LaplaceFilter
from Filter.kalman import KalmanFilter
from Filter.smooth import Smooth
from Filter.fusion import joinData

from Device.index import Device
from Plotter.index import TimeGraph
from time import sleep, time
import numpy as np

A = np.array([[1]])     # Estado constante
B = np.array([[0]])     # Sem controle
H = np.array([[1]])     # Observação direta
Q = np.array([[1e-2]])  # Variância do processo
R = np.array([[0.5]])   # Variância da medição
P = np.array([[1]])     # Covariância inicial
x = np.array([[0]])     # Estado inicial

laplace = LaplaceFilter(Tp=0.4, UP=0.05)
kalman  = KalmanFilter(A, B, H, Q, R, P, x)
smooth  = Smooth(size=18)

device = Device(rate=115200)
device.connect()
device.startStream()
startTime = time()


def getData():
    data = device.getJson()

    if data is None:
        return

    value = data.get('gz')
    kalman.predict()
    kalman.update(np.array([[value]]))

    yKalman  = kalman.getState()[0, 0]
    yLaplace = laplace.update(value)
    ySmooth  = smooth.update(value)

    fRaw     = (value,    80**2)
    fKalman  = (yKalman,  18**2)
    fLaplace = (yLaplace, 15**2)
    fSmooth  = (ySmooth,  50**2)
    
    out0 = joinData(fRaw, fKalman, w=0.60)
    out1 = joinData(out0, fLaplace, w=0.50)
    out2 = joinData(out1, fSmooth, w=0.85)
+
    return time() - startTime, {
        'raw':     value,
        #'kalman':  yKalman,
        #'laplace': yLaplace,
        #'smooth':  ySmooth,
        'fusion':  out2[0]
    }

if __name__ == '__main__':
    graph = TimeGraph(callback=getData, xLim=[0, 5])
    graph.start()
