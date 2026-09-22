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

        kernel.mode      = device->settings.template get<byte>("kernel_mode");
        kernel.calibrate = device->settings.isEnabled("calibrate");
        kernel.setup();
    }

    void handle() {
        if(debug)
            return;

        kernel.handle();
        working = kernel.working; 
    }
};

#endif
