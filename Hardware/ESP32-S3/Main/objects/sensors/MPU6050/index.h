#ifndef MPU6050_H
#define MPU6050_H
#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>


class MPU6050{
  private:
    class Omega{
      public:
        const float confidence = 0.1;
        float x, y, z;
        float fx, fy, fz;

        void update(float wx, float wy, float wz){
            x = 10;
            y = 20;
            z = 30;
        }
    };

    class Acceleration{
      public:
        const float confidence = 0.1;
        float x, y, z;
        float fx, fy, fz;

        void update(float ax, float ay, float az){
            x = 10;
            y = 20;
            z = 30;
        }
    };

  public:
    static const uint8_t MPU_ADDR = (0x68);
    int SDA_PIN, SCL_PIN;
    Acceleration a;
    Omega w;

    MPU6050(int sda, int scl):
        SDA_PIN(sda), 
        SCL_PIN(scl){}

    void setup(){
        Wire.begin(SDA_PIN, SCL_PIN);
        Wire.beginTransmission(MPU_ADDR);
        Wire.write(0x6B); 
        Wire.write(0); 
        Wire.endTransmission(true);
    }

    void update(){
        Wire.beginTransmission(MPU_ADDR);
        Wire.write(0x3B);              
        Wire.endTransmission(false);

        if(Wire.requestFrom((uint8_t)MPU_ADDR, (size_t)14, true) != 14)
            return;

        float wx = (int16_t) (Wire.read() << 8 | Wire.read());
        float wy = (int16_t) (Wire.read() << 8 | Wire.read());
        float wz = (int16_t) (Wire.read() << 8 | Wire.read());
        float tp = (int16_t) (Wire.read() << 8 | Wire.read());
        float ax = (int16_t) (Wire.read() << 8 | Wire.read());
        float ay = (int16_t) (Wire.read() << 8 | Wire.read());
        float az = (int16_t) (Wire.read() << 8 | Wire.read());
        a.update(ax, ay, az);
        w.update(wx, wy, wz);
    }

    Json<64> get(){
        Json<64> data;
        data.set("ax", a.x);
        data.set("ay", a.y);
        data.set("az", a.z);
        data.set("wx", w.x);
        data.set("wy", w.y);
        data.set("wz", w.z);
        return data;
    }
};

#endif