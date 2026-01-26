#ifndef TIME_H
#define TIME_H
#include <Arduino.h>
#include "../text/index.h"


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

    static const char* getLeft(unsigned long t0, int timeout){
        static Text<30> response;

        int timeLeft = timeout - (Time::get() - t0) + 2000;
        const bool isMinutes = (timeLeft >= 60000);

        if(timeLeft < 60000)
            timeLeft = (timeLeft/1000.0) + 1;
        else
            timeLeft = (timeLeft/1000.0/60.0);

        response = "Tempo Restante: ";
        response += String(timeLeft);
        response += (isMinutes ? " min" : " sec");
        return response.get();
    }
};

#endif