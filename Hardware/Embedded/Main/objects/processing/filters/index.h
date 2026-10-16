#ifndef FILTERS_H
#define FILTERS_H
#include <Arduino.h>

#define FILTER_BUTTERWORTH 0
#define FILTER_LOW_PASS    1
#define FILTER_EXPONENTIAL 2

#include "config.h"


// SECAO y = b0 x + b1 x1 + b2 x2 + a1 y1 + a2 y2; DE PRIMEIRA ORDEM COM b2 = a2 = 0
class Biquad{
  public:
	float b[3], a[3];
	float Xn1, Xn2, Yn1, Yn2;

	void set(const float b0, const float b1, const float b2, const float a1, const float a2){
		b[0] = b0; b[1] = b1; b[2] = b2;
		a[0] = 1;  a[1] = a1; a[2] = a2;
	}

	float compute(const float Xn){
		const float Yn = b[0]*Xn + b[1]*Xn1 + b[2]*Xn2 + a[1]*Yn1 + a[2]*Yn2;
		Yn2 = Yn1; Yn1 = Yn;
		Xn2 = Xn1; Xn1 = Xn;
		return Yn;
	}

	// ESTADOS NA PRIMEIRA LEITURA: REGIME PERMANENTE, SEM O TRANSITORIO DE PARTIDA DO ZERO
	void reset(const float value){
		Xn1 = value; Xn2 = value;
		Yn1 = value; Yn2 = value;
	}
};


// PASSA-BAIXA DE CADA EIXO NA TAXA DO KERNEL, NO TIPO QUE O Calibration/1 - Filters ESCOLHEU: O ANTI-ALIASING ANTES DE O STREAMER DECIMAR
class Filters{
  public:
	Biquad sections[6][4];    // ax, ay, az, wx, wy, wz: ATE QUATRO SECOES EM CASCATA
	int count[6];

	void setup(const float dt){
		for(int i = 0; i < 6; i++)
			count[i] = design(sections[i], FILTERS_TYPE[i], FILTERS_FC[i], dt);
	}

	// COEFICIENTES DE UM EIXO PELO CORTE EM Hz, ESPELHO DAS CLASSES DO NOTEBOOK; DEVOLVE QUANTAS SECOES USA
	int design(Biquad* section, const int type, const float f_c, const float dt){
		if(type == FILTER_BUTTERWORTH){
			const float f    = constrain(f_c*dt, 0.0001f, 0.499f);    // FRACAO DA AMOSTRAGEM: PRE-DISTORCAO DE TUSTIN
			const float wc   = tan(PI*f);
			const float c2   = wc*wc;
			const float norm = 1 + sqrt(2)*wc + c2;
			section[0].set(c2/norm, 2*c2/norm, c2/norm, -2*(c2 - 1)/norm, -(1 - sqrt(2)*wc + c2)/norm);
			return 1;
		}

		if(type == FILTER_LOW_PASS){
			const float k = PI*f_c*dt;    // Wc*dt/2: QUATRO POLOS REAIS EM Wc POR TUSTIN, SEM PRE-DISTORCAO

			for(int i = 0; i < 4; i++)
				section[i].set(k/(1 + k), k/(1 + k), 0, (1 - k)/(1 + k), 0);

			return 4;
		}

		if(type == FILTER_EXPONENTIAL){
			const float alpha = 1 - expf(-2*PI*f_c*dt);    // MESMA CONSTANTE DE TEMPO EM QUALQUER TAXA
			section[0].set(alpha, 0, 0, 1 - alpha, 0);
			return 1;
		}

		return 0;
	}

	void compute(float* sensors){
		for(int i = 0; i < 6; i++)
			for(int j = 0; j < count[i]; j++)
				sensors[i] = sections[i][j].compute(sensors[i]);
	}

	void reset(const float* sensors){
		for(int i = 0; i < 6; i++)
			for(int j = 0; j < count[i]; j++)
				sections[i][j].reset(sensors[i]);
	}
};

#endif
