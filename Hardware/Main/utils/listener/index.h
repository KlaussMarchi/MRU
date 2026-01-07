#ifndef LISTENER_H
#define LISTENER_H
#include <Arduino.h>


class Listener{
  public:
    unsigned long startTime;
    int timeout = 1000;

    Listener(int _timeout){
        startTime = time();
        timeout   = _timeout;
    }
    
    unsigned long time(){
        return esp_timer_get_time()/1000;
    }

    unsigned long get(){
        return (time() - startTime);
    }

    float getSec(){
        return get() / 1000.00;
    }

    float getMin(){
        return getSec() / 60.00;
    }

    void set(int _timeout){
        timeout = _timeout;
    }

    int passed(const unsigned long t0){
        return (time() - t0);
    }

    void reset(){
        startTime = time();
    }
    
    bool ready(const bool auto_reset=true){
        if(get() < timeout)
            return false;

        if(auto_reset)
            reset();
        
        return true;
    }
};

#endif