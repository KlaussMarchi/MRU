#include <SoftwareSerial.h>
SoftwareSerial mru(3, 2);

void setup() {
    Serial.begin(9600);
    delay(500);
    Serial.println("programa iniciado...");

    mru.begin(9600);
    delay(500);
    mru.write("$stream_start!");
}

void loop() {
    while(mru.available())
        Serial.write(mru.read());
}