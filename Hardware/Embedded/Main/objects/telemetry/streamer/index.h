#ifndef STREAMER_H
#define STREAMER_H
#include <Arduino.h>
#include "../../sensors/index.h"

template <typename Parent> class Streamer {
private:
    Parent* device;

public:
    unsigned long startTime;
    bool active, autostart;
    byte protocol = LIST_PROTOCOL;
    int dt;

    Streamer(Parent* dev): 
        device(dev){}

    void setup() {
        dt = (1.00 / device->frequency) * 1000;
        Serial.println("Frequency Set To " + String(device->frequency) + " Hz (sample time " + String(dt) + "ms)");

        if (autostart)
            active = true;

        protocol  = (byte) device->settings.template get<byte>("protocol");
        autostart = device->settings.isEnabled("autostream");
    }

    void handle() {
        static Listener timer = Listener(dt);

        if (!active || !timer.ready())
            return;

        switch (protocol) {
            case JSON_PROTOCOL: printJSON(); break;
            case LIST_PROTOCOL: printList(); break;
            case NMEA_PROTOCOL: printNMEA(); break;
        }
    }

    void set(const bool state) {
        if(active == state)
            return;

        startTime = Time::get();
        active    = state;
    }

    void printJSON() {
        static char buffer[256];
        const byte mode = device->sensors.kernel.mode;
        int n;

        if(mode == HR_MODE) {
            n = snprintf(buffer, sizeof(buffer),
                "{\"time\":%.3f,\"tmp\":%.3f,\"pitch\":%ld,\"roll\":%ld,\"yaw\":%ld,\"ax\":%ld,\"ay\":%ld,\"az\":%ld,\"wx\":%ld,\"wy\":%ld,\"wz\":%ld,\"h\":%.3f}",
                (Time::get() - startTime) / 1000.00,
                device->sensors.kernel.temperature,
                (long) device->sensors.kernel.pitch_raw, (long) device->sensors.kernel.roll_raw, (long) device->sensors.kernel.yaw_raw,
                (long) device->sensors.kernel.ax_raw, (long) device->sensors.kernel.ay_raw, (long) device->sensors.kernel.az_raw,
                (long) device->sensors.kernel.wx_raw, (long) device->sensors.kernel.wy_raw, (long) device->sensors.kernel.wz_raw,
                (float) device->sensors.kernel.heave
            );
        }
        else if (mode == HR_MODE_ADJ || mode == OR_MODE || mode == CAL_MODE) {
            n = snprintf(buffer, sizeof(buffer),
                "{\"time\":%.3f,\"tmp\":%.3f,\"pitch\":%.3f,\"roll\":%.3f,\"yaw\":%.3f,\"ax\":%.3f,\"ay\":%.3f,\"az\":%.3f,\"wx\":%.3f,\"wy\":%.3f,\"wz\":%.3f,\"h\":%.3f}",
                (Time::get() - startTime) / 1000.00,
                device->sensors.kernel.temperature,
                (float) device->sensors.kernel.pitch, (float) device->sensors.kernel.roll, (float) device->sensors.kernel.yaw,
                (float) device->sensors.kernel.ax, (float) device->sensors.kernel.ay, (float) device->sensors.kernel.az,
                (float) device->sensors.kernel.wx, (float) device->sensors.kernel.wy, (float) device->sensors.kernel.wz,
                (float) device->sensors.kernel.heave
            );
        } 
        else if (mode == QT_MODE) {
            n = snprintf(buffer, sizeof(buffer),
                "{\"time\":%.3f,\"tmp\":%.3f,\"pitch\":%ld,\"roll\":%ld,\"yaw\":%ld,\"q0\":%ld,\"q1\":%ld,\"q2\":%ld,\"q3\":%ld,\"h\":%.3f}",
                (Time::get() - startTime) / 1000.00,
                device->sensors.kernel.temperature,
                (long) device->sensors.kernel.pitch_raw, (long) device->sensors.kernel.roll_raw, (long) device->sensors.kernel.yaw_raw,
                (long) device->sensors.kernel.q0_raw, (long) device->sensors.kernel.q1_raw, (long) device->sensors.kernel.q2_raw, (long) device->sensors.kernel.q3_raw,
                (float) device->sensors.kernel.heave
            );
        }

        device->telemetry.serial.uart->write(buffer, n);
        device->telemetry.serial.uart->write('\n');
    }

    void printList(){
        static char buffer[256];
        const byte mode = device->sensors.kernel.mode;
        int n = 0;

        if(mode == HR_MODE){
            n = snprintf(buffer, sizeof(buffer),
                "[%.3f,%ld,%ld,%ld,%ld,%ld,%ld,%ld,%ld,%ld,%.3f]",
                device->sensors.kernel.temperature,
                (long) device->sensors.kernel.pitch_raw, (long) device->sensors.kernel.roll_raw, (long) device->sensors.kernel.yaw_raw,
                (long) device->sensors.kernel.ax_raw, (long) device->sensors.kernel.ay_raw, (long) device->sensors.kernel.az_raw,
                (long) device->sensors.kernel.wx_raw, (long) device->sensors.kernel.wy_raw, (long) device->sensors.kernel.wz_raw,
                (float) device->sensors.kernel.heave
            );
        } 
        else if(mode == HR_MODE_ADJ || mode == OR_MODE || mode == CAL_MODE){
            n = snprintf(buffer, sizeof(buffer),
                "[%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f,%.3f]",
                device->sensors.kernel.temperature,
                (float) device->sensors.kernel.pitch, (float) device->sensors.kernel.roll, (float) device->sensors.kernel.yaw,
                (float) device->sensors.kernel.ax, (float) device->sensors.kernel.ay, (float) device->sensors.kernel.az,
                (float) device->sensors.kernel.wx, (float) device->sensors.kernel.wy, (float) device->sensors.kernel.wz,
                (float) device->sensors.kernel.heave
            );
        }
        else if(mode == QT_MODE){
            n = snprintf(buffer, sizeof(buffer),
                "[%.3f,%ld,%ld,%ld,%ld,%ld,%ld,%ld,%.3f]",
                device->sensors.kernel.temperature,
                (long) device->sensors.kernel.pitch_raw, (long) device->sensors.kernel.roll_raw, (long) device->sensors.kernel.yaw_raw,
                (long) device->sensors.kernel.q0_raw, (long) device->sensors.kernel.q1_raw, (long) device->sensors.kernel.q2_raw, (long) device->sensors.kernel.q3_raw,
                (float) device->sensors.kernel.heave
            );
        }

        device->telemetry.serial.uart->write(buffer, n);
        device->telemetry.serial.uart->write('\n');
    }

    void printNMEA() {
        static char sentence[80];
        static char nmea[85];
        const char* header = "GPPASHR";

        snprintf(
            sentence, sizeof(sentence),
            "%s,%.3f,%.3f,%.3f",
            header,
            (float) device->processing.pitch.get(device->sensors.kernel.pitch),
            (float) device->processing.roll.get(device->sensors.kernel.roll),
            (float) device->processing.yaw.get(device->sensors.kernel.yaw)
        );

        unsigned char checksum = 0;
        size_t len = strlen(sentence);

        for(size_t i = 0; i < len; i++)
            checksum ^= (unsigned char) sentence[i];

        snprintf(nmea, sizeof(nmea), "$%s*%02X\r\n", sentence, checksum);
        device->telemetry.serial.uart->print(nmea);
    }
};

#endif