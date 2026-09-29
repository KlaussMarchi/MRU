#ifndef KALMAN_CONFIG_H
#define KALMAN_CONFIG_H

// GERADO POR Calibration/Model/KalmanFusion/1 - Model.ipynb EM 23/09/2026
#define KALMAN_NAME        "kalman_fusion"
#define KALMAN_GRAVITY     9.810000f
#define KALMAN_GYRO_NOISE  5.00935029e-11f     // (rad/s)^2/Hz do ARW do giro
#define KALMAN_BIAS_NOISE  1.17036483e-16f     // (rad/s^2)^2/Hz do random walk do bias
#define KALMAN_ACCEL_NOISE 1.42503448e+00f    // variancia do versor do acelerometro
#define KALMAN_ZUPT_NOISE  4.10093038e+00f     // (rad/s)^2 do ZARU
#define KALMAN_ACCEL_GATE  1.71964605e-02f    // ganho que infla R quando |a| foge de g
#define KALMAN_GYRO_PHASE  0.615972f     // fase da taxa integrada: 0 retangular, 0.5 trapezoidal
#define KALMAN_ALIGN_X     -4.804582f      // graus, montagem do sensor no referencial da referencia
#define KALMAN_ALIGN_Y     -8.568605f
#define KALMAN_ALIGN_Z     0.098969f
#define KALMAN_HEADING     NAN    // proa inicial em graus; NAN pega a do sensor

static const float KALMAN_LEVER[3] = {-1.80791994f, -1.12898124f, -0.91107663f};    // metros, do centro de rotacao ate o sensor, no corpo

#endif
