#ifndef ATTITUDE_H
#define ATTITUDE_H
#include <Arduino.h>


// CONTRATO DOS MODELOS DE ATITUDE: A CALIBRACAO ESCOLHE QUAL RODA SEM RECOMPILAR
class Attitude{
  public:
	float pitch = 0, roll = 0, yaw = 0;

	virtual void update(const float* sensors, const float* angles, const float dt) = 0;
	virtual void reset() = 0;
	virtual String toString() = 0;
};

#include "kalman/index.h"
#include "linear/index.h"
#include "machine/index.h"
#include "config.h"

#endif
