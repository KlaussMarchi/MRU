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

        print();
    }

    void set(const bool state){
        if(active == state)
            return;

        if(state)
            handler.reset();
        
        active = state;
    }

    void print(){
        static unsigned long startTime = Time::get();
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
        
        Serial.println(buffer);
    }

    void print2(){
        static char sentence[79 + 1]; // parte entre $ e * (sem checksum)
        static char nmea[82 + 1];     // sentença completa com $...*XX\r\n
        
        const char* header = "GPPASHR";
        const int wx = device->sensors.sensor1.w.x;
        const int wy = device->sensors.sensor1.w.y;
        const int wz = device->sensors.sensor1.w.z;
        const int ax = device->sensors.sensor1.a.x;
        const int ay = device->sensors.sensor1.a.y;
        const int az = device->sensors.sensor1.a.z;

        snprintf(
            sentence, sizeof(sentence),
            "%s,%d,%d,%d,%d,%d,%d",
            header, wx, wy, wz, ax, ay, az
        );

        unsigned char checksum = 0;
        for (int i=0; i<strlen(sentence); i++) 
            checksum ^= (unsigned char) sentence[i];
        
        snprintf(nmea, sizeof(nmea), "$%s*%02X\r\n", sentence, checksum);
        Serial.print(nmea);
    }
};

#endif
