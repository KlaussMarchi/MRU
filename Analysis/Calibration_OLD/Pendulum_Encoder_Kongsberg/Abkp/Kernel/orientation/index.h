#ifndef ORIENTATION_PARSER_H
#define ORIENTATION_PARSER_H

#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846f
#endif

/*
 * =================================================================================
 * OrientarionParser: Integração Dinâmica Off-Board (Madgwick AHRS C++ Otimizado)
 * =================================================================================
 * Resolve o Gimbal Lock (Singularidade de Euler) operando 100% via Quaternions.
 * Resolve a distorção cinética ("barriguinha") operando com ganho (beta) baixo,
 * fazendo com que o filtro confie na integração do giroscópio e rejeite as
 * acelerações tangenciais do pêndulo.
 */
class OrientationParser {
private:
    float q0, q1, q2, q3; // Quaternions de atitude
    float beta;           // Ganho do filtro

public:
    // Beta configurado para altíssima imunidade a distorção cinética
    OrientationParser(float b = 0.01f) {
        q0 = 1.0f; 
        q1 = 0.0f; 
        q2 = 0.0f; 
        q3 = 0.0f;
        beta = b;
    }

    // Espera Gyro em rad/s e Accel em 'g'. dt em segundos.
    void update(float gx, float gy, float gz, float ax, float ay, float az, float dt) {
        float recipNorm;
        float s0, s1, s2, s3;
        float qDot1, qDot2, qDot3, qDot4;
        float _2q0, _2q1, _2q2, _2q3, _4q0, _4q1, _4q2, _8q1, _8q2, q0q0, q1q1, q2q2, q3q3;

        // Taxa de variação do quaternion lida pelo giroscópio
        qDot1 = 0.5f * (-q1 * gx - q2 * gy - q3 * gz);
        qDot2 = 0.5f * (q0 * gx + q2 * gz - q3 * gy);
        qDot3 = 0.5f * (q0 * gy - q1 * gz + q3 * gx);
        qDot4 = 0.5f * (q0 * gz + q1 * gy - q2 * gx);

        // O passo corretivo do acelerômetro só ocorre se os dados forem válidos (evita NaN)
        if(!((ax == 0.0f) && (ay == 0.0f) && (az == 0.0f))) {
            // Normaliza medição do acelerômetro
            recipNorm = 1.0f / std::sqrt(ax * ax + ay * ay + az * az);
            ax *= recipNorm;
            ay *= recipNorm;
            az *= recipNorm;

            // Variáveis auxiliares para evitar aritmética repetida na GPU/CPU
            _2q0 = 2.0f * q0;
            _2q1 = 2.0f * q1;
            _2q2 = 2.0f * q2;
            _2q3 = 2.0f * q3;
            _4q0 = 4.0f * q0;
            _4q1 = 4.0f * q1;
            _4q2 = 4.0f * q2;
            _8q1 = 8.0f * q1;
            _8q2 = 8.0f * q2;
            q0q0 = q0 * q0;
            q1q1 = q1 * q1;
            q2q2 = q2 * q2;
            q3q3 = q3 * q3;

            // Algoritmo de descida de gradiente (Gradient descent)
            s0 = _4q0 * q2q2 + _2q2 * ax + _4q0 * q1q1 - _2q1 * ay;
            s1 = _4q1 * q3q3 - _2q3 * ax + 4.0f * q0q0 * q1 - _2q0 * ay - _4q1 + _8q1 * q1q1 + _8q1 * q2q2 + _4q1 * az;
            s2 = 4.0f * q0q0 * q2 + _2q0 * ax + _4q2 * q3q3 - _2q3 * ay - _4q2 + _8q2 * q1q1 + _8q2 * q2q2 + _4q2 * az;
            s3 = 4.0f * q1q1 * q3 - _2q1 * ax + 4.0f * q2q2 * q3 - _2q2 * ay;
            
            // Normaliza o gradiente corretivo
            recipNorm = 1.0f / std::sqrt(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3);
            s0 *= recipNorm;
            s1 *= recipNorm;
            s2 *= recipNorm;
            s3 *= recipNorm;

            // Subtrai o gradiente ponderado por Beta para limpar distorção do acelerômetro
            qDot1 -= beta * s0;
            qDot2 -= beta * s1;
            qDot3 -= beta * s2;
            qDot4 -= beta * s3;
        }

        // Integração no tempo (Runge-Kutta de 1ª ordem)
        q0 += qDot1 * dt;
        q1 += qDot2 * dt;
        q2 += qDot3 * dt;
        q3 += qDot4 * dt;

        // Normaliza o quaternion resultante
        recipNorm = 1.0f / std::sqrt(q0 * q0 + q1 * q1 + q2 * q2 + q3 * q3);
        q0 *= recipNorm;
        q1 *= recipNorm;
        q2 *= recipNorm;
        q3 *= recipNorm;
    }

    float getYaw() {
        return std::atan2(2.0f * (q1 * q2 - q0 * q3), 1.0f - 2.0f * (q1 * q1 + q3 * q3)) * (180.0f / M_PI);
    }

    float getPitch() {
        float sinp = 2.0f * (q2 * q3 + q0 * q1);
        if (sinp > 1.0f) sinp = 1.0f;
        if (sinp < -1.0f) sinp = -1.0f;
        return std::asin(sinp) * (180.0f / M_PI);
    }

    float getRoll() {
        return -std::atan2(2.0f * (q1 * q3 - q0 * q2), 1.0f - 2.0f * (q1 * q1 + q2 * q2)) * (180.0f / M_PI);
    }
};

#endif