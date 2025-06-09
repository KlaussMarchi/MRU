#ifndef MPU6050_H
#define MPU6050_H
#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include "processing.h"
    

struct MPU6050{
    ProcessingMPU6050 info;
    TwoWire* wire;
    static const uint8_t MPU_ADDR = (0x68);
    float ax, ay, az, wx, wy, wz, tp;
    int SDA_PIN, SCL_PIN;

    MPU6050(int sda, int scl, TwoWire* bus):
        SDA_PIN(sda), 
        SCL_PIN(scl),
        wire(bus){}

    void setup(){
        wire->begin(SDA_PIN, SCL_PIN);
        wire->beginTransmission(MPU_ADDR);
        wire->write(0x6B); 
        wire->write(0); 
        wire->endTransmission(true);
    }

    void update(){
        wire->beginTransmission(MPU_ADDR);
        wire->write(0x3B);              
        wire->endTransmission(false);

        if(wire->requestFrom((uint8_t)MPU_ADDR, (size_t)14, true) != 14)
            return;

        wx = (int16_t) (wire->read() << 8 | wire->read());
        wy = (int16_t) (wire->read() << 8 | wire->read());
        wz = (int16_t) (wire->read() << 8 | wire->read());
        tp = (int16_t) (wire->read() << 8 | wire->read());
        ax = (int16_t) (wire->read() << 8 | wire->read());
        ay = (int16_t) (wire->read() << 8 | wire->read());
        az = (int16_t) (wire->read() << 8 | wire->read());
        info.update(ax, ay, az, wx, wy, wz);
    }

    StaticJsonDocument<128>& getData(){
        static StaticJsonDocument<128> data;
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