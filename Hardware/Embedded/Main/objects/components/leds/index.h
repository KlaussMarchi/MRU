#ifndef LED_H
#define LED_H


class Duty{
  public:
    unsigned long startTime = Time::get();
    int pin, timeOn, timeOff;
    bool state;  

    void setup(){
        pinMode(pin, OUTPUT);
        digitalWrite(pin, HIGH);
        state = true;
    }

    void set(const int on, const int off){
        timeOn  = (on  == 1) ? 999999 : on;
        timeOff = (off == 1) ? 999999 : off;
    }

    void change(){
        state     = !state;
        startTime = Time::get();
        digitalWrite(pin, state ? HIGH : LOW);
    }

    void handle(){
        if(state && Time::get() - startTime > timeOn)
            return change();
        
        if(!state && Time::get() - startTime > timeOff)
            return change();
    }
};

class LEDs{
  public:
    bool enabled = true;
    Duty duty1, duty2;

    LEDs(int pin1, int pin2){
        duty1.pin = pin1;
        duty2.pin = pin2;
    }

    void setup(){
        if(!enabled)
            return;

        duty1.setup();
        duty2.setup();

        duty1.set(500, 1000);
        duty2.set(1000, 2000);
    }

    void handle(){
        if(!enabled)
            return;

        duty1.handle();
        duty2.handle();
    }
};


#endif