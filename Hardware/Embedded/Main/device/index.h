#ifndef PROG_DEVICE_H
#define PROG_DEVICE_H
#include "esp_timer.h"
#include "../globals/functions.h"
#include "../globals/constants.h"

#include "../utils/array/index.h"
#include "../utils/time/index.h"
#include "../utils/json/index.h"
#include "../utils/text/index.h"
#include "../utils/listener/index.h"

#include "settings/index.h"
#include "tasks/index.h"

#include "../objects/telemetry/index.h"
#include "../objects/sensors/index.h"
#include "../objects/components/index.h"
#include "../objects/processing/index.h"
#include "../objects/updater/index.h"
#include "../objects/health/index.h"


class Device{
  public:
	bool multitask = true;
	byte mode = NORMAL_MODE;
	float frequency = 100.0;
	unsigned long startTime;
	const char* firmware;
	Settings settings;
	Text<13> id;    // 4 + 8 DIGITOS DO MAC MAIS O TERMINADOR

	Telemetry<Device> telemetry;
	Sensors<Device> sensors;
	Processing<Device> processing;
	Tasks<Device> tasks;
	Components<Device> components;
	Updater<Device> updater;
	Health<Device> health;

	Device(const char* version):
		firmware(version),
		telemetry(this),
		sensors(this),
		processing(this),
		tasks(this),
		components(this),
		updater(this),
		health(this){}

	void setup(){
		char mac[sizeof(id.buffer)];
		snprintf(mac, sizeof(mac), "%04X%08lX", (uint16_t)(ESP.getEfuseMac() >> 32), (unsigned long)(uint32_t)ESP.getEfuseMac());
		id.set(mac);    // O Text SÓ CONTA O QUE ENTRA PELO set: ESCREVER NO buffer DEIXAVA O id VAZIO NO toString()

		Serial.println("Device Started: " + id.toString());
		Serial.println("Firmware: " + String(firmware));
		Serial.println();
		health.setup();
		components.setup();

		startTime = Time::get();
		settings.import();

		frequency = settings.template get<unsigned long>("frequency", 100);
		mode      = settings.template get<byte>("device_mode");
		Serial.println(mode == ACQUISITION_MODE ? "Device Mode: Acquisition" : "Device Mode: Normal");
		telemetry.setup();
		sensors.setup();
		processing.setup();
		health.log('I', "pronto: %s a %d bps, stream %s", telemetry.serial.getName(), telemetry.serial.baudrate, telemetry.streamer.active ? "ligado" : "desligado");
	}

	void reset(){
		updater.confirm();
		ESP.restart();
	}
};

#endif