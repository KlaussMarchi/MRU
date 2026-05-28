#ifndef SENSORS_H
#define SENSORS_H
#include <Arduino.h>
#include "Kernel/index.h"


template <typename Parent> class Sensors{
  private:
    Parent* device;
    
  public:
    KernelSensor kernel = KernelSensor(4, 3);
    bool working = false;
    bool debug   = false;

    Sensors(Parent* dev):
        device(dev){}

    void setup(){
        if(debug)
            return;

        kernel.mode = device->settings.template get<byte>("kernel_mode");
        kernel.setup();
    }

    void handle(){
        if(debug)
            return;

        kernel.handle();
        check();
    }

    void check(){
        working = kernel.working;
    }
};

#endif