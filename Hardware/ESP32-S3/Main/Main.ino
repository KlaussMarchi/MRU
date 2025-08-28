#include "objects/device/index.h"
#include "objects/telemetry/index.h"


void setup(){
    Serial.begin(115200);
    device.setup();
    telemetry.setup();
}

void loop(){
    telemetry.handle();
}

