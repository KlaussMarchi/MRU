#include <ArduinoJson.h>
#include <Wire.h>

#define SENSOR_ADDR (0x68)
unsigned long startProg;

struct Sensor {
    float ax;
    float ay;
    float az;
    float tareX;
    float tareY;
    float tareZ;
    float scale;

    void setup() {
        Wire.begin();
        Wire.beginTransmission(SENSOR_ADDR);
        Wire.write(0x6B); 
        Wire.write(0); 
        Wire.endTransmission(true);

        this->tareX = 0.0;
        this->tareY = 0.0;
        this->tareZ = 0.0;
        this->scale = (9.81 / 16384.0) * 100.0; // Escala para cm/s²
    }

    void tare() {
        const unsigned long startTime = millis();
        int size   = 0;
        float sumX = 0.0;
        float sumY = 0.0;
        float sumZ = 0.0;

        while(millis() - startTime < 5000){
            this->update();
            sumX += this->ax;
            sumY += this->ay;
            sumZ += this->az;
            
            delay(10);
            size++;
        }

        this->tareX = sumX / size;
        this->tareY = sumY / size;
        this->tareZ = sumZ / size;
    }
    
    void warm() {
        Wire.beginTransmission(SENSOR_ADDR);
        Wire.write(0x3B);
        Wire.endTransmission(false);

        if(Wire.requestFrom(SENSOR_ADDR, 14, true) != 14)
            Serial.println("Erro na leitura do sensor");
    }

    void update() {
        this->warm();
        const float rawX = (Wire.read() << 8 | Wire.read()) * this->scale;
        const float rawY = (Wire.read() << 8 | Wire.read()) * this->scale;
        const float rawZ = (Wire.read() << 8 | Wire.read()) * this->scale;

        this->ax = (rawX - this->tareX);
        this->ay = (rawY - this->tareY);
        this->az = (rawZ - this->tareZ);
    }
};

Sensor sensor;

void setup() {
    Serial.begin(9600);
    sensor.setup();
    sensor.tare();

    while (!Serial.available())
        continue;

    startProg = millis();
}

void loop() {
    static unsigned long startTime;

    if(millis() - startTime < 100)
        return;
    
    startTime = millis();
    StaticJsonDocument<256> data;
    String response;

    sensor.update();
    data["t"]  = (millis() - startProg) / 1000.0;
    data["ax"] = sensor.ax; 
    data["ay"] = sensor.ay; 
    data["az"] = sensor.az; 

    serializeJson(data, response);
    Serial.println(response);
}
