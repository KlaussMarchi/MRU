#include <ArduinoJson.h>
#include "MPU6050.h"
#include "MPU9250.h"

TwoWire I2C_1 = TwoWire(0);
TwoWire I2C_2 = TwoWire(1);

MPU6050 sensor1(26, 25, &I2C_1);
MPU9250 sensor2(33, 32, &I2C_2);


void setup(){
    Serial.begin(115200);
    sensor1.setup();  
    sensor2.setup();

    while(!Serial.available())
        continue;
}

void loop(){
    static unsigned long startTime = millis();
    static unsigned long attTime   = millis();
    
    if(millis() - attTime < 5)
        return;

    attTime = millis();
    StaticJsonDocument<256> data;
    data["time"] = (millis() - startTime)/1000.00;

    sensor1.update();
    sensor2.update();
    data["sensor1"] = sensor1.getData();
    data["sensor2"] = sensor1.getData();
    serializeJson(data, Serial);
    Serial.println();
}
