
from objects.device.index import Device
from objects.sensors.CRS0304S.index import CRS0304S

device = Device()
device.setup()

sensor1 = CRS0304S()
sensor1.setup()

while True:
    sensor1.handle()

    device.handle()