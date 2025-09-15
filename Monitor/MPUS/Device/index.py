import serial, ast
import serial.tools.list_ports
from time import sleep, time
from Utils.functions import sendEvent


class Device:
    device = None
    port   = None
    rate   = None
    data   = None

    def __init__(self, port=None, rate=9600, timeout=3.0):
        self.port = port
        self.rate = rate
        self.timeout = timeout

    def connect(self, delay=2.5):
        self.port = self.port if self.port is not None else self.scan()
        sendEvent('event', f'trying connection: {self.port}')
        
        if self.device and self.device.is_open:
            return sendEvent('success', f'already connected')
        try:
            self.device = serial.Serial(self.port, self.rate, timeout=self.timeout)
            return sendEvent('success', 'device connected successfully', delay=delay)
        except Exception as error:
            self.device = None
            return sendEvent('error', error, delay=3.0)
    
    def reconnect(self):
        if not bool(self.device and self.device.is_open):
            self.connect()

    def disconnect(self):
        if not self.device:
            return  
        try:
            if self.device.is_open:
                self.device.close()
        except Exception as error:
            sendEvent('error', error)
        
    def getPorts(self):
        return [port for port in serial.tools.list_ports.comports()]
    
    def scan(self):
        ports  = self.getPorts()
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
    
    def send(self, msg, breakLine=True):
        msg = msg.strip()
        
        if breakLine:
            msg = msg + '\r\n'

        try:
            self.device.write(msg.encode())
            #sendEvent('python', f'sent: {msg.strip()}', 'red')
        except Exception as error:
            return sendEvent('error', error)
        
        return True
    
    def wait(self, timeout=5):
        startTime = time()

        while time() - startTime < timeout:
            if self.available():
                return True

        return False
    
    def get(self, timeout=7.0):
        startTime = time()
        response = bytearray()

        try:
            while time() - startTime < timeout:
                size = self.device.in_waiting

                if size == 0:
                    sleep(0.005)
                    continue
                
                response.extend(self.device.read(size))
                
                if b'\n' in response:
                    break

            cleaned = response.decode('utf-8', errors='ignore').strip()
            return ''.join(c for c in cleaned if c not in '\r\n')
        except Exception as error:
            sendEvent('error', error)
            return None


    def getJson(self, timeout=5.0):
        data = self.get(timeout)

        if data is None:
            return None
        
        try:
            return ast.literal_eval(data)
        except Exception as error:
            sendEvent('error', error)
        
        return None

    def available(self):
        if not self.device:
            return 0
        
        totalBytes = self.device.in_waiting
        return totalBytes if totalBytes > 0 else 0
    
    def getResponse(self, msg):
        if not self.send(msg):
            return None

        return self.get(10)

    def clear(self, delay=0):
        self.device.reset_input_buffer()
        sleep(0.5)

        while self.available():
            try:
                self.device.read()
            except:
                continue
        
        self.device.reset_input_buffer()
        sleep(0.5 + delay)

    def expect(self, target='OK', command=None, fail=None, timeout=5):
        startTime  = time()
        buffer     = str()
        timePassed = 0

        if command is not None:
            self.send(command)

        while timePassed < timeout:
            size = self.device.in_waiting
            timePassed = time() - startTime
            
            if command and timePassed > 0.95*timeout:
                self.send(command)
            
            if size == 0:
                sleep(0.005)
                continue
            
            buffer += self.device.read(size).decode('utf-8', errors='ignore')

            if target in buffer:
                return True
            
            if fail and fail in buffer:
                return False

        return None
    
    def request(self, value, timeout=5.0):
        self.send(value)
        startTime = time()

        while time() - startTime < timeout:
            if self.available():
                continue

            return self.get()
        
        return None
    
    def stream(self, command='stream'):
        sendEvent('event', 'starting stream with device')
        
        if command:
            self.sendData('stream')
        
        self.device.reset_input_buffer()

        while self.available():
            continue
