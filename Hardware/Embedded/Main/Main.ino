#include "device/index.h"
Device device{"v1.0.0"};


void setup(){
    device.frequency = 10;
    device.components.encoder.enabled   = true;
    device.telemetry.streamer.autostart = false;
    device.telemetry.streamer.use_protocol = false;
    device.telemetry.protobuf.enabled = true;
    device.components.leds.enabled = true;
    device.multitask     = false;
    device.sensors.debug = false;
    
    Serial.begin(115200);
    delay(1500);

    Serial.println("Serial Setup Complete... Starting Program");
    device.setup();
}

void loop(){
    device.tasks.handle();
}
