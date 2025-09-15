#ifndef STREAMER_H
#define STREAMER_H
#include <Arduino.h>
#include "../../sensors/index.h"


template <typename Parent> class Streamer{
  private:
    Listener handler = Listener(0);
    Parent* device;

  public:
    int frequency;
    bool active;

    Streamer(Parent* dev):
        device(dev){}

    void setup(){
        frequency = 100;
        handler.timeout = (1.00/frequency)*1000;
        Serial.println("Frequency Set To " + String(frequency) + "Hz (sample time " + String(handler.timeout) + "ms)");
    }
    
    void handle(){
        static Listener timer = Listener(handler.timeout);

        if(!active || !timer.ready())
            return;

        if(device->debug)
            return device->sensors.print(handler.startTime);

        device->processing.print(handler.startTime);
    }

    void set(const bool state){
        if(active == state)
            return;

        if(state)
            handler.reset();
        
        active = state;
    }
};

#endif