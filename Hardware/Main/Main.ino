#include <ArduinoJson.h>
#include <Wire.h>
#include "global/constants.h"
#include "global/variables.h"
#include "global/functions.h"
#include "objects/espserver/espserver.h"
#include "objects/sensors/MPU6050.h"
#include "objects/sensors/MPU9250.h"
#include "objects/serport/serport.h"

TwoWire I2C_1 = TwoWire(0);
MPU9250 sensor1(26, 25, &I2C_1);

TwoWire I2C_2 = TwoWire(1);
MPU6050 sensor2(33, 32, &I2C_2);


void setup(){
    Serial.begin(115200);
    serport.setup(30);
    espserver.connect("Klauss", "Marchi12345@");

    sensor1.setup();
    sensor2.setup();
    Serial.println("setup ready");
}

void loop(){
    serport.listen();
    espserver.listen();
    sendLogsCheck();
    protocolCheck();
    handleRoutes();
}
