#ifndef PROCESSING_H
#define PROCESSING_H
#include <Arduino.h>
#include "filters/index.h"
#include "correction/index.h"
#include "align/index.h"
#include "attitude/index.h"
#include "heave/index.h"
#include "lever/index.h"
#include "calibration/index.h"


// O SINAL QUE O MRU ENTREGA: O KERNEL NA ESCALA DO ICD, PRE-FILTRO, CORRECAO E ATITUDE NO MODO CALIBRADO, E HEAVE E BRACO DE ALAVANCA NOS DOIS
template <typename Parent> class Processing{
  private:
	Parent* device;
	int64_t lastPacket = 0;

  public:
	Calibration calibration;
	Filters filters;
	Align align;
	KalmanModel kalman;
	LinearModel linear;
	MachineModel machine;
	Attitude* attitude = &kalman;    // O MODELO QUE A CALIBRACAO ESCOLHEU
	Heave heave;
	Lever lever;

	float tmp;
	float ax, ay, az;
	float wx, wy, wz;
	float q0, q1, q2, q3;
	float pitch, roll, yaw;
	float h = 0, hr = 0;
	unsigned long count = 0;    // PACOTES PROCESSADOS: A AQUISICAO MANDA CADA UM UMA VEZ
	bool active = false;        // HEAVE NA SAIDA: PRECISA DA ACELERACAO DO PACOTE
	bool calibrated = false;    // PRE-FILTRO, CORRECAO E ATITUDE; SEM ELES HEAVE E BRACO USAM O KERNEL

	Processing(Parent* dev):
		device(dev){}

	void setup(){
		const float dt = 1.0f / KernelSensor::RATE;    // OS ESTAGIOS ANDAM NA TAXA DO KERNEL, NAO NA DO STREAMER
		calibration.setup();

		const CalibrationData& params = calibration.data;
		const int model = (int) params.model;

		filters.setup(dt, params.filters);
		kalman.setup(dt, params.kalman);
		linear.setup(dt, params.linear);
		machine.setup(dt, params.machine);
		heave.setup(params.heave);
		lever.setup(params.heave, params.lever);

		attitude = (model == LINEAR_MODEL)  ? (Attitude*) &linear  :
		           (model == MACHINE_MODEL) ? (Attitude*) &machine : (Attitude*) &kalman;

		const byte mode = device->telemetry.streamer.mode;
		active          = (mode != RAW_MODE) && (device->sensors.kernel.mode != QT_MODE);    // O RAW SAI DIRETO DO KERNEL, SEM LER DAQUI
		calibrated      = active && (mode == CALIBRATED_MODE);

		if(calibrated)
			align.setup(device->sensors.kernel.alignment, params.align, params.correction);

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
		attitude->reset();
		heave.reset();
		lever.reset();
	}

	// O CALIBRADO TROCA OS CAMPOS DO KERNEL PELOS CORRIGIDOS ANTES; HEAVE E BRACO SAO OS MESMOS NOS DOIS MODOS
	void update(const float dt){
		if(calibrated)
			calibrate(dt);

		const float accel[2][3] = {{ay, ax, -az}, {ax, ay, az}};    // KERNEL (X BORESTE, Y PROA, Z CIMA) NA ORDEM DO vertical() (PROA, BORESTE, BAIXO), COM O PITCH DELE EM X E O ROLL EM Y; O CALIBRADO JA ESTA NELA
		heave.update(accel[calibrated], pitch, roll, dt);
		lever.update(heave.heave, pitch, roll, dt);

		h  = lever.heave;
		hr = lever.rate;
	}

	// PRE-FILTRO, CORRECAO E ATITUDE: OS SENSORES VAO AOS EIXOS DO NAVIO E OS ANGULOS SAO OS DO MODELO
	void calibrate(const float dt){
		float sensors[6]      = {ax, ay, az, wx, wy, wz};
		const float angles[3] = {pitch, roll, yaw};

		filters.compute(sensors);
		align.apply(sensors, tmp);    // A CORRECAO NOS EIXOS DO ALIGN DE AGORA
		attitude->update(sensors, angles, dt);

		ax = sensors[0]; ay = sensors[1]; az = sensors[2];
		wx = sensors[3]; wy = sensors[4]; wz = sensors[5];

		pitch = attitude->pitch;
		roll  = attitude->roll;
		yaw   = attitude->yaw;
	}

	// CAMPOS NA ORDEM DO STREAMER, OS MESMOS NA ESCALA E NO CALIBRADO: ATITUDE, SENSORES E O HEAVE COM A TAXA DELE NO PONTO DE INTERESSE
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
		values[10] = h; values[11] = hr;
		return 12;
	}

	void reset(){
		lastPacket = 0;
	}

	String toString(){
		if(!active)
			return "kernel scale";

		if(!calibrated)
			return "kernel scale + heave + lever";

		return attitude->toString() + " + filters + correction" + (align.active ? " + align" : "") + " + heave + lever";
	}
};

#endif
