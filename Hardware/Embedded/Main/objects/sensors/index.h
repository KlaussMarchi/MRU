#ifndef SENSORS_H
#define SENSORS_H
#include <Arduino.h>
#include "Kernel/index.h"


template <typename Parent> class Sensors{
  private:
    Parent* device;
    
  public:
    KernelSensor kernel = KernelSensor(4, 3);
    bool working = false;
    bool debug   = false;

    Sensors(Parent* dev):
        device(dev){}

    void setup(){
        if(debug)
            return;

        kernel.mode = device->settings.template get<byte>("kernel_mode");
        kernel.setup();
    }

    void handle(){
        if(debug)
            return;

        kernel.updated_this_frame = false;
        kernel.handle();
        check();
        
        if (kernel.mode == CAL_MODE && kernel.updated_this_frame) {
            kernel.ax = device->processing.ax.get(kernel.ax_raw);
            kernel.ay = device->processing.ay.get(kernel.ay_raw);
            kernel.az = device->processing.az.get(kernel.az_raw);
            
            kernel.wx = device->processing.wx.get(kernel.wx_raw);
            kernel.wy = device->processing.wy.get(kernel.wy_raw);
            kernel.wz = device->processing.wz.get(kernel.wz_raw);
            
            kernel.pitch = device->processing.pitch.get(kernel.pitch_raw);
            kernel.roll  = device->processing.roll.get(kernel.roll_raw);
            kernel.yaw   = device->processing.yaw.get(kernel.yaw_raw);
            
            kernel.heaveFilter.update(kernel.ax, kernel.ay, kernel.az, kernel.pitch, kernel.roll);
            kernel.heave = kernel.heaveFilter.getHeave();
        }
    }

    void check(){
        working = kernel.working;
    }
};

#endif