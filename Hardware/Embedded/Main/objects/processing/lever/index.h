#ifndef LEVER_H
#define LEVER_H
#include <Arduino.h>
#include "../heave/index.h"
#include "config.h"


// HEAVE NO PONTO DE INTERESSE: O DO SENSOR MAIS (R d)_z PELO MESMO PASSA-ALTA QUE A INTEGRACAO DUPLA APLICOU AO SENSOR
class Lever{
  public:
	Section first, second;
	float heave = 0, rate = 0;    // m E m/s NO PONTO, POSITIVOS PARA BAIXO

	void setup(){
		first.setup(HEAVE_PERIOD, HEAVE_DAMPING);
		second.setup(HEAVE_PERIOD, HEAVE_DAMPING);
	}

	void update(const float sensor, const float pitch, const float roll, const float dt){
		const float previous = heave;
		first.update(vertical(LEVER_POINT, pitch, roll), dt);
		second.update(first.z2, dt);
		heave = sensor + second.z2;
		rate  = (dt > 0 && dt <= Section::GAP) ? (heave - previous)/dt : 0;    // O HEAVE JA SAI SUAVE DA INTEGRACAO: A DIFERENCA NAO AMPLIFICA RUIDO
	}

	void reset(){
		first.reset();
		second.reset();
		heave = 0; rate = 0;
	}
};

#endif
