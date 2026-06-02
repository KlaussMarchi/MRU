#pragma once
#include <cmath>
#include <cstdint>
#include "esp_timer.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/**
 * Filtro de Madgwick para fusão IMU (gyro + accel).
 * Porta direta do Python — lógica idêntica, resultados idênticos.
 *
 * Uso típico:
 *   OrientationParser parser;
 *   parser.start(ax0, ay0, az0);           // uma vez, com a 1ª leitura
 *
 *   // no loop:
 *   parser.update(gx, gy, gz, ax, ay, az); // gx/gy/gz em rad/s, ax/ay/az em m/s²
 *   float pitch = parser.pitch;
 *   float roll  = parser.roll;
 *   float yaw   = parser.yaw;
 */
class OrientationParser {
public:
    float beta      = 0.01f;   // ganho de correção do acelerômetro
    float accel_min = 0.5f;    // norma mínima do accel (evita div/0)
    float accel_max = 19.6f;   // norma máxima (~2g); rejeita vibração intensa
    float dt_min    = 1e-6f;   // clamp inferior de dt (s)
    float dt_max    = 0.15f;   // clamp superior de dt (s)

    // ── Estado do quaternion ───────────────────────────────────────────
    float q0 = 1.0f, q1 = 0.0f, q2 = 0.0f, q3 = 0.0f;

    // ── Ângulos de Euler resultantes (graus) ───────────────────────────
    float yaw   = 0.0f;
    float pitch = 0.0f;
    float roll  = 0.0f;

    bool initialized = false;

    // ------------------------------------------------------------------
    // Construtor com parâmetros opcionais (mesma assinatura do Python)
    // ------------------------------------------------------------------
    OrientationParser(float beta=0.01f, float accel_min=0.5f, float accel_max=19.6f, float dt_min=1e-6f, float dt_max=0.15f): 
        beta(beta), 
        accel_min(accel_min), 
        accel_max(accel_max),
        dt_min(dt_min), 
        dt_max(dt_max){
            _prev_us = esp_timer_get_time();
        }
    
    void start(float ax, float ay, float az) {
        float norm = sqrtf(ax*ax + ay*ay + az*az);
        if (norm < accel_min) return;   // leitura inválida

        ax /= norm; ay /= norm; az /= norm;

        if (az >= 0.0f) {
            float denom = sqrtf(2.0f * (az + 1.0f));
            if (denom < 1e-10f) return;
            q0 =  denom / 2.0f;
            q1 =  ay / denom;
            q2 = -ax / denom;
            q3 =  0.0f;
        } 
        else {
            float denom = sqrtf(2.0f * (1.0f - az));
            if (denom < 1e-10f) return;
            q0 =  ay / denom;
            q1 =  denom / 2.0f;
            q2 =  0.0f;
            q3 =  ax / denom;
        }

        float rn = _recipnorm4(q0, q1, q2, q3);
        if (rn > 0.0f) { q0 *= rn; q1 *= rn; q2 *= rn; q3 *= rn; }

        // Reseta o timer para que o 1º update() tenha dt limpo
        _prev_us    = esp_timer_get_time();
        initialized = true;
    }

    // ------------------------------------------------------------------
    // update() com dt automático via esp_timer_get_time()
    // gx/gy/gz : rad/s   |   ax/ay/az : m/s² (ou qualquer unidade — normalizado)
    // ------------------------------------------------------------------
    void update(float gx, float gy, float gz, float ax, float ay, float az){
        int64_t now_us = esp_timer_get_time();
        float dt = (now_us - _prev_us) * 1e-6f;   // µs → s
        _prev_us = now_us;
        _update_internal(gx, gy, gz, ax, ay, az, dt);
    }

    // ------------------------------------------------------------------
    // update() com dt explícito (compatível com o código Python original)
    // ------------------------------------------------------------------
    void update(float gx, float gy, float gz,
                float ax, float ay, float az,
                float dt)
    {
        _update_internal(gx, gy, gz, ax, ay, az, dt);
        _prev_us = esp_timer_get_time();   // carimba APÓS o update, não antes
    }

private:
    int64_t _prev_us = 0;

    void _update_internal(float gx, float gy, float gz, float ax, float ay, float az, float dt){
        // 1. Clamp de dt
        if (dt < dt_min) dt = dt_min;
        if (dt > dt_max) dt = dt_max;

        float _q0 = q0, _q1 = q1, _q2 = q2, _q3 = q3;

        // 2. Derivada pelo giroscópio
        float qDot1 = 0.5f * (-_q1*gx - _q2*gy - _q3*gz);
        float qDot2 = 0.5f * ( _q0*gx + _q2*gz - _q3*gy);
        float qDot3 = 0.5f * ( _q0*gy - _q1*gz + _q3*gx);
        float qDot4 = 0.5f * ( _q0*gz + _q1*gy - _q2*gx);

        // 3. Correção pelo acelerômetro (gradient descent de Madgwick)
        float accel_norm = sqrtf(ax*ax + ay*ay + az*az);

        if (accel_norm > accel_min && accel_norm < accel_max) {
            float inv = 1.0f / accel_norm;
            ax *= inv; ay *= inv; az *= inv;

            float q0q0 = _q0*_q0, q1q1 = _q1*_q1;
            float q2q2 = _q2*_q2, q3q3 = _q3*_q3;
            float _4q0 = 4.0f*_q0, _4q1 = 4.0f*_q1, _4q2 = 4.0f*_q2;
            float _8q1 = 8.0f*_q1, _8q2 = 8.0f*_q2;

            float s0 = _4q0*q2q2 + 2.0f*_q2*ax + _4q0*q1q1 - 2.0f*_q1*ay;
            float s1 = (_4q1*q3q3 - 2.0f*_q3*ax
                        + 4.0f*q0q0*_q1 - 2.0f*_q0*ay
                        - _4q1 + _8q1*q1q1 + _8q1*q2q2 + _4q1*az);
            float s2 = (4.0f*q0q0*_q2 + 2.0f*_q0*ax
                        + _4q2*q3q3 - 2.0f*_q3*ay
                        - _4q2 + _8q2*q1q1 + _8q2*q2q2 + _4q2*az);
            float s3 = 4.0f*q1q1*_q3 - 2.0f*_q1*ax + 4.0f*q2q2*_q3 - 2.0f*_q2*ay;

            float rn = _recipnorm4(s0, s1, s2, s3);
            if (rn > 0.0f) {
                qDot1 -= beta * s0 * rn;
                qDot2 -= beta * s1 * rn;
                qDot3 -= beta * s2 * rn;
                qDot4 -= beta * s3 * rn;
            }
        }

        // 4. Integração de Euler de 1ª ordem
        _q0 += qDot1 * dt;
        _q1 += qDot2 * dt;
        _q2 += qDot3 * dt;
        _q3 += qDot4 * dt;

        // 5. Renormaliza — se degenerar, reinicia para identidade
        float rn = _recipnorm4(_q0, _q1, _q2, _q3);
        if (rn <= 0.0f) {
            q0 = 1.0f; q1 = 0.0f; q2 = 0.0f; q3 = 0.0f;
            return;
        }
        q0 = _q0 * rn;
        q1 = _q1 * rn;
        q2 = _q2 * rn;
        q3 = _q3 * rn;

        _compute_euler();
    }

    void _compute_euler() {
        // Yaw — denominador usa q1²+q2²  (igual ao Python)
        yaw = atan2f(
            2.0f*(q1*q2 - q0*q3),
            1.0f - 2.0f*(q1*q1 + q2*q2)
        ) * (180.0f / M_PI);

        // Pitch — clamp antes do asin (evita NaN por ruído de float)
        float sinp = 2.0f*(q2*q3 + q0*q1);
        if (sinp >  1.0f) sinp =  1.0f;
        if (sinp < -1.0f) sinp = -1.0f;
        pitch = asinf(sinp) * (180.0f / M_PI);

        // Roll — negado para convenção NED  (igual ao Python)
        roll = -atan2f(
            2.0f*(q1*q3 - q0*q2),
            1.0f - 2.0f*(q1*q1 + q2*q2)
        ) * (180.0f / M_PI);
    }

    // Retorna 1/‖v‖ ou 0.0 se ‖v‖ < 1e-10  (0.0 = sinal de falha)
    static float _recipnorm4(float a, float b, float c, float d) {
        float n = a*a + b*b + c*c + d*d;
        if (n < 1e-10f) return 0.0f;
        return 1.0f / sqrtf(n);
    }
};