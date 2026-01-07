#ifndef TELEMETRY_H
#define TELEMETRY_H
#include <Arduino.h>
#include <HardwareSerial.h>
#include "../../globals/constants.h"
#include "../../globals/functions.h"
#include "serial/index.h"
#include "protocol/index.h"
#include "streamer/index.h"
#include "protobuf/index.h"
#define MAX_SIZE 256 
#define RX_PIN 10
#define TX_PIN 11


template <typename Parent> class Telemetry{
  private:
    Parent* device;

  public:
    NextSerial<MAX_SIZE> serial = NextSerial<MAX_SIZE>(RX_PIN, TX_PIN);
    Protocol<Parent> protocol;
    Streamer<Parent> streamer;
    Protobuf<Parent> protobuf;
    Text<MAX_SIZE> response;
    byte type = 0;

    Telemetry(Parent* dev):
        device(dev),
        streamer(dev),
        protocol(dev),
        protobuf(dev){}

    void setup(){
        Serial.println("Telemetria Iniciada");
        serial.setup();
        streamer.setup();
        protobuf.setup();
    }

    void handle(){
        serial.listen();
        streamer.handle();

        if(protobuf.active)
            protobuf.handle();
        
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
