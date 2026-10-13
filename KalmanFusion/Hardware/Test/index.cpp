#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include "../index.h"


// RODA O KalmanModel SOBRE O CSV EXPORTADO PELO NOTEBOOK (time, ax, ay, az em g, wx, wy, wz em graus/s, pitch, roll, yaw) E IMPRIME O TEMPO MEDIO DO update() EM MICROSSEGUNDOS
int main(int argc, char** argv){
	if(argc < 4){
		fprintf(stderr, "uso: %s entrada.csv saida.csv periodo\n", argv[0]);
		return 1;
	}

	FILE* input  = fopen(argv[1], "r");
	FILE* output = fopen(argv[2], "w");

	if(!input || !output){
		fprintf(stderr, "nao abriu %s ou %s\n", argv[1], argv[2]);
		return 1;
	}

	KalmanModel model;
	model.setup(atof(argv[3]));

	char line[512];

	if(!fgets(line, sizeof(line), input))    // SEM CABECALHO, SEM DADOS
		return 1;

	fprintf(output, "time,roll,pitch,yaw,heave,heave_rate,heave_accel,wx,wy,wz,alpha_x,alpha_y,alpha_z,accel_n,accel_e,accel_d,period_x,period_y,period_z\n");

	double previous = NAN, busy = 0;
	long count = 0;

	while(fgets(line, sizeof(line), input)){
		double time, values[9];
		if(sscanf(line, "%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf", &time, &values[0], &values[1], &values[2], &values[3], &values[4], &values[5], &values[6], &values[7], &values[8]) != 10)
			continue;

		const KALMAN_REAL sensors[6] = {(KALMAN_REAL) values[0], (KALMAN_REAL) values[1], (KALMAN_REAL) values[2], (KALMAN_REAL) values[3], (KALMAN_REAL) values[4], (KALMAN_REAL) values[5]};
		const KALMAN_REAL angles[3]  = {(KALMAN_REAL) values[6], (KALMAN_REAL) values[7], (KALMAN_REAL) values[8]};
		const KALMAN_REAL dt         = std::isnan(previous) ? 0 : (KALMAN_REAL) (time - previous);
		previous = time;

		const auto begin = std::chrono::steady_clock::now();
		model.update(sensors, angles, dt);
		busy += std::chrono::duration<double, std::micro>(std::chrono::steady_clock::now() - begin).count();
		count++;

		const double out[18] = {model.roll, model.pitch, model.yaw, model.heave, model.heaveRate, model.heaveAccel, model.rate[0], model.rate[1], model.rate[2], model.alpha[0], model.alpha[1], model.alpha[2], model.accel[0], model.accel[1], model.accel[2], model.period[0], model.period[1], model.period[2]};
		fprintf(output, "%.6f", time);

		for(int k = 0; k < 18; k++)
			fprintf(output, ",%.17g", out[k]);

		fprintf(output, "\n");
	}

	fclose(input);
	fclose(output);
	printf("%.3f\n", count ? busy/count : 0.0);
	return 0;
}
