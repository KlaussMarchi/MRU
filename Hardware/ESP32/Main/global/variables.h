#ifndef VARIABLES_H
#define VARIABLES_H


struct Variables{
    StaticJsonDocument<2048> settings;
    const char* firmware    = "v5.3.7";
    unsigned long startTime = esp_timer_get_time()/1000;
    bool serial_debug = true;
    bool print_on = true;
    bool stream = false;
    Stream& serial = serial_debug ? Serial : Serial2;
}; 


inline Variables variables;
#endif