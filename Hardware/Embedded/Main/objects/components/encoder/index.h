#ifndef ENCODER_H
#define ENCODER_H


class Encoder{
    private:
    const float ratio = 0.3000f; // Ratio corrigido para leitura 2X de um encoder 600 PPR (360/1200)
    volatile bool previous;
    int P1, P2;

    public:
    bool enabled = true;
    volatile int counter = 0;
    volatile float angle = 0;

    Encoder(int pin1, int pin2): 
        P1(pin1), 
        P2(pin2){}

    void setup(){
        pinMode(P1, INPUT_PULLUP);
        pinMode(P2, INPUT_PULLUP);
        previous = digitalRead(P1);
        counter  = 0;
        angle    = 0;
    }

    void IRAM_ATTR handle(){
        const bool state     = (bool) digitalRead(P1);
        const bool decreased = (digitalRead(P2) == state);

        if(state == previous)
            return;
        
        previous = state;
        counter  = decreased ? (counter - 1)   : (counter + 1);
        angle    = decreased ? (angle - ratio) : (angle + ratio);
    }

    void reset(){
        previous = digitalRead(P1);
        counter = 0;
        angle   = 0;
    }
};

#endif