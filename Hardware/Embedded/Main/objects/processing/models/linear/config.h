#ifndef LINEAR_CONFIG_H
#define LINEAR_CONFIG_H

// GERADO POR Calibration/Model/LinearFit/1 - Model.ipynb EM 22/09/2026
#define LINEAR_NAME "linear_fit"

static const float LINEAR_M[3][3] = {
	{0.06479649f, 0.00000000f, 0.00000000f},
	{0.00000000f, 1.00494025f, 0.00000000f},
	{0.00000000f, 0.00000000f, 0.53541830f}
};    // linha = angulo calibrado, coluna = angulo do sensor: pitch, roll, yaw

static const float LINEAR_B[3] = {0.50969706f, -89.29141042f, 1.46362145f};

#endif
