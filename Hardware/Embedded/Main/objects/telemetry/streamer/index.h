#ifndef STREAMER_H
#define STREAMER_H
#include <Arduino.h>
#include "../../sensors/index.h"


template <typename Parent> class Streamer{
  private:
    Listener handler = Listener(0);
    Parent* device;

  public:
    unsigned long startTime;
    bool active;
    int dt;

    Streamer(Parent* dev):
        device(dev){}

    void setup(){
        dt = (1.00/device->frequency)*1000;
        Serial.println("Frequency Set To " + String(device->frequency) + " Hz (sample time " + String(dt) + "ms)");
    }
    
    void handle(){
        static Listener timer = Listener(dt);

        if(!active || !timer.ready())
            return;

        print();
    }

    void set(const bool state){
        if(active == state)
            return;

        if(state)
            handler.reset();
        
        startTime = Time::get();
        active    = state;
    }

    void print(){
        static char buffer[256];
        int n;
        
        if(device->components.encoder.enabled)
            n = snprintf(buffer, sizeof(buffer),
                "{\"time\":%.3f,\"pitch\":%.3f,\"roll\":%.3f,\"yaw\":%.3f,"
                "\"ax\":%.3f,\"ay\":%.3f,\"az\":%.3f,"
                "\"wx\":%.3f,\"wy\":%.3f,\"wz\":%.3f,\"encoder\":%.3f}",
                (Time::get() - startTime) / 1000.00,
                device->sensors.kernel.o.pitch,
                device->sensors.kernel.o.roll,
                device->sensors.kernel.o.yaw,
                device->sensors.kernel.a.x,
                device->sensors.kernel.a.y,
                device->sensors.kernel.a.z,
                device->sensors.kernel.w.x,
                device->sensors.kernel.w.y,
                device->sensors.kernel.w.z,
                device->components.encoder.angle
            );
        else
            n = snprintf(buffer, sizeof(buffer),
                "{\"time\":%.3f,\"pitch\":%.3f,\"roll\":%.3f,\"yaw\":%.3f,"
                "\"ax\":%.3f,\"ay\":%.3f,\"az\":%.3f,"
                "\"wx\":%.3f,\"wy\":%.3f,\"wz\":%.3f}",
                (Time::get() - startTime) / 1000.00,
                device->sensors.kernel.o.pitch,
                device->sensors.kernel.o.roll,
                device->sensors.kernel.o.yaw,
                device->sensors.kernel.a.x,
                device->sensors.kernel.a.y,
                device->sensors.kernel.a.z,
                device->sensors.kernel.w.x,
                device->sensors.kernel.w.y,
                device->sensors.kernel.w.z
            );
        
        Serial.write(buffer, n);
        Serial.write('\n');
    }

    void print2(){
        static char sentence[79 + 1]; // parte entre $ e * (sem checksum)
        static char nmea[82 + 1];     // sentença completa com $...*XX\r\n
        
        const char* header = "GPPASHR";
        const int wx = device->sensors.kernel.w.x;
        const int wy = device->sensors.kernel.w.y;
        const int wz = device->sensors.kernel.w.z;
        const int ax = device->sensors.kernel.a.x;
        const int ay = device->sensors.kernel.a.y;
        const int az = device->sensors.kernel.a.z;
        
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
