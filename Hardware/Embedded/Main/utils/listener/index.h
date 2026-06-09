#ifndef LISTENER_H
#define LISTENER_H
#include <Arduino.h>

class Listener {
  private:
    uint64_t startTime;
    uint64_t timeout_us; 

  public:
    Listener(uint32_t _timeout_ms = 1000) {
        timeout_us = (uint64_t)_timeout_ms * 1000ULL;
        reset();
    }
    
    uint64_t time_us() {
        return esp_timer_get_time();
    }

    unsigned long get() {
        return (unsigned long)((time_us() - startTime) / 1000ULL);
    }

    float getSec() {
        return get() / 1000.0f;
    }

    float getMin() {
        return getSec() / 60.0f;
    }

    void set(uint32_t _timeout_ms) {
        timeout_us = (uint64_t)_timeout_ms * 1000ULL;
    }

    uint64_t passed(const uint64_t t0) {
        return (time_us() - t0);
    }

    void reset(){
        startTime = time_us();
    }
    
    bool ready(const bool auto_reset = true) {
        uint64_t current_time = time_us();

        if(current_time - startTime < timeout_us) 
            return false;

        if(!auto_reset) 
            return true;

        startTime = (startTime + timeout_us); 
        
        if(current_time - startTime > timeout_us)
            startTime = current_time;
        
        return true;
    }
};

#endif