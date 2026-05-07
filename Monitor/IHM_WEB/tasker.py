from Protobuf.index import Protobuf
from time import time, sleep
import csv, os


class Tasker:
    def __init__(self, interval=600, fileName='DataBase.csv'):
        self.interval = interval
        self.fileName = fileName
        self.lastSave = 0
        self.protobuf = Protobuf()
        self.fields = [
            'timestamp', 'deviceTime', 'e', 
            'ax', 'ay', 'az', 'wx', 'wy', 'wz', 
            'pitch', 'roll', 'yaw', 'q0', 'q1', 'q2', 'q3'
        ]

    def setup(self):
        # Garante que estamos no diretório do script
        scriptPath = os.path.abspath(__file__)
        baseDir = os.path.dirname(scriptPath)
        os.chdir(baseDir)
        
        self.protobuf.setup()
        
        # Cria o cabeçalho se o arquivo não existir
        if not os.path.exists(self.fileName):
            with open(self.fileName, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.fields)
                writer.writeheader()

    def save(self, data):
        with open(self.fileName, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=self.fields)
            row = {
                'timestamp': time(),
                'deviceTime': data.get('time'),
                'e': data.get('e'),
                'ax': data.get('ax'),
                'ay': data.get('ay'),
                'az': data.get('az'),
                'wx': data.get('wx'),
                'wy': data.get('wy'),
                'wz': data.get('wz'),
                'pitch': data.get('pitch'),
                'roll': data.get('roll'),
                'yaw': data.get('yaw'),
                'q0': data.get('q0'),
                'q1': data.get('q1'),
                'q2': data.get('q2'),
                'q3': data.get('q3')
            }
            writer.writerow(row)

    def run(self):
        print(f"Monitorando Protobuf e Salvando em {self.fileName} a cada {self.interval/60} minutos.")
        self.lastSave = None

        try:
            while True:
                self.protobuf.handle()
                data      = self.protobuf.data
                firstTime = self.lastSave is None
                
                if not firstTime and time() - self.lastSave < self.interval:
                    sleep(0.01)
                    continue
            
                if not data:
                    continue
            
                self.save(data)
                self.lastSave = time()
                print(f"[{currentTime}] Amostra salva no CSV.")
            
        except KeyboardInterrupt:
            print("\nEncerrando Tasker...")
        except Exception as error:
            print(f"Erro: {error}")
            return self.run()

if __name__ == '__main__':
    tasker = Tasker(interval=5*60)
    tasker.setup()
    tasker.run()
