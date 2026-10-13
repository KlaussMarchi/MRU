#ifndef KALMAN_CONFIG_H
#define KALMAN_CONFIG_H

// GERADO POR KalmanFusion/1 - Model.ipynb EM 08/10/2026 (Backup/model_4)
#define KALMAN_NAME          "kalman_fusion"
#define KALMAN_G0            9.8066499999999994    // m/s^2 por g: o modo HR do Kernel entrega aceleracao em g
#define KALMAN_GRAVITY       9.7875777588796389    // m/s^2, gravidade local, centro do gate e do detector de repouso
#define KALMAN_GYRO_NOISE    3.551820601863024e-07    // (rad/s)^2/Hz do ARW do giro
#define KALMAN_BIAS_NOISE    7.6820777015673699e-13    // (rad/s^2)^2/Hz do random walk do bias
#define KALMAN_ACCEL_NOISE   4.8579054066101561e-05    // variancia do versor do acelerometro em movimento
#define KALMAN_STILL_NOISE   5.4991170224700996e-06    // variancia do versor do acelerometro parado: o ruido do sensor
#define KALMAN_ZUPT_NOISE    1.5998144533309354e-05    // (rad/s)^2 do ZARU
#define KALMAN_ACCEL_GATE    0.6330022829950519    // ganho que infla R quando |a| foge de g
#define KALMAN_RATE_NOISE    1.5998144533309354e-05    // (rad/s)^2 da taxa medida nos osciladores
#define KALMAN_GYRO_PHASE    0.49745694095314436    // fase da taxa integrada: 0 retangular, 0.5 trapezoidal
#define KALMAN_SPIKE         2    // m/s^2, salto isolado da aceleracao do CG que e pico
#define KALMAN_HEAVE_PERIOD  1.3    // s, Th da EP 2 092 402: wc = 2 pi / (10 Th)
#define KALMAN_HEAVE_DAMPING 0.69999999999999996    // eps dos filtros GP e HS
#define KALMAN_ALIGN_X       90.529222113133713    // graus, eixos crus do Kernel -> referencial do navio (Euler xyz)
#define KALMAN_ALIGN_Y       0.36914598526831666
#define KALMAN_ALIGN_Z       7.544073086094893
#define KALMAN_HEADING       NAN    // proa inicial em graus; NAN pega a do Kernel

static const double KALMAN_LEVER[3] = {0.041805949868863081, -1.9102454204189605, 0.059286939148420197};    // m, do centro de rotacao (CG) ate o Kernel, no corpo
static const double KALMAN_POINT[3] = {0.067793110893903524, -1.9747174817715103, -0.17189415054485871};    // m, do CG ate o ponto de medida do heave, no corpo

#endif
