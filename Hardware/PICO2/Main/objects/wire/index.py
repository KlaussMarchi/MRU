from machine import I2C, Pin
from time import sleep

class Wire:
    def __init__(self, bus_id, sda, scl, freq=400000, address=0x68):
        self._i2c   = I2C(bus_id, sda=Pin(sda), scl=Pin(scl), freq=freq)
        addresses    = self.scan()
        
        if len(addresses) == 0:
            self.address = None
        elif address in addresses:
            self.address = address
        else:
            self.address = addresses[0]

        print(f'(wire) sda={sda} scl={scl} - devices found: {[hex(address) for address in addresses]}')
        print(f'(wire) sda={sda} scl={scl} - selected: {hex(self.address)}')
        sleep(1.0)
    
    def write(self, address, registerAddress, value):
        try:
            self._i2c.writeto_mem(address, registerAddress, bytes([value]))
            return True
        except:
            return False
    
    def read(self, address, registerAddress, count=1):
        try:
            return self._i2c.readfrom_mem(address, registerAddress, count)
        except:
            return False
    
    def scan(self):
        return self._i2c.scan()
    
