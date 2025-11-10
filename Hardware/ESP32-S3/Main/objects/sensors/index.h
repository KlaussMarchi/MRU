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
    KernelSensor sensor1 = KernelSensor(47, 48);
    //MPU9250 sensor2    = MPU9250(10, 12);

    Sensors(Parent* dev):
        device(dev){}

    void setup(){
        sensor1.setup();
        //sensor2.setup();
    }

    void handle(){
        static Listener timer = Listener(10);

        if(!timer.ready())
            return;

        sensor1.update();
    }
};

#endif