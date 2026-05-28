#include "device/index.h"
Device device{"v1.0.2"};


void setup(){
    device.components.encoder.enabled = true;
    device.components.leds.enabled = true;
    device.multitask     = true;
    device.sensors.debug = false;
    
    Serial.begin(115200);
    delay(1500);

    Serial.println("Serial Setup Complete... Starting Program");
    device.setup();
}

void loop(){
    device.tasks.handle();
}
