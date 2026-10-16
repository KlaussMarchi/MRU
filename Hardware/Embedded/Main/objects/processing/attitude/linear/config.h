#ifndef LINEAR_CONFIG_H
#define LINEAR_CONFIG_H

// GERADO POR Calibration/3 - Attitude/LinearFit/1 - Model.ipynb EM 15/10/2026
#define LINEAR_NAME "linear_fit"

static const float LINEAR_M[3][3] = {
	{-0.00922058f, 0.00000000f, 0.00000000f},
	{0.00000000f, 6.84705448f, 0.00000000f},
	{0.00000000f, 0.00000000f, 0.53541830f}
};    // linha = angulo calibrado, coluna = angulo do sensor: pitch, roll, yaw

static const float LINEAR_B[3] = {0.58386718f, -81.53761347f, 1.46362145f};

#endif
