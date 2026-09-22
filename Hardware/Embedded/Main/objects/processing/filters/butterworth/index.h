#ifndef BUTTERWORTH_FILTER_H
#define BUTTERWORTH_FILTER_H
#include <Arduino.h>


// SEGUNDA ORDEM POR TUSTIN COM PRE-DISTORCAO, ESPELHO DO ButterworthFilter DO Calibration/Filters
class ButterworthFilter{
  public:
	float a[3], b[3];
	float f_c;
	float Xn1, Yn1;
	float Xn2, Yn2;

	void setup(const float cutoff, const float dt){
		f_c = cutoff * dt;    // FRACAO DA AMOSTRAGEM: O ENSAIO MEDIU O CORTE EM Hz, AQUI O PASSO E OUTRO

		if(f_c <= 0.0f)
			f_c = 0.0001f;

		if(f_c >= 0.499f)
			f_c = 0.499f;

		const float wc   = tan(PI*f_c);
		const float c2   = wc*wc;
		const float norm = 1 + sqrt(2)*wc + c2;

		b[0] = c2/norm;
		b[1] = 2*c2/norm;
		b[2] = c2/norm;

		a[0] = 1.0f;
		a[1] = -2*(c2 - 1)/norm;
		a[2] = -(1 - sqrt(2)*wc + c2)/norm;
		reset();
	}

	float compute(const float Xn){
		const float Yn = (b[0]*Xn + b[1]*Xn1 + b[2]*Xn2 + a[1]*Yn1 + a[2]*Yn2);
		Yn2 = Yn1; Yn1 = Yn;
		Xn2 = Xn1; Xn1 = Xn;
		return Yn;
	}

	// ESTADOS NA PRIMEIRA LEITURA: REGIME PERMANENTE, SEM O TRANSITORIO DE PARTIDA DO ZERO
	void reset(const float value = 0.0f){
		Xn1 = value; Xn2 = value;
		Yn1 = value; Yn2 = value;
	}
};

#endif
