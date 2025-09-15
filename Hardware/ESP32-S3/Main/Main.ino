#include "objects/device/index.h"
#include "objects/tasks/index.h"


void setup(){
    Serial.begin(115200);
    delay(1500);
    device.setup();
}

void loop(){
    tasks.handle();
}

