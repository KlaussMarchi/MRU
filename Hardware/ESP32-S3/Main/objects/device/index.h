#ifndef DEVICE_H
#define DEVICE_H
#include <Arduino.h>
#include "../../globals/constants.h"
#include "../../globals/functions.h"
#include "../../utils/text/index.h"
#include "../../utils/time/index.h"
#include "../processing/index.h"
#include "../telemetry/index.h"
#include "../sensors/index.h"
#include "settings/index.h"

class Device{
  public:
    const bool debug = false;
    unsigned long startTime;
    Settings settings;
    Text<12> id;

    Processing<Device> processing;
    Telemetry<Device> telemetry;
    Sensors<Device> sensors;

    Device():
        processing(this),
        telemetry(this),
        sensors(this){}

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
#endif