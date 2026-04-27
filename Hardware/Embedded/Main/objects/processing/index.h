#ifndef PROCESSING_H
#define PROCESSING_H

#include <cstdint>
#include <Arduino.h>
#include "../../utils/json/index.h"

template <typename Parent> class Processing{
  private:
    Parent* device;

    class LinearFit{
      public:
        float a, b;

        void setup(float a, float b){
            this->a = a;
            this->b = b;
        }

        float get(uint32_t value){
            return (float) (a * value + b);
        }
    };

  public:
    LinearFit pitch, roll, yaw;

    Processing(Parent* dev):
        device(dev){}

    void setup(){
        if(device->settings.params.data.containsKey("pitch"))
            pitch.setup(device->settings.params.data["pitch"][0], device->settings.params.data["pitch"][1]);
        
        if(device->settings.params.data.containsKey("roll"))
            roll.setup(device->settings.params.data["roll"][0], device->settings.params.data["roll"][1]);
        
        if(device->settings.params.data.containsKey("yaw"))
            yaw.setup(device->settings.params.data["yaw"][0], device->settings.params.data["yaw"][1]);

        Serial.println("Processing Options");
        Serial.println("Pitch: " + String(pitch.a, 6) + " * x + " + String(pitch.b, 6));
        Serial.println("Roll: " + String(roll.a, 6) + " * x + " + String(roll.b, 6));
        Serial.println("Yaw: " + String(yaw.a, 6) + " * x + " + String(yaw.b, 6));
    }

    bool parse(const String& jsonString){
        Json<512> update;
        Serial.println("New Parameters: " + String(jsonString));

        if(!update.parse(jsonString))
            return false;
        
        if(update.data.containsKey("pitch"))
            device->settings.params.data["pitch"] = update.data["pitch"];
        
        if(update.data.containsKey("roll"))
            device->settings.params.data["roll"] = update.data["roll"];
        
        if(update.data.containsKey("yaw"))
            device->settings.params.data["yaw"] = update.data["yaw"];
        
        device->settings.save();
        setup();
        return true;
    }
};

#endif