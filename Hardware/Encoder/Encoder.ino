#include <Arduino.h>
#include "encoder/index.cpp"

Encoder encoder = Encoder(2, 3);

void setup() {
    Serial.begin(115200);
    encoder.setup(); 
}

void loop() {
    static unsigned long startTime = millis();

    if (millis() - startTime < 10)
        return;

    startTime = millis();
    Serial.print("-90,90,");
    Serial.println(encoder.get(), 4);
}