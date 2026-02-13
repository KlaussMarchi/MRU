#ifndef COMPONENTS_H
#define COMPONENTS_H
#include "encoder/index.h"
#include "leds/index.h"

template <typename Parent> class Components{
  private:
    Parent* device;

  public:
    Encoder encoder = Encoder(8, 9);
    LEDs leds = LEDs(1, 2);

    Components(Parent* dev):
        device(dev){}

    void setup(){
        if(encoder.enabled)
            encoder.setup();

        if(leds.enabled)
            leds.setup();
    }

    void handle(){
        if(leds.enabled){
            handleSensors();
            handleComm();
            leds.handle();   
        }

        if(encoder.enabled)
            encoder.handle();
    }

    void handleSensors(){
        if(device->sensors.working)
            return leds.duty1.set(500, 500);

        leds.duty1.set(0, 1);
    }

    void handleComm(){
        if(device->telemetry.streamer.active)
            return leds.duty2.set(200, 200);

        if(device->telemetry.working)
            return leds.duty2.set(500, 500);

        leds.duty2.set(0, 1);
    }
};

/*
led 1: sensores
    - nada funcionando: apagado
    - kernel funcionando: duty 0.5 seg on 0.5 seg off 

led 2: comunicação
    - nada funcionando: apagado
    - streamando: duty 0.2 seg on e 0.2 seg off
    - comunicando por protocolo: duty 0.5 seg on e 0.5 seg off

*/

#endif