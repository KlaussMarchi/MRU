from Sensors.MPU6050.index import MPU6050
from Utils.functions import millis, sendEvent

class Monitor:
    def __init__(self, dt=0.1):
        self.startTime = 0
        self.MPU6050   = MPU6050()
        self.dt = dt*1000

    def start(self):
        self.startTime = millis()

    def handle(self):
        if millis() - self.startTime < self.dt:
            return
        
        self.startTime = millis()
        data = self.MPU6050.getVariables()
        print('data: ', data)

    def send()


if __name__ == '__main__':
    monitor = Monitor(dt=1.0)
    monitor.start()

    while True:
        monitor.handle()
