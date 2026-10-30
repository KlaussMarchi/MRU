#ifndef FILTERS_CONFIG_H
#define FILTERS_CONFIG_H

// GERADO POR Calibration/1 - Filters/1 - Model.ipynb EM 30/10/2026
static const int FILTERS_TYPE[6] = {FILTER_EXPONENTIAL, FILTER_EXPONENTIAL, FILTER_EXPONENTIAL, FILTER_EXPONENTIAL, FILTER_EXPONENTIAL, FILTER_EXPONENTIAL};    // ax, ay, az, wx, wy, wz
static const float FILTERS_FC[6] = {0.314954f, 1.246260f, 3.206470f, 9.136920f, 4.080781f, 1.057796f};    // Hz: -3 dB no butterworth, polo no low_pass, 1/(2 pi tau) na exponencial

#endif
