from Device.index import device
from utils.functions import sendEvent
from utils.classes import CustomForms
import keyboard


class SerialManager:
    def setup(self):
        sendEvent('event', 'Serial Manager Iniciado')

    def select(self):
        ports = device.scan()
        print('selecione a porta: ' )

        for i, port in enumerate(ports):
            print(f'[{i+1}] {port}')

        choice = int(input('sua opção: ').strip())
        device.port = ports[choice-1]
        device.reconnect()

    def print(self):
        if not device.available():
            return
        
        response = device.get()

        if response is None:
            return
        
        sendEvent('event', f'recebido: {response.strip()}')

        if len(response) > 30:
            print()

    def start(self):
        sendEvent('success', 'aguardando dados')

        while True:
            self.print()

            if not self.pressed():
                continue
            
            print()
            sendEvent('prompt', 'enviar: ', 'orange', end='')
            msg = input().strip()

            if len(msg) == 0:
                sendEvent('error', 'resposta muito curta\n')
                continue

            if msg.lower() == 'cancel':
                sendEvent('event', 'cancelado\n')
                continue
            
            if msg.lower() == 'exit':
                sendEvent('success', 'finalizado!\n')
                break

            device.send(msg)

    def pressed(self):
        caracteres = list("abcdefghijklmnopqrstuvwxyz0123456789")
        return any(keyboard.is_pressed(key) for key in list(keyboard.all_modifiers) + caracteres)
    

serial = SerialManager()