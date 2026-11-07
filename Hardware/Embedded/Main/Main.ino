#include "device/index.h"

static const char IMAGE[] = "MRU_FIRMWARE=v1.0.9";    // O APP LE ESTA MARCA NO .bin PARA MOSTRAR A VERSAO E RECUSAR O QUE NAO E FIRMWARE DO MRU
Device device{IMAGE + 13};


void setup(){
	device.components.encoder.enabled = false;
	device.components.leds.enabled = true;
	device.multitask     = true;
	device.sensors.debug = false;

	Serial.setRxBufferSize(1024);    // ANTES DO begin: UM BLOCO DA ATUALIZACAO NAO PODE TRANSBORDAR ENQUANTO O ESP GRAVA
	Serial.begin(115200);
	Serial.setTxTimeoutMs(0);    // USB PLUGADO SEM NINGUÉM LENDO: O LOG SE PERDE EM VEZ DE SEGURAR A TELEMETRIA DO RS232/RS422
	delay(1500);

	Serial.println("Serial Setup Complete... Starting Program");
	device.setup();
}

void loop(){
	device.tasks.handle();
}
