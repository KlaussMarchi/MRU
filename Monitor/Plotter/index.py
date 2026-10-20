import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from time import time

for keymap in ['keymap.pan', 'keymap.zoom', 'keymap.home', 'keymap.yscale', 'keymap.xscale']:    # AS LETRAS DOS GRUPOS SÃO DO MONITOR
    plt.rcParams[keymap] = []


# A JANELA AO VIVO: O GRUPO DO MRU QUE A TECLA ESCOLHE, A MESA AO LADO E O STATUS EMBAIXO; q FECHA E SALVA
class Plotter:
    INTERVAL = 100    # ms ENTRE QUADROS

    groups = {
        'p': ['pitch'],
        'r': ['roll'],
        'y': ['yaw'],
        'a': ['ax', 'ay', 'az'],
        'w': ['wx', 'wy', 'wz'],
        'h': ['heave', 'heave_rate'],
        'o': ['q0', 'q1', 'q2', 'q3'],
        't': ['tmp']
    }

    def __init__(self, monitor):
        self.monitor = monitor
        self.group   = 'p'

    def start(self):
        panels      = 2 if self.monitor.reference else 1
        self.figure = plt.figure(figsize=(16, 6))
        self.axes   = [plt.subplot(1, panels, i + 1) for i in range(panels)]
        self.figure.canvas.mpl_connect('key_press_event', self.handle)
        self.animation = FuncAnimation(self.figure, self.update, interval=self.INTERVAL, cache_frame_data=False)
        plt.show()

    def handle(self, event):
        if event.key in self.groups:
            self.group = event.key

    def update(self, frame):
        self.monitor.update()
        self.draw(self.axes[0], self.monitor.target, self.groups[self.group], f'MRU ({self.group})')

        if self.monitor.reference:
            self.draw(self.axes[1], self.monitor.reference, ['pitch', 'roll'], 'Mesa de referência')

        self.figure.suptitle(self.monitor.getStatus(), fontsize=10)
        self.figure.supxlabel('teclas: p r y pitch, roll, yaw · a aceleração · w giro · h heave · o quaternion · t temperatura · q sai e salva', fontsize=9)

    def draw(self, axis, stream, keys, title):
        now  = time()
        rows = list(stream.buffer)
        axis.cla()

        for key in keys:
            points = [(host - now, values[key]) for host, values in rows if key in values]

            if points:
                axis.plot(*zip(*points), label=key, linewidth=1)

        axis.set_xlim(-stream.window, 0)
        axis.set_title(title); axis.set_xlabel('s até agora'); axis.grid(alpha=0.3)

        if axis.get_legend_handles_labels()[0]:
            axis.legend(loc='upper left')
