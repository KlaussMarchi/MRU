#ifndef MACHINE_MODEL_H
#define MACHINE_MODEL_H
#include <Arduino.h>
#include "config.h"


// REGRESSAO SOBRE A JANELA DE ESTADOS DOS SENSORES, PADRONIZADA COM A MEDIA E O DESVIO DO TREINO
class MachineModel{
  private:
	float window[MACHINE_INPUTS][MACHINE_STATES];    // [sensor][atraso], 0 E A AMOSTRA ATUAL
	float elapsed;
	int   filled;

	void shift(const float* sensors){
		for(int i = 0; i < MACHINE_INPUTS; i++){
			for(int j = MACHINE_STATES - 1; j > 0; j--)
				window[i][j] = window[i][j-1];

			window[i][0] = sensors[MACHINE_SENSOR[i]];
		}

		if(filled < MACHINE_STATES)
			filled++;
	}

	void compute(float* output){
		int feature = 0;

		for(int k = 0; k < MACHINE_OUTPUTS; k++)
			output[k] = MACHINE_BIAS[k];

		for(int i = 0; i < MACHINE_INPUTS; i++){
			for(int j = 0; j < MACHINE_STATES; j++, feature++){
				const float value = (window[i][j] - MACHINE_MEAN[feature]) / MACHINE_SCALE[feature];

				for(int k = 0; k < MACHINE_OUTPUTS; k++)
					output[k] += MACHINE_COEF[k][feature] * value;
			}
		}
	}

  public:
	float pitch, roll, yaw;

	void setup(const float dt){
		reset();
	}

	void update(const float* sensors, const float* angles, const float dt){
		if(filled < MACHINE_STATES){    // JANELA ENCHENDO: SAI O ANGULO DO SENSOR ATE O MODELO TER O QUE PREVER
			pitch = angles[0];
			roll  = angles[1];
			yaw   = angles[2];
		}

		elapsed += dt;

		if(elapsed < MACHINE_PERIOD)    // A JANELA VALE NA TAXA DO TREINO: MAIS RAPIDO ENCOLHE O TEMPO QUE ELA COBRE
			return;

		elapsed -= MACHINE_PERIOD;
		shift(sensors);

		if(filled < MACHINE_STATES)     // JANELA INCOMPLETA: A PREVISAO SAIRIA COM ZEROS
			return;

		float output[MACHINE_OUTPUTS];
		compute(output);

		pitch = (MACHINE_TARGET[0] < 0) ? angles[0] : output[MACHINE_TARGET[0]];
		roll  = (MACHINE_TARGET[1] < 0) ? angles[1] : output[MACHINE_TARGET[1]];
		yaw   = (MACHINE_TARGET[2] < 0) ? angles[2] : output[MACHINE_TARGET[2]];
	}

	void reset(){
		memset(window, 0, sizeof(window));
		elapsed = 0;
		filled  = 0;

		pitch = 0; roll = 0; yaw = 0;
	}

	String toString(){
		return String(MACHINE_NAME);
	}
};

#endif
