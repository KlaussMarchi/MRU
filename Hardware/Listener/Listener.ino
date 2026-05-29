#include <SoftwareSerial.h>
SoftwareSerial mru(3, 2);

const bool autostart = false;

void setup() {
    Serial.begin(9600);
    delay(500);
    Serial.println("programa iniciado...");

    mru.begin(9600);
    delay(500);

    if(autostart)
        mru.write("$stream_start!");
}

void loop(){
    while(Serial.available())
        mru.write(Serial.read());

    while(mru.available())
        Serial.write(mru.read());
}