from Sensor.index import Sensor
from Serial.index import Device
from Filter.laplace import LaplaceFilter
from time import sleep
import matplotlib.pyplot as plt


def main():
    device = Device()
    device.connect()

    filter = LaplaceFilter()

    sensor = Sensor()
    sensor.setup()
    sensor.startStream()

    while True:
        filtered = filter.update(sensor.variables)
        device.sendData(filtered)


if __name__ == '__main__':
    filter = LaplaceFilter(Ts=1.5, UP=0.01, T=0.05)
    sensor = Sensor()
    sensor.setup()
    #sensor.startStream()
    x = []
    y = []
    z = []

    for i in range(500):
        response = sensor.getVariables()
        print(f'[{i}] {response}')

        if response is None:
            continue

        x.append(response['t'])
        y.append(response['az'])
        z.append(filter.update(response['az']))
        sleep(0.05)

    plt.plot(x, y)
    plt.plot(x, z)
    plt.legend()
    plt.grid()
    plt.show()