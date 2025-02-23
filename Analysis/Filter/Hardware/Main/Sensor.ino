
struct Kalman {
    float A[2][2];
    float B[2][1];
    float H[2][2];
    float Q[2][2];
    float R[2][2];
    float P[2][2];
    float x[2][1];

    void predict(float u[1][1]){
        float tempX[2][1];
        matrixVectorMultiply(A, x, tempX);

        for(int i = 0; i < 2; i++)
            x[i][0] = tempX[i][0] + B[i][0] * u[0][0];

        float tempP[2][2];
        float AT[2][2] = {{A[0][0], A[1][0]}, {A[0][1], A[1][1]}};

        matrixMultiply(A, P, tempP);
        matrixMultiply(tempP, AT, P);

        for(int i = 0; i < 2; i++)
            for (int j = 0; j < 2; j++)
                P[i][j] += Q[i][j];
    }

    void update(float z[2][1]){
        float hx[2][1];
        matrixVectorMultiply(H, x, hx);
        float y[2][1];

        for(int i = 0; i < 2; i++)
            y[i][0] = z[i][0] - hx[i][0];

        float tempS[2][2];
        float HT[2][2] = {{H[0][0], H[1][0]}, {H[0][1], H[1][1]}};
        float S[2][2];

        matrixMultiply(H, P, tempS);
        matrixMultiply(tempS, HT, S);

        for(int i = 0; i < 2; i++)
            for (int j = 0; j < 2; j++) 
                S[i][j] += R[i][j];

        float K[2][2];
        float S_inv[2][2] = {{1.0 / S[0][0], 0.0}, {0.0, 1.0 / S[1][1]}};
        float tempK[2][2];

        matrixMultiply(P, HT, tempK);
        matrixMultiply(tempK, S_inv, K);

        float Ky[2][1];
        matrixVectorMultiply(K, y, Ky);

        for(int i = 0; i < 2; i++)
            x[i][0] += Ky[i][0];

        float KH[2][2];
        matrixMultiply(K, H, KH);
        float I[2][2] = {{1.0, 0.0}, {0.0, 1.0}};

        for(int i = 0; i < 2; i++)
            for (int j = 0; j < 2; j++) 
                KH[i][j] = I[i][j] - KH[i][j];
            
        
        float tempP[2][2];
        matrixMultiply(KH, P, tempP);

        for(int i = 0; i < 2; i++)
            for(int j = 0; j < 2; j++)
                P[i][j] = tempP[i][j];
    }

    float getState(int index) {
        return x[index][0];
    }
};

Kalman kalman;

void kalmanSetup(){
    kalman.A[0][0] = 1.0; kalman.A[0][1] = 0.01996;
    kalman.A[1][0] = 0.0; kalman.A[1][1] = 1.0;

    kalman.B[0][0] = 0.0001992;
    kalman.B[1][0] = 0.01996;

    kalman.H[0][0] = 1.0; kalman.H[0][1] = 0.0;
    kalman.H[1][0] = 0.0; kalman.H[1][1] = 1.0;

    kalman.Q[0][0] = 0.01; kalman.Q[0][1] = 0.0;
    kalman.Q[1][0] = 0.0;  kalman.Q[1][1] = 0.01;

    kalman.R[0][0] = 0.01; kalman.R[0][1] = 0.0;
    kalman.R[1][0] = 0.0;  kalman.R[1][1] = 0.01;

    kalman.P[0][0] = 1.0;  kalman.P[0][1] = 0.0;
    kalman.P[1][0] = 0.0;  kalman.P[1][1] = 1.0;

    kalman.x[0][0] = 0.0;
    kalman.x[1][0] = 0.0;
}

void handleVelocity(){
    static unsigned long startTime = millis();

    if(millis() - startTime < 20)
        return;

    const float dt = (millis() - startTime) / 1000.0;
    startTime = millis();

    static float v = 0.0;
    static float x = 0.0;

    float t = (millis() - startProg)/1000.00;
    float a = 5.0*sin(0.5*t);
    v = v + a * dt;
    x = x + v * dt + (a * dt * dt * 2) / 2;

    float U[1][1] = {{a}};
    float Z[2][1] = {{x}, {v}};

    kalman.predict(U);
    kalman.update(Z);

    const float x_f = kalman.getState(0);
    const float v_f = kalman.getState(1);
    plot(v_f, 500);
}

void matrixMultiply(float a[2][2], float b[2][2], float result[2][2]) {
    for(int i = 0; i < 2; i++)
        for(int j = 0; j < 2; j++){
            result[i][j] = 0.0;

            for(int k = 0; k < 2; k++)
                result[i][j] += a[i][k] * b[k][j];
        }
}

void matrixVectorMultiply(float a[2][2], float b[2][1], float result[2][1]){
    for(int i = 0; i < 2; i++){
        result[i][0] = 0.0;
        
        for (int j = 0; j < 2; j++)
            result[i][0] += a[i][j] * b[j][0];
    }
}

void predictFuture(int steps, float u[1][1], float futureStates[][2]) {
    float originalX[2][1] = {{kalman.x[0][0]}, {kalman.x[1][0]}};
    float originalP[2][2] = {{kalman.P[0][0], kalman.P[0][1]},
                             {kalman.P[1][0], kalman.P[1][1]}};

    for (int i=0; i<steps; i++){
        kalman.predict(u); // Predição baseada no modelo interno
        futureStates[i][0] = kalman.x[0][0]; // Posição futura
        futureStates[i][1] = kalman.x[1][0]; // Velocidade futura
    }

    // Restaura o estado original
    kalman.x[0][0] = originalX[0][0];
    kalman.x[1][0] = originalX[1][0];
    kalman.P[0][0] = originalP[0][0];
    kalman.P[0][1] = originalP[0][1];
    kalman.P[1][0] = originalP[1][0];
    kalman.P[1][1] = originalP[1][1];
}
