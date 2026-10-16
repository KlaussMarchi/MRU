#ifndef ALIGN_CONFIG_H
#define ALIGN_CONFIG_H

// GERADO POR Calibration/2 - Correction/1 - Model.ipynb EM 16/10/2026
static const float ALIGN_CALIBRATION[3] = {NAN, NAN, NAN};    // proa, pitch e roll do Kernel no ensaio; NAN desliga a rotacao
static const float ALIGN_FRAME[3][3]    = {{1.00000000f, 0.00000000f, 0.00000000f}, {0.00000000f, 0.00000000f, 1.00000000f}, {0.00000000f, -1.00000000f, 0.00000000f}};    // eixos do navio do ensaio nos eixos do Kernel: a montagem arredondada

#endif
