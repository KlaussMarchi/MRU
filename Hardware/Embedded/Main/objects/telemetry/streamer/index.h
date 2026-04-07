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
    bool active, autostart;
    int dt;
    
    Streamer(Parent* dev):
        device(dev){}

    void setup(){
        dt = (1.00/device->frequency)*1000;
        Serial.println("Frequency Set To " + String(device->frequency) + " Hz (sample time " + String(dt) + "ms)");

        if(autostart)
            active = true;
    }
    
    void handle(){
        static Listener timer = Listener(dt);

        if(!active || !timer.ready())
            return;

        device->sensors.kernel.print();
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
        int n = snprintf(buffer, sizeof(buffer),
            "{\"time\":%.3f,\"pitch\":%ld,\"roll\":%ld,\"yaw\":%ld,"
            "\"ax\":%ld,\"ay\":%ld,\"az\":%ld,"
            "\"wx\":%ld,\"wy\":%ld,\"wz\":%ld,\"e\":%.4f}",
            (Time::get() - startTime) / 1000.00,
            (long) device->sensors.kernel.pitch,
            (long) device->sensors.kernel.roll,
            (long) device->sensors.kernel.yaw,
            (long) device->sensors.kernel.ax,
            (long) device->sensors.kernel.ay,
            (long) device->sensors.kernel.az,
            (long) device->sensors.kernel.wx,
            (long) device->sensors.kernel.wy,
            (long) device->sensors.kernel.wz
        );
        
        device->telemetry.serial.uart->write(buffer, n);
        device->telemetry.serial.uart->write('\n');
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
        device->telemetry.serial.uart->print(nmea);
    }
};

#endif
