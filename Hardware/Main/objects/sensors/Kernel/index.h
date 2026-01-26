#ifndef KERNEL_H
#define KERNEL_H
#include <HardwareSerial.h>
#include "../../processing/filters/index.h"
#include "../../../utils/time/index.h"


class KernelSensor{
  private:
    const uint8_t CMD_ORIENTATION[9] = {0xAA, 0x55, 0x00, 0x00, 0x07, 0x00, 0x33, 0x3A, 0x00};
    static const int PKT_LEN = 42;
    unsigned long lastUpdate;
    uint8_t packet[PKT_LEN];
    HardwareSerial* uart;
    bool header = false;
    int index;
    
    static const bool apply_filters = false;
    static const bool apply_convert = false;

    class Acceleration{
      public:
        ButterworthFilter fx = ButterworthFilter(0.10);
        ButterworthFilter fy = ButterworthFilter(0.10);
        ButterworthFilter fz = ButterworthFilter(0.10);
        float x, y, z;
        
        void update(float ax, float ay, float az) {
            x = apply_convert ? (ax / 500.00) : ax;
            y = apply_convert ? (ay / 500.00) : ay;
            z = apply_convert ? (az / 500.00) : az;

            if(apply_filters){
                x = fx.compute(x);
                y = fy.compute(y);
                z = fz.compute(z);
            }
        }
    };

    class Omega{
      public:
        ButterworthFilter fx = ButterworthFilter(0.15);
        ButterworthFilter fy = ButterworthFilter(0.15);
        ButterworthFilter fz = ButterworthFilter(0.15);
        float x, y, z;
        
        void update(float wx, float wy, float wz) {
            x = apply_convert ? (wx / 10.00) : wx;
            y = apply_convert ? (wy / 10.00) : wy;
            z = apply_convert ? (wz / 10.00) : wz;

            if(apply_filters){
                x = fx.compute(x);
                y = fy.compute(y);
                z = fz.compute(z);
            }
        }
    };

    class Orientation{
      public:
        ButterworthFilter fx = ButterworthFilter(0.1);
        ButterworthFilter fy = ButterworthFilter(0.1);
        ButterworthFilter fz = ButterworthFilter(0.1);
        float pitch, roll, yaw;

        void update(float _yaw, float _pitch, float _roll){
            pitch = apply_convert ? (_pitch / 100.0) : _pitch;
            roll  = apply_convert ? (_roll  / 100.0) : _roll;
            yaw   = apply_convert ? (_yaw   / 100.0) : _yaw;

            if(apply_filters){
                pitch = fx.compute(pitch);
                roll  = fy.compute(roll);
                yaw   = fz.compute(yaw);
            }
        }
    };
    
  public:
    Acceleration a;
    Omega w;
    Orientation o;
    float temperature;
    int tx_pin, rx_pin;
    
    KernelSensor(int tx, int rx){
        uart = new HardwareSerial(1);
        tx_pin = tx;
        rx_pin = rx;
    }
    
    void setup(){
        uart->begin(115200, SERIAL_8N1, rx_pin, tx_pin);
        
        Serial.printf("Kernel Started at tx=%d and rx=%d\n", tx_pin, rx_pin);
        lastUpdate = Time::get();
        reset();

        Serial.println("Activation CMD Sent");
        uart->write(CMD_ORIENTATION, 9);
        delay(200);
    }

    int16_t extract(int pos){
        return (int16_t) (packet[pos] | (packet[pos+1] << 8));
    }

    uint16_t extract_u16(int pos){
        return (uint16_t) (packet[pos] | (packet[pos+1] << 8));
    }

    bool timeout(){
        return (header && Time::get() - lastUpdate > 100);
    }

    bool checksum(){
        uint16_t recv_checksum = extract_u16(40);
        uint16_t calc_checksum = 0;
        
        for(int i=2; i<40; i++) 
            calc_checksum += packet[i];

        if(calc_checksum == recv_checksum)
            return true;

        Serial.println("Checksum inválido!");
        return false;
    }

    void handle(){
        if(timeout())
            return reset();

        if(!uart->available())
            return;
        
        uint8_t newByte = uart->read();
        lastUpdate      = Time::get();

        if(!header && newByte == 0xAA){
            packet[0] = 0xAA;
            index = 1;
            return;
        }

        if(!header && newByte == 0x55 && index == 1){
            packet[1] = 0x55;
            header = true;
            index  = 2;
            return;
        }

        if(index < PKT_LEN)
            packet[index++] = newByte;

        if(index >= PKT_LEN)
            update();
    }

    bool update(){
        if(!checksum())
            {reset(); return false;}
        
        // orientação
        o.update(
            (float) extract_u16(6),  // yaw  (bytes 6..7)
            (float) extract(8),      // pitch(bytes 8..9)
            (float) extract(10)      // roll (bytes 10..11)
        );

        // giroscópio
        w.update(
            (float) extract(12),   // wx (bytes 12..13)
            (float) extract(14),   // wy (bytes 14..15)
            (float) extract(16)    // wz (bytes 16..17)
        );
        
        // aceleração
        a.update(
            (float) extract(18),   // ax (bytes 18..19)
            (float) extract(20),   // ay (bytes 20..21)
            (float) extract(22)    // az (bytes 22..23)
        );
        
        temperature = ((float) extract(38)) / 10.00;
        reset();
        return true;
    }

    void reset(){
        header = false;
        index  = 0;
    }
};

#endif