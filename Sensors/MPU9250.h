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
    float mx, my, mz;

    MPU9250(int sda, int scl, TwoWire* bus): 
        SDA_PIN(sda), 
        SCL_PIN(scl), 
        wire(bus) {}

    void setup(){
        wire->begin(SDA_PIN, SCL_PIN);
        imu.setWire(wire);
        imu.beginAccel();
        imu.beginGyro();
        imu.beginMag(); // Importante para habilitar o magnetômetro
    }

    void update(){
        imu.accelUpdate();
        imu.gyroUpdate();
        imu.magUpdate(); // Atualiza valores do magnetômetro

        ax = imu.accelX();
        ay = imu.accelY();
        az = imu.accelZ();

        gx = imu.gyroX();
        gy = imu.gyroY();
        gz = imu.gyroZ();

        mx = imu.magX();
        my = imu.magY();
        mz = imu.magZ();
    }

    StaticJsonDocument<256> getData(){
        StaticJsonDocument<256> data;
        data["ax"] = ax; data["ay"] = ay; data["az"] = az;
        data["gx"] = gx; data["gy"] = gy; data["gz"] = gz;
        data["mx"] = mx; data["my"] = my; data["mz"] = mz;
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
