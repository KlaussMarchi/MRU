#include <SoftwareSerial.h>

// Configura RX no pino 2 e TX no pino 3
SoftwareSerial mru(2, 3);

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("programa iniciado...");

    mru.begin(115200);
    delay(500);

    mru.println("$stream_start!");
    mru.write("$stream_start!");
}

void loop() {
    while (mru.available())
      Serial.write((char) mru.read());
}