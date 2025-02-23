#include <ArduinoJson.h>
unsigned long startProg;



void setup() {
    Serial.begin(9600);
    Serial.println("Iniciando...");
    startProg = millis();
    kalmanSetup();
}

void loop() {
    handleVelocity();
}

