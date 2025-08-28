#include "objects/device/index.h"
#include "objects/telemetry/index.h"
#include "objects/sensors/index.h"


void setup(){
    Serial.begin(115200);
    device.setup();
    telemetry.setup();
    sensors.setup();
}

void loop(){
    telemetry.handle();
    sensors.handle();

    auto raw = sensors.get();
    raw.print();
}

