#ifndef KERNEL_H
#define KERNEL_H
#include <HardwareSerial.h>


class KernelSensor{
  private:
    const uint8_t CMD_ORIENTATION[9] = {0xAA, 0x55, 0x00, 0x00, 0x07, 0x00, 0x33, 0x3A, 0x00};
    static const int PKT_LEN = 42;
    const float KG = 10.0;
    const float KA = 500.0;

    HardwareSerial* uart;
    const bool debug = false;
    
    unsigned long lastUpdate;
    uint8_t packet[PKT_LEN];
    bool header;
    int index;

    class Acceleration {
        public:
        float x, y, z;
        
        void update(float ax, float ay, float az) {
            x = ax;
            y = ay;
            z = az;
        }
    };

    class Omega{
      public:
        float x, y, z;
        
        void update(float wx, float wy, float wz) {
            x = wx;
            y = wy;
            z = wz;
        }
    };
    
  public:
    Acceleration a;
    Omega w;
    float temp;

    KernelSensor(int tx_pin, int rx_pin) {
        Serial.printf("Kernel Started at tx=%d and rx=%d\n", tx_pin, rx_pin);
        uart = new HardwareSerial(1);
        uart->begin(9600, SERIAL_8N1, rx_pin, tx_pin);
        header = false;
        index = 0;
        lastUpdate = millis();
    }

    void setup() {
        Serial.println("Activation CMD Sent");
        uart->write(CMD_ORIENTATION, 9);
        delay(200);
    }

    void reset() {
        header = false;
        index = 0;
    }

    bool available() {
        if(header && (millis() - lastUpdate > 100)){
            reset();
            return false;
        }

        while(uart->available()){
            uint8_t newByte = uart->read();
            lastUpdate = millis();

            if(!header){
                if (newByte == 0xAA){
                    packet[0] = 0xAA;
                    index = 1;
                } 
                else if (index == 1 && newByte == 0x55){
                    packet[1] = 0x55;
                    header = true;
                    index = 2;
                }

                continue;
            }

            if(index < PKT_LEN){
                packet[index] = newByte;
                index++;
            }

            if(index >= PKT_LEN) 
                return true;
        }

        return false;
    }

    bool update(){
        if(!available()) 
            return false;

        uint16_t calc_checksum = 0;
        for (int i = 2; i < 40; i++) 
            calc_checksum += packet[i];

        uint16_t recv_checksum = packet[40] | (packet[41] << 8);

        if(calc_checksum != recv_checksum){
            Serial.println("Checksum inválido!");
            reset();
            return false;
        }

        float heading = ((int16_t)(packet[7] | (packet[8] << 8))) / 100.0;
        float pitch = ((int16_t)(packet[9] | (packet[10] << 8)))  / 100.0;
        float roll = ((int16_t)(packet[11] | (packet[12] << 8)))  / 100.0;

        float wx = ((int16_t)(packet[13] | (packet[14] << 8))) / KG;
        float wy = ((int16_t)(packet[15] | (packet[16] << 8))) / KG;
        float wz = ((int16_t)(packet[17] | (packet[18] << 8))) / KG;

        float ax = ((int16_t)(packet[19] | (packet[20] << 8))) / KA;
        float ay = ((int16_t)(packet[21] | (packet[22] << 8))) / KA;
        float az = ((int16_t)(packet[23] | (packet[24] << 8))) / KA;
        temp = ((int16_t)(packet[33] | (packet[34] << 8))) / 10.0;

        a.update(ax, ay, az);
        w.update(wx, wy, wz);
        reset();
        return true;
    }
};

#endif