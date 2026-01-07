#ifndef MPU6050_H
#define MPU6050_H
#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include "../../processing/filters/index.h"


class MPU6050{
  private:
    class Omega{
      public:
        const float confidence = 0.1;
        ButterworthFilter fx = ButterworthFilter(0.5);
        ButterworthFilter fy = ButterworthFilter(0.5);
        ButterworthFilter fz = ButterworthFilter(0.5);
        float x, y, z;

        void update(float wx, float wy, float wz){
            x = fx.compute(wx);
            y = fy.compute(wy);
            z = fz.compute(wz);
        }
    };

    class Acceleration{
      public:
        const float confidence = 0.1;
        ButterworthFilter fx = ButterworthFilter(0.5);
        ButterworthFilter fy = ButterworthFilter(0.5);
        ButterworthFilter fz = ButterworthFilter(0.5);
        float x, y, z;

        void update(float ax, float ay, float az){
            x = fx.compute(ax);
            y = fy.compute(ay);
            z = fz.compute(az);
        }
    };

  public:
    static const uint8_t ADDRESS = (0x68);
    const bool debug = true;
    int SDA_PIN, SCL_PIN;
    Acceleration a;
    Omega w;

    MPU6050(int sda, int scl):
        SDA_PIN(sda), 
        SCL_PIN(scl){}

    void setup(){
        if(!debug){
            Wire.begin(SDA_PIN, SCL_PIN);
            Wire.beginTransmission(ADDRESS);
            Wire.write(0x6B); 
            Wire.write(0); 
            Wire.endTransmission(true);
        }

        Serial.println("MPU6050 Setup Complete");
    }

    void update(){
        if(debug){
            a.update(2, 2, 2);
            w.update(5, 5, 5);
            return;
        }

        Wire.beginTransmission(ADDRESS);
        Wire.write(0x3B);              
        Wire.endTransmission(false);

        if(Wire.requestFrom((uint8_t)ADDRESS, (size_t)14, true) != 14)
            return;

        const float wx = (int16_t) (Wire.read() << 8 | Wire.read());
        const float wy = (int16_t) (Wire.read() << 8 | Wire.read());
        const float wz = (int16_t) (Wire.read() << 8 | Wire.read());
        const float tp = (int16_t) (Wire.read() << 8 | Wire.read());
        const float ax = (int16_t) (Wire.read() << 8 | Wire.read());
        const float ay = (int16_t) (Wire.read() << 8 | Wire.read());
        const float az = (int16_t) (Wire.read() << 8 | Wire.read());
        a.update(ax, ay, az);
        w.update(wx, wy, wz);
    }
};

#endif