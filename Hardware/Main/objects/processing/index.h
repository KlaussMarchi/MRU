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
};

#endif