#include "globals/constants.h"
#include "globals/functions.h"
#include "utils/text/index.h"
#include "utils/time/index.h"
#include "objects/processing/index.h"
#include "objects/telemetry/index.h"
#include "objects/sensors/index.h"
#include "objects/settings/index.h"
#include "objects/tasks/index.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>


class Device{
  public:
    const bool debug = false;
    const bool serial_debug = false;
    unsigned long startTime;
    Settings settings;
    Text<12> id;

    Processing<Device> processing;
    Telemetry<Device> telemetry;
    Sensors<Device> sensors;
    Tasks<Device> tasks;

    Device():
        processing(this),
        telemetry(this),
        sensors(this),
        tasks(this){}

    void setup(){
        snprintf(id.buffer, sizeof(id.buffer), "%04X%08X", (uint16_t)(ESP.getEfuseMac() >> 32), (uint32_t)ESP.getEfuseMac());
        Serial.println("Device Started: " + id.toString());
        startTime = Time::get();
        settings.import();
        
        processing.setup();
        telemetry.setup();
        sensors.setup();
    }

    void reset(){
        ESP.restart();
    }
};

inline Device device;


void setup(){
    Serial.begin(115200);
    delay(1500);
    device.setup();
}

void loop(){
    device.tasks.handle();
}

