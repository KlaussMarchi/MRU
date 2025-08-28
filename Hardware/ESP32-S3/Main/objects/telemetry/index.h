#ifndef TELEMETRY_H
#define TELEMETRY_H
#include <Arduino.h>
#include "../../globals/constants.h"
#include "../../globals/functions.h"
#include "../device/index.h"
#include "serial/index.h"
#define MAX_SIZE 256 


class Telemetry{
  public:
    const bool debug = true;
    byte type = 0;

    NextSerial<MAX_SIZE> serial = NextSerial<MAX_SIZE>(debug ? Serial : Serial2);
    Text<MAX_SIZE> response;

    void setup(){
        Serial.println("Telemetria Iniciada");
    }

    void event(const char* value){
        Serial.println("(telemetry) sent: " + String(value));
        serial.send(value, true);
    }

    void handle(){
        serial.listen();

        if(serial.available && routes())
            serial.reset();
        
        if(response.length() == 0)
            return;

        serial.send(response.get(), true);
        response.reset();
    }

    bool routes(){
        serial.clean();
        serial.print();

        if(serial.command.length() > 100)
            return true;

        if(serial.command.contains("$ETRS!"))
            device.reset();

        if(serial.command.contains("D:")){
            handleID();
            return true;
        }

        if(serial.command.contains("F:")){
            handleConfig();
            return true;
        }

        if(serial.command.contains("$ETKA!")){
            response.set("$ETACK!");
            return true;
        }
            
        if(serial.command.contains("settings")){
            serial.send(device.settings.params.toString());
            return true;
        }

        if(serial.command.contains("$ERASE!")){
            device.settings.erase(); 
            device.reset();
        }

        serial.reset();
        return false;
    }

    void handleID(){
        const int start = serial.command.find(':');
        const int end   = serial.command.find('$');

        if(start == -1 || end == -1)
            {response = "ERROR"; return;}
        
        auto key   = serial.command.substring(start+1, end);
        auto value = device.settings.params.get<const char*>(key.get());

        if(value == nullptr)
            {response = "ERROR"; return;}

        response.reset();
        response += '$';
        response += (value);
        response += '!';
    }

    void handleConfig(){
        const int start = serial.command.find(':');
        const int mid   = serial.command.find('$');
        const int end   = serial.command.find('!');

        if(start == -1 || mid == -1 || end == -1)
            {response = "NONE"; return;}

        auto key   = serial.command.substring(start+1, mid);
        auto value = serial.command.substring(mid+1, end);

        device.settings.params.set(key.get(), value.get());
        device.settings.save();
        response.set("OK");
    }
};


inline Telemetry telemetry;
#endif 
