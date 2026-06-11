#ifndef PROCESSING_H
#define PROCESSING_H

#include <cstdint>
#include <Arduino.h>
#include "../../utils/json/index.h"
#include "filters/index.h"


template <typename Parent> class Processing{
  private:
    Parent* device;

    class LinearFit{
      private:
        LowPassFilter filter;

      public:
        float a = 1;
        float b = 0;
        float constant  = 1;
        float fc = 0;
        bool use_filter = false;

        void setup(JsonObject data, float dt){
            if(data.containsKey("a"))
                this->a = data["a"];
            
            if(data.containsKey("b"))
                this->b = data["b"];
            
            if(data.containsKey("fc")){
                fc = data["fc"];
                use_filter = (fc > 0.0f);
                
                if(use_filter)
                    filter.setup(fc, dt);
            }
        }

        float get(int32_t newValue){
            float scaled = (float) newValue * constant;
            
            if(use_filter)
                scaled = filter.update(scaled);

            return (float) (a * scaled + b);
        }
    };

  public:
    bool active;
    LinearFit pitch, roll, yaw;
    LinearFit ax, ay, az;
    LinearFit wx, wy, wz;

    Processing(Parent* dev):
        device(dev){}

    void setup(){
        float dt = 1.0f / device->frequency;

        ax.constant = ay.constant = az.constant = 1.00f / (1000000.0f * 9.80665f);
        ay.constant = ay.constant;
        az.constant = az.constant;

        wx.constant = wy.constant = wz.constant = 1.00f / (100000.0f);
        wy.constant = wy.constant;
        wz.constant = wz.constant;

        pitch.constant = 1.00f / (1000.0f);
        roll.constant  = pitch.constant;
        yaw.constant   = pitch.constant;
    
        auto apply_fit = [&](LinearFit& fit, const char* key){
            if(!device->settings.params.data.containsKey("calibration"))
                return;
                
            JsonObject proc = device->settings.params.data["calibration"].template as<JsonObject>();
            
            if(proc.containsKey(key))
                fit.setup(proc[key].template as<JsonObject>(), dt);
        };

        apply_fit(pitch, "pitch");
        apply_fit(roll,  "roll");
        apply_fit(yaw,   "yaw");
        apply_fit(ax, "ax");
        apply_fit(ay, "ay");
        apply_fit(az, "az");
        apply_fit(wx, "wx");
        apply_fit(wy, "wy");
        apply_fit(wz, "wz");

        Serial.println("Calibration Options:");
        auto print_stats = [](const char* name, const LinearFit& fit) {
            String msg = String(name) + ":\t" + String(fit.a, 6) + " * x + " + String(fit.b, 6);
            if(fit.use_filter)
                msg += "\t| Filter: " + String(fit.fc, 2) + "Hz";
            Serial.println(msg);
        };

        print_stats("Pitch", pitch);
        print_stats("Roll ", roll);
        print_stats("Yaw  ", yaw);
        print_stats("Acc X", ax);
        print_stats("Acc Y", ay);
        print_stats("Acc Z", az);
        print_stats("Gyr X", wx);
        print_stats("Gyr Y", wy);
        print_stats("Gyr Z", wz);
    }

    bool parse(const String& jsonString){
        Json<512> update;
        Serial.println("New Parameters: " + String(jsonString));

        if(!update.parse(jsonString))
            return false;
        
        JsonObject rootObj = update.data.is<JsonArray>() ? update.data[0] : update.data.as<JsonObject>();

        auto setOptions = [&](const char* key) {
            if(!rootObj.containsKey(key))
                return;
            
            if(!device->settings.params.data.containsKey("calibration"))
                device->settings.params.data.createNestedObject("calibration");
                
            JsonObject proc = device->settings.params.data["calibration"].template as<JsonObject>();
            
            if(!proc.containsKey(key))
                proc.createNestedObject(key);
            
            JsonObject dest = proc[key].template as<JsonObject>();
            JsonObject src = rootObj[key].as<JsonObject>();
            
            if(src.containsKey("a")) dest["a"] = src["a"];
            if(src.containsKey("b")) dest["b"] = src["b"];
            if(src.containsKey("fc")) dest["fc"] = src["fc"];
        };
        
        setOptions("pitch"); setOptions("roll"); setOptions("yaw");
        setOptions("ax"); setOptions("ay"); setOptions("az");
        setOptions("wx"); setOptions("wy"); setOptions("wz");
        
        device->settings.save();
        setup();
        return true;
    }
};

#endif