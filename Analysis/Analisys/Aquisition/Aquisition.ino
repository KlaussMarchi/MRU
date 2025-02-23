#include <ArduinoJson.h>
#include <Wire.h>

#define SENSOR_ADDR (0x68)
unsigned long startProg;

struct Sensor{
    float ax, ay, az, tp, wx, wy, wz;
    float tareAX, tareAY, tareAZ, aScale;

    void setup() {
        Wire.begin();
        Wire.beginTransmission(SENSOR_ADDR);
        Wire.write(0x6B); 
        Wire.write(0); 
        Wire.endTransmission(true);
        aScale = 9.81/32768.00;
    }

    void tare() {
        const unsigned long startTime = millis();
        float sumX = 0.0;
        float sumY = 0.0;
        float sumZ = 0.0;
        int size = 0;

        while(millis() - startTime < 5000){
            update();
            sumX += ax;
            sumY += ay;
            sumZ += az;
            
            delay(10);
            size++;
        }

        tareAX = sumX / size;
        tareAY = sumY / size;
        tareAZ = sumZ / size;
    }

    float getNext(){
        return (Wire.read() << 8 | Wire.read()); 
    }

    bool update() {
        Wire.beginTransmission(SENSOR_ADDR);
        Wire.write(0x3B);
        Wire.endTransmission(false);
        
        if(Wire.requestFrom(SENSOR_ADDR, 14, true) != 14)
            return false;
        
        wx = getNext();
        wy = getNext();
        wz = getNext();
        tp = getNext();
        ax = (getNext() - tareAX) * aScale;      
        ay = (getNext() - tareAY) * aScale;
        az = (getNext() - tareAZ) * aScale;
        return true;
    }
};

Sensor sensor;

void setup() {
    Serial.begin(9600);
    sensor.setup();
    //sensor.tare();

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
    data["wx"] = sensor.wx; 
    data["wy"] = sensor.wy; 
    data["wz"] = sensor.wz; 

    serializeJson(data, response);
    Serial.println(response);
}
