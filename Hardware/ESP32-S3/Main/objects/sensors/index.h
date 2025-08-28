#ifndef SENSORS_H
#define SENSORS_H
#include <Arduino.h>
#include "MPU6050/index.h"
#include "MPU9250/index.h"
#include "../../utils/listener/index.h"
#include "../../utils/json/index.h"
#include "../device/index.h"


class Sensors{
  public:
    MPU6050 sensor1 = MPU6050(10, 12);
    MPU9250 sensor2 = MPU9250(10, 12);
    
    void setup(){
        sensor1.setup();
        sensor2.setup();
    }

    void handle(){
        static Listener listener = Listener(20);

        if(!listener.ready())
            return;

        sensor1.update();
        sensor2.update();
    }

    Json<512> get(){
        static unsigned long startTime = device.time();

        Json<512> data;
        data.set("time", (device.time() - startTime)/1000.00);
        data.set("s1", sensor1.get().toString());
        data.set("s2", sensor2.get().toString());
        return data;
    }
};


inline Sensors sensors;
#endif