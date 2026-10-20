#ifndef PROCESSING_H
#define PROCESSING_H
#include <Arduino.h>
#include "filters/index.h"
#include "correction/index.h"
#include "align/index.h"
#include "attitude/config.h"
#include "heave/index.h"
#include "lever/index.h"


// O SINAL QUE O MRU ENTREGA: O KERNEL NA ESCALA DO ICD E, NO MODO CALIBRADO, PRE-FILTRO, CORRECAO, ATITUDE, HEAVE E BRACO DE ALAVANCA
template <typename Parent> class Processing{
  private:
	Parent* device;
	int64_t lastPacket = 0;

  public:
	Filters filters;
	Align align;
	AttitudeModel attitude;
	Heave heave;
	Lever lever;

	float tmp;
	float ax, ay, az;
	float wx, wy, wz;
	float q0, q1, q2, q3;
	float pitch, roll, yaw;
	float h = 0, hr = 0;
	unsigned long count = 0;    // PACOTES PROCESSADOS: A AQUISICAO MANDA CADA UM UMA VEZ
	bool active = false;

	Processing(Parent* dev):
		device(dev){}

	void setup(){
		const float dt = 1.0f / KernelSensor::RATE;    // OS ESTAGIOS ANDAM NA TAXA DO KERNEL, NAO NA DO STREAMER

		filters.setup(dt);
		attitude.setup(dt);
		heave.setup();
		lever.setup();

		active = (device->telemetry.streamer.mode == CALIBRATED_MODE) && (device->sensors.kernel.mode != QT_MODE);

		if(active)
			align.setup(device->sensors.kernel.alignment);

		Serial.println("Processing: " + toString());
	}

	void handle(){
		if(device->sensors.kernel.lastAckTime == lastPacket)    // SEM PACOTE NOVO: FILTRO NAO PODE COMER A MESMA AMOSTRA DUAS VEZES
			return;

		const bool first = (lastPacket == 0);
		const float dt   = (device->sensors.kernel.lastAckTime - lastPacket) * 1e-6f;
		lastPacket       = device->sensors.kernel.lastAckTime;
		scale();
		count++;

		if(!active)
			return;

		if(first)
			start();

		update(first ? 0.0f : dt);
	}

	// O PACOTE NA ESCALA DO ICD: m/s^2, graus/s, graus, QUATERNION UNITARIO E graus C
	void scale(){
		const KernelSensor& kernel = device->sensors.kernel;
		const KernelScale& k       = KernelSensor::SCALE[kernel.mode];

		tmp = kernel.temperature * k.temperature;
		ax  = kernel.ax * k.accel; ay = kernel.ay * k.accel; az = kernel.az * k.accel;
		wx  = kernel.wx * k.gyro;  wy = kernel.wy * k.gyro;  wz = kernel.wz * k.gyro;
		q0  = kernel.q0 * k.quat;  q1 = kernel.q1 * k.quat;  q2 = kernel.q2 * k.quat; q3 = kernel.q3 * k.quat;

		pitch = kernel.pitch * k.angle;
		roll  = kernel.roll  * k.angle;
		yaw   = kernel.yaw   * k.angle;
		h     = 0; hr = 0;
	}

	// PRIMEIRO PACOTE: OS FILTROS COMECAM NA LEITURA E OS OUTROS ESTAGIOS RECOMECAM
	void start(){
		const float sensors[6] = {ax, ay, az, wx, wy, wz};

		filters.reset(sensors);
		attitude.reset();
		heave.reset();
		lever.reset();
	}

	void update(const float dt){
		float sensors[6]      = {ax, ay, az, wx, wy, wz};
		const float angles[3] = {pitch, roll, yaw};

		filters.compute(sensors);
		align.apply(sensors, tmp);    // A CORRECAO NOS EIXOS DO ALIGN DE AGORA
		attitude.update(sensors, angles, dt);
		heave.update(sensors, attitude.pitch, attitude.roll, dt);
		lever.update(heave.heave, attitude.pitch, attitude.roll, dt);

		ax = sensors[0]; ay = sensors[1]; az = sensors[2];
		wx = sensors[3]; wy = sensors[4]; wz = sensors[5];

		pitch = attitude.pitch;
		roll  = attitude.roll;
		yaw   = attitude.yaw;
		h     = lever.heave;
		hr    = lever.rate;
	}

	// CAMPOS NA ORDEM DO STREAMER: OS DO KERNEL NA ESCALA E, CALIBRADO, MAIS O HEAVE E A TAXA DELE NO PONTO DE INTERESSE
	int read(double* values) const {
		values[0] = tmp;
		values[1] = pitch; values[2] = roll; values[3] = yaw;

		if(device->sensors.kernel.mode == QT_MODE){
			values[4] = q0; values[5] = q1; values[6] = q2; values[7] = q3;
			values[8] = h;
			return 9;
		}

		values[4] = ax; values[5] = ay; values[6] = az;
		values[7] = wx; values[8] = wy; values[9] = wz;
		values[10] = h;

		if(!active)
			return 11;

		values[11] = hr;
		return 12;
	}

	void reset(){
		lastPacket = 0;
	}

	String toString(){
		if(!active)
			return "kernel scale";

		return attitude.toString() + " + filters + correction" + (align.active ? " + align" : "") + " + heave + lever";
	}
};

#endif
