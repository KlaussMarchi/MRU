#ifndef PROTOCOL_H
#define PROTOCOL_H
#include <Arduino.h>


template <typename Parent> class Protocol{
  private:
    Parent* device;

  public:
    Protocol(Parent* dev):
        device(dev){}

    void check(){
        device->telemetry.serial.clean();

        if(device->telemetry.serial.command.contains("MICRS")){
            device->reset();
            return;
        }

        if(device->telemetry.serial.command.contains("D:")){
            handleID();
            return;
        }

        if(device->telemetry.serial.command.contains("F:")){
            handleConfig();
            return;
        }
        
        if(device->telemetry.serial.command.contains("$STREAM!")){
            device->telemetry.streamer.set(true);
            return;
        }

        if(device->telemetry.serial.command.contains("$STOP!")){
            device->telemetry.streamer.set(false);
            return;
        }

        if(device->telemetry.serial.command.contains("$PROT_STREAM!")){
            device->telemetry.protobuf.set(true);
            return;
        }

        if(device->telemetry.serial.command.contains("$PROT_STOP!")){
            device->telemetry.protobuf.set(false);
            return;
        }

        if(device->telemetry.serial.command.contains("$ETKA!")){
            device->telemetry.response.set("$ETACK!");
            return;
        }
            
        if(device->telemetry.serial.command.contains("settings")){
            device->telemetry.serial.send(device->settings.params.toString());
            return;
        }

        if(device->telemetry.serial.command.contains("$ERASE!")){
            device->settings.erase(); 
            device->reset();
        }

        device->telemetry.serial.reset();
    }

    void handleID(){
        const int start = device->telemetry.serial.command.find(':');
        const int end   = device->telemetry.serial.command.find('$');

        if(start == -1 || end == -1)
            return device->telemetry.response.set("ERROR");
        
        auto key   = device->telemetry.serial.command.substring(start+1, end);
        auto value = device->settings.template get<String>(key.get());

        if(value.length() == 0)
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
        device->telemetry.response.set("OK");
        device->settings.save();
    }
};

#endif