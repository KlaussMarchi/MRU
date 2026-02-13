#ifndef ENCODER_H
#define ENCODER_H

class Encoder {
  private:
    const double ratio = 90.00f/326.00f;
    int P1, P2;
    bool previous;

  public:
    bool enabled = false;
    int counter  = 0;
    double angle = 0;

    Encoder(int pin1, int pin2): 
        P1(pin1), 
        P2(pin2){}

    void setup(){
        pinMode(P1, INPUT_PULLUP);
        pinMode(P2, INPUT_PULLUP);
        previous = digitalRead(P1);
    }

    void handle() {
        const bool state = (bool) digitalRead(P1);
        const bool decreased = (digitalRead(P2) == state);

        if(state == previous)
            return;
        
        previous = state;
        counter  = decreased ? (counter - 1)   : (counter + 1);
        angle    = decreased ? (angle - ratio) : (angle + ratio);
    }
};

#endif