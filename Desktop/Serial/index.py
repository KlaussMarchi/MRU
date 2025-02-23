import serial, json
import serial.tools.list_ports
from time import sleep, time
import threading


def sendEvent(eventType, message, delay=0.0):
    status = None

    if eventType == 'error':
        print(f'\033[31m[error]\033[0m', message)
        status = False
    elif eventType == 'success':
        print(f'\033[34m[success]\033[0m', message)
        status = True
    else:
        print(f'\033[32m[event]\033[0m', message)

    if delay > 0.0:
        sleep(delay)

    return status


class Device:
    device = None
    port   = None
    rate   = None
    data   = None

    def __init__(self, port=None, rate=9600, timeout=1.0):
        self.port = port
        self.rate = rate
        self.timeout = timeout

    def connect(self):
        self.port = self.port if self.port is not None else self.autoSelection()
        sendEvent('event', f'trying connection: {self.port}')
        
        if self.device and self.device.is_open:
            return sendEvent('success', f'already connected')

        try:
            self.device = serial.Serial(self.port, self.rate, timeout=self.timeout)
            return sendEvent('success', 'device connected successfully')
        except Exception as error:
            self.device = None
            return sendEvent('error', error, delay=3.0)
    
    def autoSelection(self):
        ports  = [port for port in serial.tools.list_ports.comports()]
        target = 0

        if not ports:
            return sendEvent('error', 'no port found')

        for i, port in enumerate(ports):
            if 'usb' in str(port).lower():
                target = i
        
        selected = str(ports[target]).strip()
        parts    = selected.split(' ')  

        if selected == '' or len(parts) == 0:
            return sendEvent('error', f'parts: {parts}')

        return parts[0].strip()

    def sendData(self, message, breakLine=True):
        if self.device is None:
            return sendEvent('error', 'device not settled')
        
        message = message.strip()

        if breakLine:
            message = message + '\r\n' 

        try:
            self.device.write(message.encode())
        except Exception as error:
            return sendEvent('error', error)
        
        return True
    
    def getData(self, timeout=5.0):
        if self.device is None:
            return None

        response  = None
        startTime = time()

        try:
            while self.available() and time() - startTime < timeout: 
                response = self.device.readline().decode('utf-8').strip()
        except Exception as error:
            if response is not None:
                return response

            return sendEvent('error', error)

        return response
    
    def available(self):
        if not self.device:
            return 0
        
        return self.device.in_waiting
    
    def getResponse(self, msg):
        if not self.sendData(msg):
            return None

        return self.getData(10)

    def startStream(self, command='start'):
        if not self.sendData(command) or self.active:
            return sendEvent('error', 'cant start stream', 5.0)

        while not self.available():
            continue
        
        sendEvent('success', 'stream started')
        thread = threading.Thread(target=self.handleStream)
        thread.daemon = True
        thread.start()

    def handleStream(self):
        while True:
            try:
                sendEvent('event', 'enviando...')
                response = self.getData()

                if not response:
                    continue

                self.data = json.loads(response)
            except Exception as error:
                sendEvent('error', error)
                continue

    def getTarget(self):
        if self.data is None:
            return None
        
        return self.data['t'], self.data['ax']

