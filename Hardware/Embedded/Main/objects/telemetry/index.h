#ifndef TELEMETRY_H
#define TELEMETRY_H
#include "protocol/index.h"
#include "serial/index.h"
#include "streamer/index.h"
#include <Arduino.h>

#define CMD_MAX_SIZE 256


template <typename Parent> class Telemetry{
private:
	Parent *device;

public:
	NextSerial<CMD_MAX_SIZE> serial;
	Text<CMD_MAX_SIZE> last_cmd;
	Protocol<Parent> protocol;
	Streamer<Parent> streamer;
	Text<64> response;
	bool working;

	Telemetry(Parent *dev): 
		device(dev),
		protocol(dev),
		streamer(dev){}

	void setup(){
		int baud = device->settings.template get<int>("baudrate", 9600);

		serial.setup(baud);
		Serial.println("baudrate: " + String(baud));

		streamer.setup();
		response.reset();
	}

	void handle(){
		serial.listen();

		if(serial.available)
			Serial.println(serial.command.toString());

		if(serial.available)
			protocol.check();

		if(Time::get() - serial.lastAckTime > 60000)
			working = false;

		if(response.length() > 0)
			event(response.get());

		if(serial.available)
			last_cmd = serial.command.get();

		streamer.handle();
		serial.reset();
	}

	void event(const char *value){
		// device->logs.add(value);
		serial.send(value, true);
		response.reset();
	}

	void event(const String &value){
		// device->logs.add(value.c_str());
		serial.send(value.c_str(), true);
		response.reset();
	}
};

#endif
