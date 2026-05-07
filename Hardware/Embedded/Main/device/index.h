#ifndef PROG_DEVICE_H
#define PROG_DEVICE_H
#include "../globals/functions.h"
#include "../globals/constants.h"

#include "../utils/array/index.h"
#include "../utils/time/index.h"
#include "../utils/json/index.h"
#include "../utils/text/index.h"
#include "../utils/listener/index.h"

#include "settings/index.h"
#include "tasks/index.h"

#include "../objects/telemetry/index.h"
#include "../objects/sensors/index.h"
#include "../objects/components/index.h"
#include "../objects/processing/index.h"


class Device{
  public:
    bool multitask = true;
    float frequency = 100.0;
    unsigned long startTime;
    const char* firmware;
    Settings settings;
    Text<12> id;

    Telemetry<Device> telemetry;
    Sensors<Device> sensors;
    Processing<Device> processing;
    Tasks<Device> tasks;
    Components<Device> components;

    Device(const char* version):
        firmware(version),
        telemetry(this),
        processing(this),
        sensors(this),
        tasks(this),
        components(this){}
    
    void setup(){
        snprintf(id.buffer, sizeof(id.buffer), "%04X%08X", (uint16_t)(ESP.getEfuseMac() >> 32), (uint32_t)ESP.getEfuseMac());

        Serial.println("Device Started: " + id.toString());
        Serial.println("Firmware: " + String(firmware));
        Serial.println();
        components.setup();
        
        startTime = Time::get();
        settings.import();
        
        telemetry.setup();
        sensors.setup();
        processing.setup();
    }

    void reset(){
        ESP.restart();
    }
};

#endif