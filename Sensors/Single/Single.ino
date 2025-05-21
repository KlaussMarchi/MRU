#include <ArduinoJson.h>
#include "MPU9250.h"
#include "MPU6050.h"

TwoWire I2C_1 = TwoWire(0);
MPU9250 sensor(33, 32, &I2C_1);


void setup(){
    Serial.begin(115200);
    sensor.setup();

    while(!Serial.available())
        continue;
}

void loop(){
    static unsigned long startTime = millis();
    static unsigned long attTime   = millis();
    
    if(millis() - attTime < 5)
        return;

    attTime = millis();
    sensor.update();
    auto data = sensor.getData();
    data["time"] = (millis() - startTime)/1000.00;

    serializeJson(data, Serial);
    Serial.println();
}
