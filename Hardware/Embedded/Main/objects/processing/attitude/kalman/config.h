#ifndef KALMAN_CONFIG_H
#define KALMAN_CONFIG_H

// GERADO POR Calibration/3 - Attitude/KalmanFusion/1 - Model.ipynb EM 15/10/2026
#define KALMAN_NAME        "kalman_fusion"
#define KALMAN_GRAVITY     9.785000f
#define KALMAN_GYRO_NOISE  5.13451773e-09f     // (rad/s)^2/Hz do ARW do giro
#define KALMAN_BIAS_NOISE  1.40933133e-13f     // (rad/s^2)^2/Hz do random walk do bias
#define KALMAN_ACCEL_NOISE 1.29655289e+00f    // variancia do versor do acelerometro
#define KALMAN_ZUPT_NOISE  4.81066615e-04f     // (rad/s)^2 do ZARU
#define KALMAN_ACCEL_GATE  1.68638902e-02f    // ganho que infla R quando |a| foge de g
#define KALMAN_GYRO_PHASE  0.528416f     // fase da taxa integrada: 0 retangular, 0.5 trapezoidal
#define KALMAN_HEADING     NAN    // proa inicial em graus; NAN pega a do sensor

static const float KALMAN_LEVER[3] = {2.97795191f, -2.02417821f, 0.10480773f};    // metros, do centro de rotacao ate o sensor, no corpo

#endif
