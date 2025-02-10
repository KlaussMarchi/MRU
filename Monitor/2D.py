import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
from time import time, sleep
import threading
import serial
import serial.tools.list_ports


class TimeGraph:
    startTime = time()

    def __init__(self, xLim=[0, 5], interval=0.1):
        self.xLim = xLim
        self.interval = interval
        self.size = len(np.arange(xLim[0], xLim[1], interval))
        self.lastValue = {'x': 0, 'y': 0}
        self.xDados    = [0]
        self.yDados    = [0]
        self.v = 0
        self.x = 0
    
    def handleThread(self):
        print('starting thread')

        while True:
            value = getArduinoData()
            print('value: ', value)

            if value is not None:
                t = value['t']
                a = value['az']

                dt = 0.030
                self.v = self.v + a*dt
                self.x = self.x + self.v*dt + (a*0.5*dt**2)
                
                self.lastValue['x'] = t
                self.lastValue['y'] = a


    def update(self, frame):
        t = self.lastValue['x']
        y = self.lastValue['y']

        self.xDados.append(t)
        self.yDados.append(y)
        
        self.xDados = self.xDados[-self.size:]
        self.yDados = self.yDados[-self.size:]

        if self.xDados[-1] > self.xLim[1]:
            self.xLim[0] += self.xDados[-1] - self.xLim[1]
            self.xLim[1] = self.xDados[-1]

        minY = min(self.yDados)
        maxY = max(self.yDados)
        minY = minY * 0.95 if minY > 0 else minY * 1.05
        maxY = maxY * 1.05 if maxY > 0 else maxY * 0.95

        self.ax.set_xlim(self.xLim[0], self.xLim[1])
        self.ax.set_ylim(minY, maxY)
        self.line.set_data(self.xDados, self.yDados)
        return (self.line, )

    def start(self):
        thread = threading.Thread(target=self.handleThread)
        thread.daemon = True
        thread.start()

        self.fig, self.ax = plt.subplots(figsize=(10, 6))
        self.line, = self.ax.plot(self.xDados, self.yDados, color='blue')
        self.ax.set_title('Plotter Serial')
        self.ax.set_xlabel('time')
        self.ax.set_ylabel('response')
        self.ax.grid()
        ani = FuncAnimation(self.fig, self.update, interval=self.interval*1000, blit=False, cache_frame_data=False)
        plt.show()



def getPort():
    ports  = [port for port in serial.tools.list_ports.comports()]

    target = 0

    for i, port in enumerate(ports):
        if 'usb' in str(port).lower():
            target = i

    selected = str(ports[target]).split(' ')[0].strip()
    return selected


def getArduinoData():
    global device

    try:
        return eval(device.readline().decode('utf-8'))
    except:
        return None


port   = getPort()
device = serial.Serial(port, 9600, timeout=10)
list   = []

print(f'conectado na {port}')
sleep(2)

device.write('start\r\n'.encode())
print('aguarde...')


if __name__ == "__main__":
    graph = TimeGraph(xLim=[0, 15], interval=0.001)
    graph.start()
