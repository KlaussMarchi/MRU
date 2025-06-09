#ifndef MPU9250_H
#define MPU9250_H
#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <MPU9250_asukiaaa.h>
#include "processing.h"


struct MPU9250{
    ProcessingMPU9250 info;
    TwoWire* wire;
    MPU9250_asukiaaa imu;
    const int SDA_PIN;
    const int SCL_PIN;
    float ax, ay, az;
    float vx, vy, vz;
    float wx, wy, wz;
    float roll, pitch, yaw;

    MPU9250(int sda, int scl, TwoWire* bus): 
        SDA_PIN(sda), 
        SCL_PIN(scl), 
        wire(bus){}

    void setup(){
        wire->begin(SDA_PIN, SCL_PIN);
        imu.setWire(wire);
        imu.beginAccel();
        imu.beginGyro();
    }
    
    void update(){
        imu.accelUpdate();
        imu.gyroUpdate();
        imu.magUpdate(); 

        ax = imu.accelX();
        ay = imu.accelY();
        az = imu.accelZ();

        wx = imu.gyroX();
        wy = imu.gyroY();
        wz = imu.gyroZ();
        info.update(ax, ay, az, wx, wy, wz);
    }

    StaticJsonDocument<256>& getData(){
        static StaticJsonDocument<256> data;
        data["ax"] = ax; 
        data["ay"] = ay; 
        data["az"] = az;
        data["wx"] = wx; 
        data["wy"] = wy; 
        data["wz"] = wz;
        return data;
    }

    void plot(const char* variable, const int lower, const int upper){
        update();
        auto data = getData();
        const int value = data[variable].as<const int>();
        Serial.print(value);
        Serial.print(",");
        Serial.print(lower);
        Serial.print(",");
        Serial.println(upper);
    }
};

#endif
