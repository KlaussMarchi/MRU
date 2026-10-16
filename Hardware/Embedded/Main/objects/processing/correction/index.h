#ifndef CORRECTION_H
#define CORRECTION_H
#include <Arduino.h>
#include "config.h"


// CALIBRACAO DETERMINISTICA DOS DOIS TRIEDROS: x = M x + c + k (T - T0), COM M LEVANDO OS EIXOS DO KERNEL AOS DO NAVIO
void correct(float* sensors, const float temperature){
	for(int s = 0; s < 2; s++){    // 0 ACELEROMETRO, 1 GIROSCOPIO
		const float in[3] = {sensors[3*s], sensors[3*s+1], sensors[3*s+2]};

		for(int i = 0; i < 3; i++)
			sensors[3*s+i] = CORRECTION_M[s][i][0]*in[0] + CORRECTION_M[s][i][1]*in[1] + CORRECTION_M[s][i][2]*in[2] + CORRECTION_C[s][i] + CORRECTION_K[s][i]*(temperature - CORRECTION_T0);
	}
}

#endif
