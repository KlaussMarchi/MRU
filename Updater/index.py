from Device.index import Device
from utils.functions import sendEvent
from time import sleep, time
import base64, io


class SerialUpdater:
    CHUNK_SIZE = 2048 
    device = None
    percentage = -1

    def __init__(self, device, filePath):
        self.file   = open(filePath, 'rb')
        self.device = device

        sendEvent('event', f'file downloaded {self.file.read(10)}')
        print()
    
    def start(self):
        sendEvent('event', 'aguardando sincronização')
        
        for i in range(5):
            if self.device.expect('$MICACK!', '$ackoneledge!', timeout=5.0, show=True):
                break
        
        sendEvent('success', 'Dispositivo Sincronizado', end='\n\n')
        sleep(1.5)
        self.device.expect('STARTING_UPDATE', command='__updt__')
        sendEvent('event', 'update iniciado')
        sleep(0.5)
        self.upload()

    def upload(self):
        self.percentage = 0
        startProg = time()
        
        self.file.seek(0)
        fileBytes = self.file.read()
        total     = len(fileBytes)
        
        firmware  = io.BufferedReader(io.BytesIO(fileBytes))
        sum_bytes = 0.0 

        while self.percentage < 100:
            chunk = firmware.read(self.CHUNK_SIZE)

            if not chunk:
                break
                
            self.write(chunk, self.percentage)
            
            if not self.device.expect('WRITTEN', show=True, timeout=30.0):
                return sendEvent('error', 'erro ao atualizar')
            
            sum_bytes += len(chunk)
            self.percentage = (sum_bytes/total)*100

        timeout = int(time() - startProg)
        sendEvent('success', f'completed in {timeout} seg! verifying result\n')
        sleep(11.0)
        line = self.device.get()
        sendEvent('arduino', line, 'blue')

    def write(self, chunk, percentage):
        chunkString = base64.b64encode(chunk).decode('utf-8')
        startTime   = time()

        message = f'${chunkString}!'
        sample  = (message[:25] + ' ... ' + message[-25:])
        
        for i in range(0, len(message), 64):
            self.device.device.write(message[i:i+64].encode())
            sleep(0.002)
        
        timePassed = int((time() - startTime) * 1000)
        logText    = f'{timePassed}ms - {len(chunkString)} bytes - {percentage:.2f}% - chunk: {sample}'
        sendEvent('python', logText, 'red')


if __name__ == '__main__':
    device = Device(rate=9600)
    device.port = '/dev/ttyACM0'
    device.connect()

    updater = SerialUpdater(device, '../Hardware/Embedded/Main/build/esp32.esp32.esp32s3/Main.ino.bin')
    updater.start()
