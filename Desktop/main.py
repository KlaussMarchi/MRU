from Device.index import device
from Serial.index import serial

device.connect()
print('iniciado\n')

while True:
    size = device.available()
    
    if 0 < size < 30:
        print(device.get())

    if not serial.pressed():
        continue

    msg = input('msg: ').strip()
    device.send(msg)