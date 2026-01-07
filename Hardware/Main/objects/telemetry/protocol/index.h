#ifndef PROTOCOL_H
#define PROTOCOL_h
#include <Arduino.h>


template <typename Parent> class Protocol{
  public:
    Parent* device;

    Protocol(Parent* dev):
        device(dev){}

    bool handle(){
        device->telemetry.serial.command.clean();
        device->telemetry.serial.print();

        if(device->telemetry.serial.command.contains("$MICRS!")){
            device->reset();
            return true;
        }

        if(device->telemetry.serial.command.contains("D:")){
            handleID();
            return true;
        }

        if(device->telemetry.serial.command.contains("F:")){
            handleConfig();
            return true;
        }
        
        if(device->telemetry.serial.command.contains("$STREAM!")){
            device->telemetry.streamer.set(true);
            return true;
        }

        if(device->telemetry.serial.command.contains("$STOP!")){
            device->telemetry.streamer.set(false);
            return true;
        }

        if(device->telemetry.serial.command.contains("$PROT_STREAM!")){
            device->telemetry.protobuf.set(true);
            return true;
        }

        if(device->telemetry.serial.command.contains("$PROT_STOP!")){
            device->telemetry.protobuf.set(false);
            return true;
        }

        if(device->telemetry.serial.command.contains("$ETKA!")){
            device->telemetry.response.set("$ETACK!");
            return true;
        }
            
        if(device->telemetry.serial.command.contains("settings")){
            device->telemetry.serial.send(device->settings.params.toString());
            return true;
        }

        if(device->telemetry.serial.command.contains("$ERASE!")){
            device->settings.erase(); 
            device->reset();
        }

        device->telemetry.serial.reset();
        return false;
    }

    void handleID(){
        const int start = device->telemetry.serial.command.find(':');
        const int end   = device->telemetry.serial.command.find('$');

        if(start == -1 || end == -1)
            return device->telemetry.response.set("ERROR");
        
        auto key   = device->telemetry.serial.command.substring(start+1, end);
        auto value = device->settings.template get<const char*>(key.get());

        if(value == nullptr)
            return device->telemetry.response.set("ERROR");

        device->telemetry.response.reset();
        device->telemetry.response += '$';
        device->telemetry.response += (value);
        device->telemetry.response += '!';
    }

    void handleConfig(){
        const int start = device->telemetry.serial.command.find(':');
        const int mid   = device->telemetry.serial.command.find('$');
        const int end   = device->telemetry.serial.command.find('!');

        if(start == -1 || mid == -1 || end == -1)
            return device->telemetry.response.set("NONE");

        auto key   = device->telemetry.serial.command.substring(start+1, mid);
        auto value = device->telemetry.serial.command.substring(mid+1, end);

        device->settings.params.set(key.get(), value.get());
        device->settings.save();
        device->telemetry.response.set("OK");
    }
};

#endif