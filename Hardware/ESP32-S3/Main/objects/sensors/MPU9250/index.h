#ifndef MPU9250_H
#define MPU9250_H
#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <MPU9250_asukiaaa.h>
#include "../../processing/filters/index.h"


class MPU9250{
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
    MPU9250_asukiaaa imu = MPU9250_asukiaaa(ADDRESS);
    const bool debug = true;
    const int SDA_PIN;
    const int SCL_PIN;
    Acceleration a;
    Omega w;

    MPU9250(int sda, int scl): 
        SDA_PIN(sda), 
        SCL_PIN(scl){}

    void setup(){
        if(!debug){
            Wire.begin(SDA_PIN, SCL_PIN);
            imu.setWire(&Wire);
            imu.beginAccel();
            imu.beginGyro();
        }

        Serial.println("MPU9250 Setup Complete");
    }
    
    void update(){
        if(debug){
            a.update(7, 7, 7);
            w.update(9, 9, 9);
            return;
        }

        imu.accelUpdate();
        imu.gyroUpdate();
        imu.magUpdate(); 

        const float ax = imu.accelX();
        const float ay = imu.accelY();
        const float az = imu.accelZ();
        const float wx = imu.gyroX();
        const float wy = imu.gyroY();
        const float wz = imu.gyroZ();
        a.update(ax, ay, az);
        w.update(wx, wy, wz);
    }
};

#endif
