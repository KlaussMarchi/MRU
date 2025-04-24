#include <ArduinoJson.h>
#include "MPU6050.h"
#include "MPU9250.h"

TwoWire I2C_1 = TwoWire(0);
TwoWire I2C_2 = TwoWire(1);

MPU6050 sensor1(26, 25, &I2C_1);
MPU9250 sensor2(33, 32, &I2C_2);


void setup() {
    Serial.begin(115200);
    sensor1.setup();  
    sensor2.setup();

    while(!Serial.available())
        continue;
}

void loop(){
    static unsigned long startTime = micros();
    StaticJsonDocument<256> data;
    sensor1.update();
    sensor2.update();

    data["time"] = (micros() - startTime)/1e6;
    data["MRU1"] = sensor1.getData();
    data["MRU2"] = sensor2.getData();

    serializeJson(data, Serial);
    Serial.println();
}
