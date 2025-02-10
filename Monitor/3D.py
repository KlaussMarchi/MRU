import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
from time import time
import threading


class TimeGraph:
    def __init__(self, xLim=[0, 5], size=200):
        self.xLim = xLim
        self.size = size
        self.xDados = []
        self.yDados = []
        self.zDados = []
        self.startTime = time()
        self.lastValue = None

    def getValue(self):
        t = time() - self.startTime
        value = np.sin(t / 2)
        self.lastValue = (t, value, np.cos(t / 2))  # Gera valores de x, y e z

    def handleThread(self):
        while True:
            self.getValue()

    def update(self, frame):
        if self.lastValue is not None:
            t, y, z = self.lastValue
            self.xDados.append(t)
            self.yDados.append(y)
            self.zDados.append(z)

            # Limitar o tamanho das listas
            self.xDados = self.xDados[-self.size:]
            self.yDados = self.yDados[-self.size:]
            self.zDados = self.zDados[-self.size:]
            self.lastValue = None

        # Atualizar limites
        self.ax.set_xlim(min(self.xDados, default=0),  max(self.xDados, default=5))
        self.ax.set_ylim(min(self.yDados, default=-1), max(self.yDados, default=1))
        self.ax.set_zlim(min(self.zDados, default=-1), max(self.zDados, default=1))

        # Atualizar a linha
        self.line.set_data(self.xDados, self.yDados)
        self.line.set_3d_properties(self.zDados)
        return (self.line, )

    def start(self):
        thread = threading.Thread(target=self.handleThread)
        thread.daemon = True
        thread.start()

        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')

        # Linha inicial vazia
        self.line, = self.ax.plot([], [], [], color='blue')
        self.ax.set_title('Real-time 3D Plot')
        self.ax.set_xlabel('Time')
        self.ax.set_ylabel('Y')
        self.ax.set_zlabel('Z')

        # Animação
        ani = FuncAnimation(self.fig, self.update, interval=1000, blit=False)
        plt.show()



def getArduinoData():
    global device

    try:
        return eval(device.readline().decode('utf-8'))
    except:
        return None



if __name__ == "__main__":
    graph = TimeGraph(xLim=[0, 10], size=50)
    graph.start()
