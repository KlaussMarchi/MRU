import time
import json
import smbus  # Biblioteca para comunicação I2C
from Sensor.index import *
from Serial.index import *

# Endereço I2C do MPU6050
SENSOR_ADDR = 0x68

class Sensor:
    def __init__(self, bus, address):
        self.bus = bus
        self.address = address
        
        # Acelerações lidas (em cm/s^2)
        self.ax = 0.0
        self.ay = 0.0
        self.az = 0.0
        
        # Valores de "tare" (offset)
        self.tareX = 0.0
        self.tareY = 0.0
        self.tareZ = 0.0
        
        # Fator de escala (conversão do valor cru para cm/s^2)
        # Se o sensor estiver configurado no range +/- 2g: 16384 LSB/g
        # 1g = 9.81 m/s^2 → 981 cm/s^2
        # => (981 cm/s^2 / 16384) = ~0.0598 cm/s^2 por LSB
        # Multiplicando por 100 apenas se for de interesse; 
        # mas aqui segue a mesma lógica do seu código:
        self.scale = (9.81 / 16384.0) * 100.0

    def setup(self):
        """
        Inicializa o sensor (acorda o MPU6050).
        Registrador 0x6B controla o 'power management', 
        escrevendo 0x00 'acorda' o sensor.
        """
        self.bus.write_byte_data(self.address, 0x6B, 0x00)
        time.sleep(0.1)  # pequena pausa para estabilizar

    def read_raw_data(self):
        """
        Lê os 6 bytes de acelerômetro a partir do registrador 0x3B.
        Retorna (ax_raw, ay_raw, az_raw), valores brutos (signed 16 bits).
        """
        # Lê 6 bytes a partir do registrador 0x3B
        data = self.bus.read_i2c_block_data(self.address, 0x3B, 6)

        # data é um array de 6 bytes: [AxH, AxL, AyH, AyL, AzH, AzL]
        raw_x = (data[0] << 8) | data[1]
        raw_y = (data[2] << 8) | data[3]
        raw_z = (data[4] << 8) | data[5]

        # Converter para inteiro de 16 bits com sinal
        if raw_x > 32767: 
            raw_x -= 65536
        if raw_y > 32767: 
            raw_y -= 65536
        if raw_z > 32767: 
            raw_z -= 65536

        return raw_x, raw_y, raw_z

    def tare(self, duration=5):
        """
        Faz a calibração/tara do sensor por um período (em segundos).
        Captura várias leituras e calcula a média, que será subtraída como offset.
        """
        print("Iniciando tara ({} segundos)...".format(duration))
        start_time = time.time()
        
        sum_x = 0.0
        sum_y = 0.0
        sum_z = 0.0
        count = 0
        
        while time.time() - start_time < duration:
            raw_x, raw_y, raw_z = self.read_raw_data()
            
            # Converter usando a escala
            gx = raw_x * self.scale
            gy = raw_y * self.scale
            gz = raw_z * self.scale

            sum_x += gx
            sum_y += gy
            sum_z += gz
            
            count += 1
            time.sleep(0.01)  # Ajuste conforme desejar

        self.tareX = sum_x / count
        self.tareY = sum_y / count
        self.tareZ = sum_z / count
        
        print("Tara concluída!")
        print("tareX = {:.2f}, tareY = {:.2f}, tareZ = {:.2f}"
              .format(self.tareX, self.tareY, self.tareZ))

    def update(self):
        """
        Lê os valores brutos do acelerômetro, converte em cm/s^2,
        subtrai o offset (tare) e armazena em ax, ay, az.
        """
        raw_x, raw_y, raw_z = self.read_raw_data()
        gx = raw_x * self.scale
        gy = raw_y * self.scale
        gz = raw_z * self.scale
        
        # Subtrai offset
        self.ax = gx - self.tareX
        self.ay = gy - self.tareY
        self.az = gz - self.tareZ

def main():
    # Abre o barramento I2C: no Raspberry Pi (modelo recente) geralmente é "1"
    bus = smbus.SMBus(1)
    
    sensor = Sensor(bus, SENSOR_ADDR)
    sensor.setup()
    
    # Fazer tara por 5 segundos (ou o tempo que quiser)
    sensor.tare(duration=5)
    
    start_prog = time.time()
    
    # Loop infinito (Ctrl+C para sair)
    while True:
        sensor.update()
        
        # Monta o JSON
        data = {
            "t": time.time() - start_prog,  # tempo em segundos desde o início
            "ax": sensor.ax,
            "ay": sensor.ay,
            "az": sensor.az
        }

        # Imprime em formato JSON
        print(json.dumps(data))
        
        # Taxa de atualização ~10 Hz (ajuste conforme necessidade)
        time.sleep(0.1)

if __name__ == "__main__":
    main()
