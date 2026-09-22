#ifndef KALMAN_CONFIG_H
#define KALMAN_CONFIG_H

// GERADO POR Calibration/Model/KalmanFusion/1 - Model.ipynb EM 22/09/2026
#define KALMAN_NAME        "kalman_fusion"
#define KALMAN_GRAVITY     9.810000f
#define KALMAN_GYRO_NOISE  6.17539440e-07f     // (rad/s)^2/Hz do ARW do giro
#define KALMAN_BIAS_NOISE  4.49112781e-13f     // (rad/s^2)^2/Hz do random walk do bias
#define KALMAN_ACCEL_NOISE 5.47798846e-03f    // variancia do versor do acelerometro
#define KALMAN_ZUPT_NOISE  2.98306286e-07f     // (rad/s)^2 do ZARU
#define KALMAN_ACCEL_GATE  3.34326119e+00f    // ganho que infla R quando |a| foge de g
#define KALMAN_GYRO_PHASE  0.388826f     // fase da taxa integrada: 0 retangular, 0.5 trapezoidal
#define KALMAN_ALIGN_X     -3.137605f      // graus, montagem do sensor no referencial da referencia
#define KALMAN_ALIGN_Y     9.122139f
#define KALMAN_ALIGN_Z     7.659612f
#define KALMAN_HEADING     NAN    // proa inicial em graus; NAN pega a do sensor

static const float KALMAN_LEVER[3] = {1.82529170f, -2.15272221f, 0.99109092f};    // metros, do centro de rotacao ate o sensor, no corpo

#endif
