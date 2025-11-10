#ifndef TELEMETRY_H
#define TELEMETRY_H
#include <Arduino.h>
#include <HardwareSerial.h>
#include "../../globals/constants.h"
#include "../../globals/functions.h"
#include "serial/index.h"
#include "protocol/index.h"
#include "streamer/index.h"
#define MAX_SIZE 256 
#define TX_PIN 4
#define RX_PIN 3

template <typename Parent> class Telemetry{
  private:
    Parent* device;

  public:
    NextSerial<MAX_SIZE> serial;
    Protocol<Parent> protocol;
    Streamer<Parent> streamer;
    Text<MAX_SIZE> response;
    byte type = 0;

    Telemetry(Parent* dev):
        device(dev),
        streamer(dev),
        protocol(dev),
        serial(Serial2){}

    void setup(){
        Serial2.begin(115200, SERIAL_8N1, TX_PIN, RX_PIN);
        Serial.println("Telemetria Iniciada");
        streamer.setup();
    }

    void handle(){
        serial.listen();
        streamer.handle();
        
        if(!serial.available)
            return;

        if(protocol.handle())
            serial.reset();
        
        if(response.length() > 0)
            event(response.get());
    }

    void event(const char* value){
        Serial.println("(telemetry) event: " + String(value));
        serial.send(value, true);
        response.reset();
    }
};

#endif 
