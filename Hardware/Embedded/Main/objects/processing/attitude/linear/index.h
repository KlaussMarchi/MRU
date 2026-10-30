#ifndef LINEAR_MODEL_H
#define LINEAR_MODEL_H
#include <Arduino.h>
#include "config.h"


// LINHA = ANGULO CALIBRADO, COLUNA = ANGULO DO SENSOR (PITCH, ROLL, YAW): OS LINEAR_* DA CALIBRACAO
struct LinearParams{
	float M[3][3];
	float B[3];
};


// CADA ANGULO CALIBRADO E UMA COMBINACAO LINEAR DOS ANGULOS DO SENSOR: ref = M*x + B
class LinearModel : public Attitude{
  private:
	const LinearParams* params;

  public:
	void setup(const float dt, const LinearParams& linearParams){
		params = &linearParams;
		reset();
	}

	void update(const float* sensors, const float* angles, const float dt) override {
		float output[3];

		for(int i = 0; i < 3; i++){
			output[i] = params->B[i];

			for(int j = 0; j < 3; j++)
				output[i] += params->M[i][j] * angles[j];
		}

		pitch = output[0];
		roll  = output[1];
		yaw   = output[2];
	}

	void reset() override {
		pitch = 0; roll = 0; yaw = 0;
	}

	String toString() override {
		return String(LINEAR_NAME);
	}
};

#endif
