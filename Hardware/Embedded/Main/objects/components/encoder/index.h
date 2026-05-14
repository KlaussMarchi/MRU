#ifndef ENCODER_H
#define ENCODER_H

#include <Arduino.h>

class Encoder {
  private:
    int pinA, pinB;
    const double ratio = 360.00 / (2.00 * 5000.00); 
    volatile long counter = 0;
    static Encoder* instance;

    #if defined(ESP32)
        static void IRAM_ATTR isrWrapper();
        void IRAM_ATTR update(); 
    #else
        static void isrWrapper();
        void update();
    #endif

  public:
    bool enabled = true;

    Encoder(int pA, int pB);
    void setup();
    void reset();
    float get();
};

#endif