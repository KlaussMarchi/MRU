#ifndef LED_H
#define LED_H

#define LED01 1
#define LED02 2


class Duty{
  public:
    unsigned long startTime = Time::get();
    bool state = false;  
    int pin    = 0;

    void setup(int _pin){
        pin = _pin;
        pinMode(pin, OUTPUT);
    }

    void set(const bool value){
        if(state == value)
            return;
        
        state     = value;
        startTime = Time::get();
        digitalWrite(pin, state ? HIGH : LOW);
    }

    void handle(const int on, const int off){
        const int onTime  = on;
        const int timeOff = off;

        if(state && Time::get() - startTime > onTime)
            return set(!state);
        
        if(!state && Time::get() - startTime > timeOff)
            return set(!state);
    }
};

template <typename Parent> class LED{
  private:
    Parent* device;

  public:
    bool enabled = true;
    Duty pin1, pin2;

    LED(Parent* dev):
        device(dev){}

    void setup(){
        if(!enabled)
            return;

        pin1.setup(LED01);
        pin2.setup(LED02);

        pin1.set(true);
        pin2.set(true);
    }

    void handle(){
        if(!enabled)
            return;

        pin1.handle(1000, 2000);
        pin2.handle(500, 500);
    }
};


#endif