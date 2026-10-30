#include "device/index.h"
Device device{"v1.0.8"};


void setup(){
	device.components.encoder.enabled = false;
	device.components.leds.enabled = true;
	device.multitask     = true;
	device.sensors.debug = false;

	Serial.begin(115200);
	Serial.setTxTimeoutMs(0);    // USB PLUGADO SEM NINGUÉM LENDO: O LOG SE PERDE EM VEZ DE SEGURAR A TELEMETRIA DO RS232/RS422
	delay(1500);

	Serial.println("Serial Setup Complete... Starting Program");
	device.setup();
}

void loop(){
	device.tasks.handle();
}
