#ifndef FILTERS_CONFIG_H
#define FILTERS_CONFIG_H

// GERADO POR Calibration/1 - Filters/1 - Model.ipynb EM 15/10/2026
static const int FILTERS_TYPE[6] = {FILTER_EXPONENTIAL, FILTER_EXPONENTIAL, FILTER_EXPONENTIAL, FILTER_EXPONENTIAL, FILTER_EXPONENTIAL, FILTER_EXPONENTIAL};    // ax, ay, az, wx, wy, wz
static const float FILTERS_FC[6] = {0.314952f, 1.246259f, 3.206469f, 9.136918f, 4.080783f, 1.057796f};    // Hz: -3 dB no butterworth, polo no low_pass, 1/(2 pi tau) na exponencial

#endif
