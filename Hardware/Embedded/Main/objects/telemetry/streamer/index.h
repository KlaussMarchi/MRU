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
    byte protocol = LIST_PROTOCOL;
    int dt;
    
    Streamer(Parent* dev):
        device(dev){}

    void setup(){
        dt = (1.00/device->frequency)*1000;
        Serial.println("Frequency Set To " + String(device->frequency) + " Hz (sample time " + String(dt) + "ms)");

        if(autostart)
            active = true;

        protocol = (byte) device->settings.template get<byte>("protocol");
    }
    
    void handle(){
        static Listener timer = Listener(dt);

        if(!active || !timer.ready())
            return;

        switch(protocol){
            case JSON_PROTOCOL: printJSON(); break;
            case LIST_PROTOCOL: printList(); break;
            case NMEA_PROTOCOL: printNMEA(); break;
        }
    }

    void set(const bool state){
        if(active == state)
            return;

        if(state)
            handler.reset();
        
        startTime = Time::get();
        active    = state;
    }

    void printJSON(){
        static char buffer[256];
        const byte mode = device->sensors.kernel.mode;
        int n;

        if(mode == HR_MODE || mode == OR_MODE)
            n = snprintf(buffer, sizeof(buffer),
                "{\"time\":%.3f,\"tmp\":%.2f,\"pitch\":%ld,\"roll\":%ld,\"yaw\":%ld,"
                "\"ax\":%ld,\"ay\":%ld,\"az\":%ld,"
                "\"wx\":%ld,\"wy\":%ld,\"wz\":%ld}",
                (Time::get() - startTime) / 1000.00,
                device->sensors.kernel.temperature,
                (long) device->sensors.kernel.pitch, (long) device->sensors.kernel.roll, (long) device->sensors.kernel.yaw,
                (long) device->sensors.kernel.ax,    (long) device->sensors.kernel.ay,   (long) device->sensors.kernel.az,
                (long) device->sensors.kernel.wx,    (long) device->sensors.kernel.wy,   (long) device->sensors.kernel.wz
            );
        else
            n = snprintf(buffer, sizeof(buffer),
                "{\"time\":%.3f,\"tmp\":%.2f,\"pitch\":%ld,\"roll\":%ld,\"yaw\":%ld,\"q0\":%ld,\"q1\":%ld,\"q2\":%ld,\"q3\":%ld}",
                (Time::get() - startTime) / 1000.00,
                device->sensors.kernel.temperature,
                (long) device->sensors.kernel.pitch, (long) device->sensors.kernel.roll, (long) device->sensors.kernel.yaw,
                (long) device->sensors.kernel.q0,    (long) device->sensors.kernel.q1,   (long) device->sensors.kernel.q2, (long) device->sensors.kernel.q3
            );

        device->telemetry.serial.uart->write(buffer, n);
        device->telemetry.serial.uart->write('\n');
    }

    void printList(){
        static char buffer[256];
        const byte mode = device->sensors.kernel.mode;
        int n;

        if(mode == HR_MODE || mode == OR_MODE)
            n = snprintf(buffer, sizeof(buffer),
                "[%.2f,%ld,%ld,%ld,%ld,%ld,%ld,%ld,%ld,%ld]",
                device->sensors.kernel.temperature,
                (long) device->sensors.kernel.pitch, (long) device->sensors.kernel.roll, (long) device->sensors.kernel.yaw,
                (long) device->sensors.kernel.ax,    (long) device->sensors.kernel.ay,   (long) device->sensors.kernel.az,
                (long) device->sensors.kernel.wx,    (long) device->sensors.kernel.wy,   (long) device->sensors.kernel.wz
            );
        else
            n = snprintf(buffer, sizeof(buffer),
                "[%.2f,%ld,%ld,%ld,%ld,%ld,%ld,%ld]",
                device->sensors.kernel.temperature,
                (long) device->sensors.kernel.pitch, (long) device->sensors.kernel.roll, (long) device->sensors.kernel.yaw,
                (long) device->sensors.kernel.q0,    (long) device->sensors.kernel.q1,   (long) device->sensors.kernel.q2, (long) device->sensors.kernel.q3
            );

        device->telemetry.serial.uart->write(buffer, n);
        device->telemetry.serial.uart->write('\n');
    }

    void printNMEA(){
        static char sentence[79 + 1]; // parte entre $ e * (sem checksum)
        static char nmea[82 + 1];     // sentença completa com $...*XX\r\n
        const char* header = "GPPASHR";
        
        snprintf(
            sentence, sizeof(sentence),
            "%s,%ld,%ld,%ld",
            header, 
            device->processing.pitch.get(device->sensors.kernel.pitch),
            device->processing.roll.get(device->sensors.kernel.roll), 
            device->processing.yaw.get(device->sensors.kernel.yaw)
        );

        unsigned char checksum = 0;
        for (int i=0; i<strlen(sentence); i++) 
            checksum ^= (unsigned char) sentence[i];
        
        snprintf(nmea, sizeof(nmea), "$%s*%02X\r\n", sentence, checksum);
        device->telemetry.serial.uart->print(nmea);
    }
};

#endif
