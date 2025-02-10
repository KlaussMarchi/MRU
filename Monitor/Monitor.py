import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np
from time import time, sleep
import threading
import serial
import serial.tools.list_ports


class KalmanFilter:
    def __init__(self, A, B, H, Q, R, P, x):
        self.A = A
        self.B = B
        self.H = H
        self.Q = Q
        self.R = R
        self.P = P
        self.x = x

    def predict(self, u=0):
        self.x = np.dot(self.A, self.x) + np.dot(self.B, u)
        self.P = np.dot(np.dot(self.A, self.P), self.A.T) + self.Q

    def update(self, z):
        y = z - np.dot(self.H, self.x)  # Inovação
        S = np.dot(np.dot(self.H, self.P), self.H.T) + self.R  # Covariância da inovação
        K = np.dot(np.dot(self.P, self.H.T), np.linalg.inv(S))  # Ganho de Kalman
        self.x = self.x + np.dot(K, y)
        I = np.eye(self.A.shape[0])  # Matriz identidade
        self.P = np.dot(I - np.dot(K, self.H), self.P)

    def predictFuture(self, steps, U=None):
        original_x = self.x.copy()  # Salva o estado atual
        original_P = self.P.copy()  # Salva a covariância atual

        predictions = []
        u_index = 0

        for step in range(steps):
            if U is not None and u_index < len(U):
                u = np.array(U[u_index]).reshape(-1, 1)  # Transforma em vetor coluna
                u_index += 1
            else:
                u = np.zeros((self.B.shape[1], 1))  # Entrada padrão: zero

            self.predict(u)
            predictions.append(self.x.copy())  # Salva o estado predito

        self.x = original_x  # Restaura o estado original
        self.P = original_P  # Restaura a covariância original
        return predictions


    def getState(self):
        return self.x


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
        self.a = 0
        dt = 0.100
        
        A = np.array([
            [1, dt, 0],     # Posição depende da velocidade
            [0, 1, 0],      # Velocidade permanece constante
            [0, 0, 1],
        ])

        B = np.array([
            [0.5*dt**2],  # Contribuição da aceleração para a posição
            [dt],         # Contribuição da aceleração para a velocidade
            [0]           # Contribuição da aceleração para a aceleração    
        ])

        H = np.array([
            [1, 0, 0],     # queremos posição
            [0, 1, 0],     # queremos velocidade
            [0, 0, 1]      # queremos aceleração
        ])

        Q = np.array([
            [0.001, 0, 0],  # variância na posição (velocidade de reação a mudanças)
            [0, 0.001, 0],  # variância na posição (velocidade de reação a mudanças)
            [0, 0, 0.1]
        ])

        R = np.array([
            [0.2, 0, 0],  # Ruído na posição     (quanto menor, o kalman confia nos dados)
            [0, 0.2, 0],  # Ruído na velocidade  (quanto menor, o kalman confia nos dados)
            [0, 0, 0.6]
        ])

        x = np.array([
            [0],        # Posição inicial
            [0],        # Velocidade inicial
            [0]
        ])

        P = np.eye(3)
        self.kalman = KalmanFilter(A, B, H, Q, R, P, x)

    
    def handleThread(self):
        print('starting thread')

        while True:
            value = getArduinoData()
            print('value: ', value)

            if value is not None:
                t = value['t']
                a = value['az']

                dt = 0.100
                self.v = self.v + a*dt
                self.x = self.x + self.v*dt + (a*0.5*dt**2)
                self.a = a

                U = np.array([[self.x], [self.v], [self.a]])
                self.kalman.predict()
                self.kalman.update(U)
                result = self.kalman.getState()[0, 0]

                self.lastValue['x'] = t
                self.lastValue['y'] = result


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
