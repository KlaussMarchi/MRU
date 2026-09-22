#ifndef PROCESSING_H
#define PROCESSING_H
#include <Arduino.h>
#include "config.h"
#include "filters/butterworth/index.h"
#include "filters/butterworth/config.h"


// O SINAL QUE O MRU ENTREGA: SENSORES FILTRADOS E ANGULOS DO MODELO QUE A CALIBRACAO ESCOLHEU
template <typename Parent> class Processing{
  private:
	Parent* device;
	int64_t lastPacket = 0;

	void read(float* sensors){
		sensors[0] = device->sensors.kernel.ax;
		sensors[1] = device->sensors.kernel.ay;
		sensors[2] = device->sensors.kernel.az;
		sensors[3] = device->sensors.kernel.wx;
		sensors[4] = device->sensors.kernel.wy;
		sensors[5] = device->sensors.kernel.wz;
	}

	// PRIMEIRO PACOTE: OS FILTROS COMECAM NA LEITURA, SEM O TRANSITORIO DE PARTIDA DO ZERO
	void start(){
		float sensors[6];
		read(sensors);

		for(int i = 0; i < 6; i++)
			filters[i].reset(sensors[i]);

		model.reset();
		mirror();
	}

	void update(const float dt){
		float sensors[6], angles[3];
		read(sensors);

		angles[0] = device->sensors.kernel.pitch;
		angles[1] = device->sensors.kernel.roll;
		angles[2] = device->sensors.kernel.yaw;

		ax = filters[0].compute(sensors[0]);
		ay = filters[1].compute(sensors[1]);
		az = filters[2].compute(sensors[2]);
		wx = filters[3].compute(sensors[3]);
		wy = filters[4].compute(sensors[4]);
		wz = filters[5].compute(sensors[5]);

		model.update(sensors, angles, dt);    // O MODELO VE O SINAL CRU, QUE E COMO ELE FOI AJUSTADO

		pitch = model.pitch;
		roll  = model.roll;
		yaw   = model.yaw;
	}

  public:
	ButterworthFilter filters[6];    // ax, ay, az, wx, wy, wz
	ProcessingModel model;

	float ax, ay, az;
	float wx, wy, wz;
	float pitch, roll, yaw;
	bool active = false;

	Processing(Parent* dev):
		device(dev){}

	void setup(){
		const float dt = 1.0f / device->frequency;

		for(int i = 0; i < 6; i++)
			filters[i].setup(BUTTERWORTH_FC[i], dt);

		model.setup(dt);
		active = (device->sensors.kernel.mode == HR_MODE) && !device->sensors.kernel.calibrate;

		mirror();
		Serial.println("Processing: " + toString());
	}

	void handle(){
		if(!active)
			return mirror();

		if(device->sensors.kernel.lastAckTime == lastPacket)    // SEM PACOTE NOVO: FILTRO NAO PODE COMER A MESMA AMOSTRA DUAS VEZES
			return;

		const bool first = (lastPacket == 0);
		const float dt   = (device->sensors.kernel.lastAckTime - lastPacket) * 1e-6f;
		lastPacket       = device->sensors.kernel.lastAckTime;

		if(first)
			return start();

		update(dt);
	}

	// SEM MODELO, EM AQUISICAO OU FORA DO MODO HR: SAI O QUE O SENSOR JA ENTREGA
	void mirror(){
		ax = device->sensors.kernel.ax;
		ay = device->sensors.kernel.ay;
		az = device->sensors.kernel.az;

		wx = device->sensors.kernel.wx;
		wy = device->sensors.kernel.wy;
		wz = device->sensors.kernel.wz;

		pitch = device->sensors.kernel.pitch;
		roll  = device->sensors.kernel.roll;
		yaw   = device->sensors.kernel.yaw;
	}

	void reset(){
		lastPacket = 0;
		model.reset();

		for(int i = 0; i < 6; i++)
			filters[i].reset();
	}

	String toString(){
		if(!active)
			return "raw sensor";

		return model.toString() + " + butterworth";
	}
};

#endif
