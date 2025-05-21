#from Sensor.index import Sensor, sensorTest
from Filter.laplace import LaplaceFilter
from Filter.fusion import joinData, KalmanFusion

from Device.index import Device
from Plotter.index import TimeGraph
from time import sleep, time
import numpy as np

DELTA_SENSOR_1 = 0.65
DELTA_SENSOR_2 = 0.45
dt = 0.05

x0 = 0
P0 = 2**2
Q  = 1.8
R  = np.diag([DELTA_SENSOR_1**2, DELTA_SENSOR_2**2])  
kalman  = KalmanFusion(x0, P0, Q, R)

filter1 = LaplaceFilter(Tp=0.20, UP=0.15, dt=dt)
filter2 = LaplaceFilter(Tp=0.50, UP=0.05, dt=dt)

device = Device(rate=115200)
device.connect()
device.startStream()

startTime = time()
target    = 'gz'

def getData():
    data = device.getJson()

    if data is None:
        return
    
    s1 = filter1.update(data['sensor1'][target])
    s2 = filter2.update(data['sensor2'][target])

    data = np.array([s1, s2])
    kalman.predict()
    output = kalman.update(data)

    return time() - startTime, {
        'sensor1': s1,
        'sensor2': s2,
        'fusion':  output
    }

if __name__ == '__main__':
    graph = TimeGraph(callback=getData, xLim=[0, 6])
    graph.start()
