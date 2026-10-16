#ifndef CORRECTION_CONFIG_H
#define CORRECTION_CONFIG_H

// GERADO POR Calibration/2 - Correction/1 - Model.ipynb EM 16/10/2026
#define CORRECTION_T0 54.448f    // graus C de referencia do termo termico

static const float CORRECTION_M[2][3][3] = {
	{{0.98955804f, 0.13000589f, 0.00045352f}, {0.00063462f, -0.00849339f, 0.99764257f}, {0.12981775f, -0.98990654f, -0.00857929f}},    // acelerometro: linha = eixo do navio, coluna = eixo do Kernel
	{{0.98621125f, 0.12851017f, 0.00145039f}, {0.00997993f, -0.00800420f, 0.98205890f}, {0.12800558f, -0.97318002f, -0.00768652f}}     // giroscopio
};

static const float CORRECTION_C[2][3] = {{9.50862503e-02f, 2.03593656e-02f, -2.05440608e-04f}, {7.27234294e-03f, 6.86504931e-04f, 5.74786091e-03f}};    // vies em m/s^2 e graus/s
static const float CORRECTION_K[2][3] = {{0.00000000e+00f, 0.00000000e+00f, 0.00000000e+00f}, {0.00000000e+00f, 0.00000000e+00f, 0.00000000e+00f}};    // por graus C

#endif
