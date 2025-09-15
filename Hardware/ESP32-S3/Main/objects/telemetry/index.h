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


template <typename Parent> class Telemetry{
  private:
    Parent* device;

  public:
    NextSerial<MAX_SIZE> serial{Serial};
    Protocol<Parent> protocol;
    Streamer<Parent> streamer;
    Text<MAX_SIZE> response;
    byte type = 0;

    Telemetry(Parent* dev):
        device(dev),
        streamer(dev),
        protocol(dev){}

    void setup(){
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
