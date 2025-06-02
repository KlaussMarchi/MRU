#ifndef MPU6050_H
#define MPU6050_H
#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>


struct MPU6050{
    static const uint8_t MPU_ADDR = (0x68);
    static const byte size = 6;
    float ax, ay, az, gx, gy, gz, tp;
    int SDA_PIN, SCL_PIN;
    TwoWire* wire;

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

        gx = (int16_t) (wire->read() << 8 | wire->read());
        gy = (int16_t) (wire->read() << 8 | wire->read());
        gz = (int16_t) (wire->read() << 8 | wire->read());
        tp = (int16_t) (wire->read() << 8 | wire->read());
        ax = (int16_t) (wire->read() << 8 | wire->read());
        ay = (int16_t) (wire->read() << 8 | wire->read());
        az = (int16_t) (wire->read() << 8 | wire->read());
    }

    StaticJsonDocument<128>& getData(){
        static StaticJsonDocument<128> data;
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