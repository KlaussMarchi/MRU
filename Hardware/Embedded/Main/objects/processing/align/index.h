#ifndef ALIGN_H
#define ALIGN_H
#include <Arduino.h>
#include "config.h"
#include "../correction/index.h"


// A CORRECAO FOI AJUSTADA COM O KERNEL NO ALIGN DO ENSAIO: COM OUTRO ALIGN, A ENTRADA VOLTA AOS EIXOS DO ENSAIO E A SAIDA VAI AOS DO NAVIO DE AGORA
class Align{
  private:
	float Q[3][3];    // ALIGN DE AGORA SOBRE O DO ENSAIO, NOS EIXOS DO KERNEL
	float F[3][3];    // A MESMA ROTACAO NOS EIXOS DO NAVIO

	// ICD APENDICE B: PROA HORARIA EM Z, PITCH EM X, ROLL EM Y; CADA COLUNA E UM EIXO DO KERNEL NOS EIXOS DO NAVIO
	static void rotation(const float* angles, float R[3][3]){
		const float ch = cosf(radians(angles[0])), sh = -sinf(radians(angles[0]));
		const float cp = cosf(radians(angles[1])), sp = sinf(radians(angles[1]));
		const float cr = cosf(radians(angles[2])), sr = sinf(radians(angles[2]));

		R[0][0] = ch*cr - sh*sp*sr; R[0][1] = -sh*cp; R[0][2] = ch*sr + sh*sp*cr;
		R[1][0] = sh*cr + ch*sp*sr; R[1][1] = ch*cp;  R[1][2] = sh*sr - ch*sp*cr;
		R[2][0] = -cp*sr;           R[2][1] = sp;     R[2][2] = cp*cr;
	}

	static void product(const float A[3][3], const float B[3][3], float C[3][3], const bool transpose){
		for(int i = 0; i < 3; i++)
			for(int j = 0; j < 3; j++){
				C[i][j] = 0;

				for(int k = 0; k < 3; k++)
					C[i][j] += A[i][k] * (transpose ? B[j][k] : B[k][j]);
			}
	}

	static void rotate(float* sensors, const float R[3][3], const bool transpose){
		for(int s = 0; s < 2; s++){    // 0 ACELEROMETRO, 1 GIROSCOPIO
			const float v[3] = {sensors[3*s], sensors[3*s+1], sensors[3*s+2]};

			for(int i = 0; i < 3; i++)
				sensors[3*s+i] = transpose ? R[0][i]*v[0] + R[1][i]*v[1] + R[2][i]*v[2] : R[i][0]*v[0] + R[i][1]*v[1] + R[i][2]*v[2];
		}
	}

  public:
	bool active = false;

	void setup(const float* alignment){
		float now[3][3], test[3][3], frame[3][3], deviation = 0;
		active = !isnan(alignment[0]) && !isnan(ALIGN_CALIBRATION[0]);

		if(active){
			rotation(alignment, now);
			rotation(ALIGN_CALIBRATION, test);
			product(now, test, Q, true);
			product(ALIGN_FRAME, Q, frame, false);
			product(frame, ALIGN_FRAME, F, true);
		}

		for(int i = 0; active && i < 3; i++)
			for(int j = 0; j < 3; j++)
				deviation = max(deviation, fabsf(Q[i][j] - (i == j)));

		active = active && deviation > 1e-4f;    // MESMO ALIGN DO ENSAIO: A CORRECAO JA ESTA NOS EIXOS CERTOS
		Serial.printf("Align: ensaio %.0f %.0f %.0f | Kernel %.0f %.0f %.0f | %s\n", ALIGN_CALIBRATION[0], ALIGN_CALIBRATION[1], ALIGN_CALIBRATION[2], alignment[0], alignment[1], alignment[2], active ? "correcao girada" : "sem rotacao");
	}

	void apply(float* sensors, const float temperature){
		if(active)
			rotate(sensors, Q, true);

		correct(sensors, temperature);

		if(active)
			rotate(sensors, F, false);
	}
};

#endif
