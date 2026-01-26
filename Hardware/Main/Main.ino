#include "device/index.h"
Device device{"v1.0.0"};


void setup(){
    device.telemetry.protobuf.enabled = false;
    device.leds.enabled = false;
    device.multitask = true;
    device.sensors.debug = true;

    Serial.begin(115200);
    delay(1500);
    device.setup();
}

void loop(){
    device.tasks.handle();
}
