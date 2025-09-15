#ifndef PROCESSING_H
#define PROCESSING_H
#include <Arduino.h>
#include "../../utils/time/index.h"
#include "filters/index.h"


template <typename Parent> class Processing{
  private:
    Parent* device;

    class Omega{
      public:
        const float confidence = 0.1;
        float x, y, z;

        void update(float wx, float wy, float wz){
            x = wx;
            y = wy;
            z = wz;
        }
    };

    class Acceleration{
      public:
        const float confidence = 0.1;
        float x, y, z;

        void update(float ax, float ay, float az){
            x = ax;
            y = ay;
            z = az;
        }
    };
   
  public:
    Acceleration a;
    Omega w;

    Processing(Parent* dev):
        device(dev){}

    void setup(){

    }

    void print(unsigned long startTime){
        char buffer[512];

        snprintf(buffer, sizeof(buffer),
            "{\"time\": %f, \"ax\": %f, \"ay\": %f, \"az\": %f, \"wx\": %f, \"wy\": %f, \"wz\": %f}",
            (Time::get() - startTime)/1000.00,
            device->sensors.sensor1.a.x,
            device->sensors.sensor1.a.y, 
            device->sensors.sensor1.a.z, 
            device->sensors.sensor1.w.x, 
            device->sensors.sensor1.w.y, 
            device->sensors.sensor1.w.z
        );
        
        Serial.println(buffer); // Actually output the data
    }
};

#endif