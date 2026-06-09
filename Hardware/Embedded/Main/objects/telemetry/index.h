#ifndef TELEMETRY_H
#define TELEMETRY_H
#include "modes/coppe/index.h"
#include "protocol/index.h"
#include "serial/index.h"
#include "streamer/index.h"
#include <Arduino.h>

#define CMD_MAX_SIZE 256


template <typename Parent> class Telemetry{
private:
    Parent *device;

public:
    NextSerial<CMD_MAX_SIZE> serial;
    Text<CMD_MAX_SIZE> last_cmd;
    Protocol<Parent> protocol;
    Streamer<Parent> streamer;
    Text<64> response;
    Coppe<Parent> coppe;
    byte type = 0;
    bool working;

    Telemetry(Parent *dev): 
        device(dev),
        streamer(dev),
        protocol(dev),
        coppe(dev){}

    void setup(){
        type = device->settings.template get<byte>("telemetry");
        serial.setup(device->settings.template get<int>("baudrate", 9600));

        if(type == COPPE_TEL)
            coppe.setup();

        streamer.setup();
        response.reset();
    }

    void handle() {
        serial.listen();

        if(serial.available)
            Serial.println(serial.command.toString());

        handleProtocol();
        handleRequest();

        if(Time::get() - serial.lastAckTime > 60000)
            working = false;

        if(response.length() > 0)
            event(response.get());

        if(serial.available)
            last_cmd = serial.command.get();

        streamer.handle();

        handleOperation();
        serial.reset();
    }

    void handleProtocol() {
        if(type == COPPE_TEL)
            coppe.check();

        if(serial.available)
            protocol.check();
    }

    void handleRequest() {
        if (type == COPPE_TEL)
            coppe.request();
    }

    void handleOperation() {
        if (type == COPPE_TEL)
            coppe.handle();
    }

    void event(const char *value) {
        // device->logs.add(value);
        serial.send(value, true);
        response.reset();
    }

    void event(const String &value) {
        // device->logs.add(value.c_str());
        serial.send(value.c_str(), true);
        response.reset();
    }

    const char *toText() {
        if (type == COPPE_TEL)
            return "Padrão";

        return "None";
    }
};

#endif
