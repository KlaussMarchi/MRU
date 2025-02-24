from Sensor.index import Sensor
from Serial.index import Device
from Filter.index import Filter


if __name__ == '__main__':
    device = Device()
    device.connect()

    filter = Filter()
    filter.setup()

    sensor = Sensor()
    sensor.setup()
    sensor.startStream()

    while True:
        filtered = filter.update(sensor.variables)
        device.sendData(filtered)