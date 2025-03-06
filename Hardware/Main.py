from Sensor.index import Sensor, sensorTest
from Device.index import Device
from Filter.laplace import LaplaceFilter
from time import sleep


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
    main()
