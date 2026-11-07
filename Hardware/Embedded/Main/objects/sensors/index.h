#ifndef SENSORS_H
#define SENSORS_H
#include "Kernel/index.h"
#include <Arduino.h>

template <typename Parent>
class Sensors {
private:
  Parent *device;

public:
    KernelSensor kernel = KernelSensor(4, 3);
    bool working = false;
    bool debug   = false;

    Sensors(Parent *dev) : device(dev) {}

    void setup() {
        if(debug)
            {working=true; return;}

        kernel.mode = device->settings.template get<byte>("kernel_mode");
        kernel.setup();

        if(!kernel.found)
            return device->health.log('E', "kernel nao respondeu em 460800/115200/230400/921600: alimentacao ou TX/RX");

        device->health.log('I', "kernel respondeu a %lu bps, align %.0f %.0f %.0f", (unsigned long) kernel.baud, kernel.alignment[0], kernel.alignment[1], kernel.alignment[2]);
    }

    void handle() {
        if(debug)
            return;

        kernel.handle();
        working = kernel.alive();
    }
};

#endif
