#ifndef SENSORS_H
#define SENSORS_H
#include <Arduino.h>
#include "MPU6050/index.h"
#include "MPU9250/index.h"
#include "Kernel/index.h"
#include "../../utils/listener/index.h"
#include "../../utils/json/index.h"
#include "../../utils/time/index.h"


template <typename Parent> class Sensors{
  private:
    Parent* device;
    
  public:
    KernelSensor kernel = KernelSensor(4, 3);
    //MPU9250 sensor2   = MPU9250(10, 12);

    Sensors(Parent* dev):
        device(dev){}

    void setup(){
        kernel.setup();
    }

    void handle(){
        kernel.handle();
    }
};

#endif