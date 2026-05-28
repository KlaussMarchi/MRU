#include "index.h"

Encoder* Encoder::instance = nullptr;

Encoder::Encoder(int pA, int pB) : pinA(pA), pinB(pB) {
    instance = this;
}

#if defined(ESP32)
void IRAM_ATTR Encoder::isrWrapper() {
    if (instance != nullptr) instance->update();
}

void IRAM_ATTR Encoder::update() {
#else
void Encoder::isrWrapper() {
    if (instance != nullptr) instance->update();
}

void Encoder::update() {
#endif
    bool stateA = digitalRead(pinA);
    bool stateB = digitalRead(pinB);
    
    counter += (stateA == stateB) ? -1 : 1;
}

void Encoder::setup() {
    pinMode(pinA, INPUT_PULLUP);
    pinMode(pinB, INPUT_PULLUP);
    attachInterrupt(digitalPinToInterrupt(pinA), isrWrapper, CHANGE);
}

void Encoder::reset() {
    noInterrupts();
    counter = 0;
    interrupts();
}

float Encoder::get() {
    if(!enabled)
        return 0;

    noInterrupts();
    long currentCounter = counter;
    interrupts();
    
    return currentCounter * ratio;
}