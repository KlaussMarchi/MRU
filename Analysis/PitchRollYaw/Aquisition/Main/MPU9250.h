#ifndef MPU9250_H
#define MPU9250_H
#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <MPU9250_asukiaaa.h>


struct MPU9250{
    const int SDA_PIN;
    const int SCL_PIN;
    TwoWire* wire;
    MPU9250_asukiaaa imu;
    float ax, ay, az, gx, gy, gz;

    MPU9250(int sda, int scl, TwoWire* bus): 
        SDA_PIN(sda), 
        SCL_PIN(scl), 
        wire(bus){}

    void setup(){
        wire->begin(SDA_PIN, SCL_PIN);
        imu.setWire(wire);
        imu.beginAccel();
        imu.beginGyro();
        imu.beginMag();
    }

    void update(){
        imu.accelUpdate();
        imu.gyroUpdate();
        ax = imu.accelX();
        ay = imu.accelY();
        az = imu.accelZ();
        gx = imu.gyroX();
        gy = imu.gyroY();
        gz = imu.gyroZ();
    }

    StaticJsonDocument<128> getData(){
        StaticJsonDocument<128> data;
        data["ax"] = ax; 
        data["ay"] = ay; 
        data["az"] = az;
        data["gx"] = gx; 
        data["gy"] = gy; 
        data["gz"] = gz;
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
