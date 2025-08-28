#ifndef MPU9250_H
#define MPU9250_H
#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <MPU9250_asukiaaa.h>


class MPU9250{
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
    MPU9250_asukiaaa imu;
    const int SDA_PIN;
    const int SCL_PIN;
    Acceleration a;
    Omega w;

    MPU9250(int sda, int scl): 
        SDA_PIN(sda), 
        SCL_PIN(scl){}

    void setup(){
        Wire.begin(SDA_PIN, SCL_PIN);
        imu.beginAccel();
        imu.beginGyro();
    }
    
    void update(){
        imu.accelUpdate();
        imu.gyroUpdate();
        imu.magUpdate(); 

        float ax = imu.accelX();
        float ay = imu.accelY();
        float az = imu.accelZ();
        float wx = imu.gyroX();
        float wy = imu.gyroY();
        float wz = imu.gyroZ();
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
