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
    MPU9250 sensor2      = MPU9250(10, 12);

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
        //sensor2.update();
    }

    void print(unsigned long startTime){
        char buffer[512];

        snprintf(buffer, sizeof(buffer),
            "{\"time\": %f, \"ax\": %f, \"ay\": %f, \"az\": %f, \"wx\": %f, \"wy\": %f, \"wz\": %f}",
            (Time::get() - startTime)/1000.00,
            sensor1.a.x,
            sensor1.a.y, 
            sensor1.a.z, 
            sensor1.w.x, 
            sensor1.w.y, 
            sensor1.w.z
        );
        
        Serial.println(buffer);
    }
};

#endif