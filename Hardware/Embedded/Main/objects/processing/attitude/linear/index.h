#ifndef LINEAR_MODEL_H
#define LINEAR_MODEL_H
#include <Arduino.h>
#include "config.h"


// CADA ANGULO CALIBRADO E UMA COMBINACAO LINEAR DOS ANGULOS DO SENSOR: ref = M*x + B
class LinearModel{
  public:
	float pitch, roll, yaw;

	void setup(const float dt){
		reset();
	}

	void update(const float* sensors, const float* angles, const float dt){
		float output[3];

		for(int i = 0; i < 3; i++){
			output[i] = LINEAR_B[i];

			for(int j = 0; j < 3; j++)
				output[i] += LINEAR_M[i][j] * angles[j];
		}

		pitch = output[0];
		roll  = output[1];
		yaw   = output[2];
	}

	void reset(){
		pitch = 0; roll = 0; yaw = 0;
	}

	String toString(){
		return String(LINEAR_NAME);
	}
};

#endif
