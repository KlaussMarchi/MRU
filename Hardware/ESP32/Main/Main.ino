#include <ArduinoJson.h>
#include <BasicLinearAlgebra.h>
#include <Wire.h>
#include "global/constants.h"
#include "global/variables.h"
#include "global/functions.h"
#include "objects/serport/serport.h"
#include "objects/sensors/MPU6050/index.h"
#include "objects/sensors/MPU9250/index.h"

TwoWire I2C_1 = TwoWire(0);
TwoWire I2C_2 = TwoWire(1);

MPU6050 sensor1(21, 19, &I2C_2);
MPU9250 sensor2(5, 18,  &I2C_1);


void setup(){
    Serial.begin(115200);
    serport.setup(30);

    sensor1.setup();
    sensor2.setup();
    Serial.println("setup ready");
}

void loop(){
    serport.listen();
    sendLogsCheck();
    protocolCheck();
}
