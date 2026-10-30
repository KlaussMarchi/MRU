#ifndef CORRECTION_H
#define CORRECTION_H
#include <Arduino.h>
#include "config.h"


// x = M x + c + k (T - T0) DE CADA TRIEDRO: OS CORRECTION_* DA CALIBRACAO, 0 ACELEROMETRO E 1 GIROSCOPIO
struct CorrectionParams{
	float T0;
	float M[2][3][3];
	float C[2][3];
	float K[2][3];
};


// CALIBRACAO DETERMINISTICA DOS DOIS TRIEDROS, COM M LEVANDO OS EIXOS DO KERNEL AOS DO NAVIO
void correct(float* sensors, const float temperature, const CorrectionParams& params){
	for(int s = 0; s < 2; s++){    // 0 ACELEROMETRO, 1 GIROSCOPIO
		const float in[3] = {sensors[3*s], sensors[3*s+1], sensors[3*s+2]};

		for(int i = 0; i < 3; i++)
			sensors[3*s+i] = params.M[s][i][0]*in[0] + params.M[s][i][1]*in[1] + params.M[s][i][2]*in[2] + params.C[s][i] + params.K[s][i]*(temperature - params.T0);
	}
}

#endif
