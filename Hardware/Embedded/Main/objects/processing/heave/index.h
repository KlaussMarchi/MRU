#ifndef HEAVE_H
#define HEAVE_H
#include <Arduino.h>
#include "config.h"


// (R v)_z: A TERCEIRA LINHA DE R = Rz Ry Rx, QUE NAO DEPENDE DA PROA
float vertical(const float* v, const float pitch, const float roll){
	const float p = radians(pitch), r = radians(roll);
	return -sinf(p)*v[0] + sinf(r)*cosf(p)*v[1] + cosf(r)*cosf(p)*v[2];
}


// SECAO z'' = u - 2 zeta w z' - w^2 z COM A ENTRADA LINEAR NO PASSO: z' E O INTEGRADOR LIMITADO E z'' O PASSA-ALTA, ESPELHO DO Calibration/4 - Heave
class Section{
  public:
	static constexpr double GAP = 0.5;    // s SEM PACOTE: A INTEGRACAO NAO ATRAVESSA O BURACO, RECOMECA EM REGIME

	double w, zeta;
	double z0, z1, z2, u;    // double: PASSO PEQUENO SOBRE ESTADO GRANDE, EM float O ARREDONDAMENTO DE z0 ACUMULA
	bool primed = false;

	void setup(const double period, const double damping){
		w    = 2*PI/(10*period);    // wc = 2 pi / (10 Th) DA EP 2 092 402
		zeta = damping;
	}

	void update(const double input, const double dt){
		if(!primed || dt > GAP){    // PRIMEIRA AMOSTRA: REGIME PARA ELA, SEM O DEGRAU DE PARTIDA
			z0 = input/(w*w);
			z1 = 0; z2 = 0;
			u  = input;
			primed = true;
			return;
		}

		const double w0 = u     - 2*zeta*w*z1 - w*w*z0;
		const double w1 = input - 2*zeta*w*z1 - w*w*z0;
		z0 += z1*dt + dt*dt*(2*w0 + w1)/6;
		z1 += dt*(w0 + w1)/2;
		z2  = input - 2*zeta*w*z1 - w*w*z0;
		u   = input;
	}

	void reset(){
		primed = false;
	}
};


// HEAVE NO SENSOR, POSITIVO PARA BAIXO: ACELERACAO VERTICAL PELA ATITUDE, MAIS g, DUAS VEZES INTEGRADA COM PASSA-ALTA
class Heave{
  public:
	Section velocity, position;
	float heave = 0;

	void setup(){
		velocity.setup(HEAVE_PERIOD, HEAVE_DAMPING);
		position.setup(HEAVE_PERIOD, HEAVE_DAMPING);
	}

	void update(const float* accel, const float pitch, const float roll, const float dt){
		velocity.update(vertical(accel, pitch, roll) + HEAVE_GRAVITY, dt);
		position.update(velocity.z1, dt);
		heave = position.z1;
	}

	void reset(){
		velocity.reset();
		position.reset();
		heave = 0;
	}
};

#endif
