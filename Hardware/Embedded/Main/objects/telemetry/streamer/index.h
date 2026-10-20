#ifndef STREAMER_H
#define STREAMER_H
#include <Arduino.h>
#include "../../sensors/index.h"

template <typename Parent> class Streamer {
private:
	Parent* device;

public:
	static constexpr const char* KEYS[2][13] = {
		{"time", "tmp", "pitch", "roll", "yaw", "ax", "ay", "az", "wx", "wy", "wz", "heave", "heave_rate"},
		{"time", "tmp", "pitch", "roll", "yaw", "q0", "q1", "q2", "q3", "heave"}    // QT_MODE
	};

	unsigned long startTime = 0;
	unsigned long sent = 0;
	bool active, autostart;
	byte protocol = LIST_PROTOCOL;
	byte mode = CALIBRATED_MODE;
	int dt;

	Streamer(Parent* dev):
		device(dev){}

	void setup() {
		dt = (1.00 / device->frequency) * 1000;
		Serial.println("Frequency Set To " + String(device->frequency) + " Hz (sample time " + String(dt) + "ms)");

		protocol  = (byte) device->settings.template get<byte>("protocol");
		mode      = (byte) device->settings.template get<byte>("streamer_mode");
		autostart = device->settings.isEnabled("autostream");

		if(device->mode == ACQUISITION_MODE){    // ENSAIO: TODO PACOTE DO KERNEL, SO NA ESCALA, EM LISTA, SEM ESPERAR COMANDO
			mode      = SCALE_MODE;
			protocol  = LIST_PROTOCOL;
			autostart = true;
		}

		Serial.println("Streamer Mode: " + toString());

		if(autostart)
			set(true);
	}

	void handle() {
		static Listener timer = Listener(dt);

		if(!active || !ready(timer))
			return;

		double values[13];
		values[0] = device->sensors.kernel.lastAckTime*1e-6 - startTime*1e-3;    // s DESDE O INICIO DO STREAM, NA AMOSTRA DO KERNEL E NAO NA HORA DA IMPRESSAO
		const int length = 1 + ((mode == RAW_MODE) ? device->sensors.kernel.read(values + 1) : device->processing.read(values + 1));

		switch(protocol){
			case JSON_PROTOCOL: printJSON(values, length); break;
			case LIST_PROTOCOL: printList(values, length); break;
			case NMEA_PROTOCOL: printNMEA(values); break;
		}
	}

	// CADA PACOTE DO KERNEL SAI NO MAXIMO UMA VEZ (SEM PACOTE NOVO NAO HA O QUE ENVIAR); NO NORMAL O TIMER AINDA DECIMA PARA A frequency
	bool ready(Listener& timer){
		if(device->processing.count == sent)
			return false;

		if(device->mode != ACQUISITION_MODE && !timer.ready())
			return false;

		sent = device->processing.count;
		return true;
	}

	void set(const bool state) {
		if(active == state)
			return;

		startTime = Time::get();
		active    = state;
	}

	String toString(){
		if(mode == CALIBRATED_MODE) return "Calibrated Mode";
		if(mode == RAW_MODE)        return "Raw Mode";
		if(mode == SCALE_MODE)      return "Scale Mode";
		return "Unknown Mode";
	}

	// NO RAW_MODE O INTEIRO DO KERNEL SAI COMO VEIO; NOS OUTROS, TRES CASAS
	int getDigits(){
		return (mode == RAW_MODE) ? 0 : 3;
	}

	void printJSON(const double* values, const int length) {
		static char buffer[512];
		const char* const* keys = KEYS[device->sensors.kernel.mode == QT_MODE];
		int n = snprintf(buffer, sizeof(buffer), "{\"time\":%.3f", values[0]);

		for(int i = 1; i < length; i++)
			n += snprintf(buffer + n, sizeof(buffer) - n, ",\"%s\":%.*f", keys[i], getDigits(), values[i]);

		n += snprintf(buffer + n, sizeof(buffer) - n, "}");
		device->telemetry.serial.uart->write(buffer, n);
		device->telemetry.serial.uart->write('\n');
	}

	void printList(const double* values, const int length){
		static char buffer[320];
		int n = snprintf(buffer, sizeof(buffer), "[%.3f", values[0]);

		for(int i = 1; i < length; i++)
			n += snprintf(buffer + n, sizeof(buffer) - n, ",%.*f", getDigits(), values[i]);

		n += snprintf(buffer + n, sizeof(buffer) - n, "]");
		device->telemetry.serial.uart->write(buffer, n);
		device->telemetry.serial.uart->write('\n');
	}

	void printNMEA(const double* values) {
		static char sentence[80];
		static char nmea[85];
		const int heave = (device->sensors.kernel.mode == QT_MODE) ? 9 : 11;
		const double fields[4] = {values[2], values[3], values[4], values[heave]};    // pitch, roll, yaw E heave
		int n = snprintf(sentence, sizeof(sentence), "GPPASHR");

		for(int i = 0; i < 4; i++)
			n += snprintf(sentence + n, sizeof(sentence) - n, ",%.*f", getDigits(), fields[i]);

		unsigned char checksum = 0;
		size_t len = strlen(sentence);

		for(size_t i = 0; i < len; i++)
			checksum ^= (unsigned char) sentence[i];

		snprintf(nmea, sizeof(nmea), "$%s*%02X\r\n", sentence, checksum);
		device->telemetry.serial.uart->print(nmea);
	}
};

#endif
