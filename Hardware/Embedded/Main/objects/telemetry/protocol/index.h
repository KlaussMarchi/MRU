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

		if(device->telemetry.serial.command.contains("CL:")){
			handleCalibration();
			return;
		}

		if(device->telemetry.serial.command.contains("CS:")){
			handleConfig(false);
			return;
		}

		if(device->telemetry.serial.command.contains("calibration_save")){
			handleSave();
			return;
		}

		if(device->telemetry.serial.command.contains("calibration_erase")){
			device->processing.calibration.erase();
			restart("$CALIBRATION ERASED!");
			return;
		}

		if(device->telemetry.serial.command.contains("calibration_check")){
			device->telemetry.serial.send(device->processing.calibration.toJson());
			return;
		}

		if(device->telemetry.serial.command.contains("status")){
			handleStatus();
			return;
		}

		if(device->telemetry.serial.command.contains("D:")){
			handleID();
			return;
		}

		if(device->telemetry.serial.command.contains("F:")){
			handleConfig(true);
			return;
		}

		if(device->telemetry.serial.command.contains("updt")){
			device->updater.start();
			return;
		}

		if(device->telemetry.serial.command.contains("firmware")){
			device->telemetry.response.set(device->firmware);
			return;
		}

		if(device->telemetry.serial.command.contains("stream_start")){
			device->telemetry.streamer.set(true);
			return;
		}

		if(device->telemetry.serial.command.contains("stream_stop")){
			device->telemetry.streamer.set(false);
			return;
		}

		if(device->telemetry.serial.command.contains("calibrate")){
			device->telemetry.response.set(device->processing.toString());
			return;
		}

		if(device->telemetry.serial.command.contains("check_sensor")){
			device->telemetry.response.set(device->sensors.working ? "OK" : "NOT WORKING");
			return;
		}

		if(device->telemetry.serial.command.contains("align")){
			const int start = device->telemetry.serial.command.find(':');
			const int end   = device->telemetry.serial.command.find('!');

			if(start == -1 || end == -1)
				return device->telemetry.response.set("ERROR");

			long value = device->telemetry.serial.command.substring(start + 1, end).toInt();
			device->sensors.kernel.align(static_cast<byte>(value));
			device->processing.reset();    // A ATITUDE DE REFERENCIA MUDOU: FILTRO E MODELO RECOMECAM
			device->telemetry.response.set("ALIGNMENT COMPLETE: ");
			device->telemetry.response += String(value);
			return;
		}

		if(device->telemetry.serial.command.contains("ackoneledge")){
			device->telemetry.response.set("$MICACK!");
			return;
		}

		if(device->telemetry.serial.command.contains("reset_encoder")){
			device->telemetry.response.set("$MICACK!");
			device->components.encoder.reset();
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

	// CF:chave$valor! GRAVA E REINICIA; CS:chave$valor! SO GRAVA, PARA VARIAS CONFIGURACOES VALEREM NUM REINICIO SO (MICRS)
	void handleConfig(const bool reboot){
		const int start = device->telemetry.serial.command.find(':');
		const int mid   = device->telemetry.serial.command.find('$');
		const int end   = device->telemetry.serial.command.find('!');

		if(start == -1 || mid == -1 || end == -1)
			return device->telemetry.response.set("NONE");

		auto key   = device->telemetry.serial.command.substring(start+1, mid);
		auto value = device->telemetry.serial.command.substring(mid+1, end);

		device->settings.params.set(key.get(), value.get());
		device->settings.save();

		if(reboot)
			return restart((key.toString() + " set to " + value.toString()).c_str());

		device->telemetry.response.set("$OK:" + key.toString() + "=" + value.toString() + "!");
	}

	// CL:CHAVE@posicao$v1,v2,...! PREENCHE A CALIBRACAO PENDENTE, QUE SO VALE DEPOIS DO $calibration_save!
	void handleCalibration(){
		const int start = device->telemetry.serial.command.find(':');
		const int mid   = device->telemetry.serial.command.find('$');
		const int end   = device->telemetry.serial.command.find('!');

		if(start == -1 || mid == -1 || end == -1)
			return device->telemetry.response.set("$ERROR!");

		auto key         = device->telemetry.serial.command.substring(start+1, mid);
		const int at     = key.find('@');
		const int offset = (at == -1) ? 0 : key.substring(at+1, key.length()).toInt();

		if(at != -1)
			key = key.substring(0, at);

		const int count = device->processing.calibration.set(key.get(), offset, device->telemetry.serial.command.substring(mid+1, end).get());

		if(count < 0)
			return device->telemetry.response.set("$ERROR:" + key.toString() + "!");

		device->telemetry.response.set("$OK:" + key.toString() + "@" + String(offset) + "+" + String(count) + "!");
	}

	void handleSave(){
		if(!device->processing.calibration.save())
			return device->telemetry.response.set("$ERROR:SAVE!");

		restart("$CALIBRATION SAVED!");
	}

	// RETRATO DO MRU PARA O APP: IDENTIDADE, PORTA, MODOS EFETIVOS, SENSOR, ALIGN DO KERNEL E A CALIBRACAO EM USO
	void handleStatus(){
		const auto& kernel = device->sensors.kernel;
		JsonDocument doc;

		doc["id"]            = device->id.get();
		doc["firmware"]      = device->firmware;
		doc["port"]          = device->telemetry.serial.getName();
		doc["baud"]          = device->telemetry.serial.baudrate;
		doc["device_mode"]   = device->mode;
		doc["streamer_mode"] = device->telemetry.streamer.mode;
		doc["protocol"]      = device->telemetry.streamer.protocol;
		doc["kernel_mode"]   = kernel.mode;
		doc["frequency"]     = device->frequency;
		doc["autostream"]    = device->telemetry.streamer.autostart;
		doc["streaming"]     = device->telemetry.streamer.active;
		doc["sensor"]        = device->sensors.working;
		doc["kernel_baud"]   = kernel.baud;
		doc["processing"]    = device->processing.toString();
		doc["calibration"]   = device->processing.calibration.getSource();
		doc["model"]         = (int) device->processing.calibration.data.model;

		JsonArray align = doc["align"].to<JsonArray>();

		for(const float angle : kernel.alignment)
			isnan(angle) ? align.add(nullptr) : align.add(angle);    // NAN NAO E JSON: O KERNEL QUE NAO RESPONDEU SAI null

		String output;
		serializeJson(doc, output);
		device->telemetry.serial.send(output);
	}

	// A RESPOSTA SAI ANTES DO REINICIO: SEM ELA O APP NAO SABE SE O COMANDO CHEGOU
	void restart(const char* message){
		device->telemetry.serial.send(message);
		delay(500);
		device->reset();
	}
};

#endif