#ifndef MACHINE_MODEL_H
#define MACHINE_MODEL_H
#include <Arduino.h>
#include "config.h"


#define MACHINE_FEATURES (MACHINE_INPUTS*MACHINE_STATES)


// PASSO DA JANELA, DE ONDE CADA BLOCO LE, SAIDAS E A REGRESSAO PADRONIZADA: OS MACHINE_* DA CALIBRACAO, NAS DIMENSOES COMPILADAS
struct MachineParams{
	float period;
	float sensor[MACHINE_INPUTS];
	float target[3];
	float mean[MACHINE_FEATURES];
	float scale[MACHINE_FEATURES];
	float coef[MACHINE_OUTPUTS][MACHINE_FEATURES];
	float bias[MACHINE_OUTPUTS];
};


// REGRESSAO SOBRE A JANELA DE ESTADOS DOS SENSORES, PADRONIZADA COM A MEDIA E O DESVIO DO TREINO
class MachineModel : public Attitude{
  private:
	float window[MACHINE_INPUTS][MACHINE_STATES];    // [sensor][atraso], 0 E A AMOSTRA ATUAL
	float elapsed;
	int   filled;
	const MachineParams* params;

	void shift(const float* sensors){
		for(int i = 0; i < MACHINE_INPUTS; i++){
			for(int j = MACHINE_STATES - 1; j > 0; j--)
				window[i][j] = window[i][j-1];

			window[i][0] = sensors[(int) params->sensor[i]];
		}

		if(filled < MACHINE_STATES)
			filled++;
	}

	void compute(float* output){
		int feature = 0;

		for(int k = 0; k < MACHINE_OUTPUTS; k++)
			output[k] = params->bias[k];

		for(int i = 0; i < MACHINE_INPUTS; i++){
			for(int j = 0; j < MACHINE_STATES; j++, feature++){
				const float value = (window[i][j] - params->mean[feature]) / params->scale[feature];

				for(int k = 0; k < MACHINE_OUTPUTS; k++)
					output[k] += params->coef[k][feature] * value;
			}
		}
	}

  public:
	void setup(const float dt, const MachineParams& machineParams){
		params = &machineParams;
		reset();
	}

	void update(const float* sensors, const float* angles, const float dt) override {
		if(filled < MACHINE_STATES){    // JANELA ENCHENDO: SAI O ANGULO DO SENSOR ATE O MODELO TER O QUE PREVER
			pitch = angles[0];
			roll  = angles[1];
			yaw   = angles[2];
		}

		elapsed += dt;

		if(elapsed < params->period)    // A JANELA VALE NA TAXA DO TREINO: MAIS RAPIDO ENCOLHE O TEMPO QUE ELA COBRE
			return;

		elapsed -= params->period;
		shift(sensors);

		if(filled < MACHINE_STATES)     // JANELA INCOMPLETA: A PREVISAO SAIRIA COM ZEROS
			return;

		float output[MACHINE_OUTPUTS];
		compute(output);

		const int target[3] = {(int) params->target[0], (int) params->target[1], (int) params->target[2]};
		pitch = (target[0] < 0) ? angles[0] : output[target[0]];
		roll  = (target[1] < 0) ? angles[1] : output[target[1]];
		yaw   = (target[2] < 0) ? angles[2] : output[target[2]];
	}

	void reset() override {
		memset(window, 0, sizeof(window));
		elapsed = 0;
		filled  = 0;

		pitch = 0; roll = 0; yaw = 0;
	}

	String toString() override {
		return String(MACHINE_NAME);
	}
};

#endif
