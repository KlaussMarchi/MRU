#ifndef TIME_H
#define TIME_H
#include <Arduino.h>


class Time{
  public:
    unsigned long startTime;

    Time(){
        startTime = get();
    }

    static unsigned long get(){
        return esp_timer_get_time()/1000;
    }

    static void sleep(const int timeout){
        delay(timeout);
    }

    unsigned long getSec(){
        return get()/1000.00;
    }

    float alive(){
        return (get() - startTime)/1000.0;
    }
};

#endif