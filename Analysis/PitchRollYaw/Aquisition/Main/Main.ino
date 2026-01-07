#include <ArduinoJson.h>
#include "MPU6050.h"
#include "MPU9250.h"

TwoWire I2C_1 = TwoWire(0);
MPU9250 sensor(26, 25, &I2C_1);


void setup(){
    Serial.begin(115200);
    sensor.setup();  

    while(!Serial.available())
        continue;
}

void loop(){
    static unsigned long startTime = micros();
    sensor.update();
    
    auto data = sensor.getData();
    data["time"] = (micros() - startTime)/1e6;

    serializeJson(data, Serial);
    Serial.println();
}
