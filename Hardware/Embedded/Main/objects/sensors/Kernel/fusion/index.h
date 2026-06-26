#ifndef FUSION_H
#define FUSION_H

#include <math.h>
#include "esp_timer.h"

/*
 * Madgwick 6-DOF AHRS — bit-exact port of Fusion/Fusion.py.
 * State is a quaternion (q0,q1,q2,q3) = (w,x,y,z).
 * All math is single-precision float to match ESP32 hardware FP semantics.
 */
class Fusion {
public:
    float beta;
    float q0, q1, q2, q3;
    float pitch, roll, yaw;
    float gyroBiasX, gyroBiasY, gyroBiasZ;
    int64_t prevTimestampUs;
    bool initialized;

    Fusion() {
        beta = 0.1f;
        q0 = 1.0f; q1 = 0.0f; q2 = 0.0f; q3 = 0.0f;
        pitch = 0.0f; roll = 0.0f; yaw = 0.0f;
        gyroBiasX = 0.0f; gyroBiasY = 0.0f; gyroBiasZ = 0.0f;
        prevTimestampUs = 0;
        initialized = false;
    }

    void begin(float b) {
        beta = b;
        q0 = 1.0f; q1 = 0.0f; q2 = 0.0f; q3 = 0.0f;
        pitch = 0.0f; roll = 0.0f; yaw = 0.0f;
        gyroBiasX = 0.0f; gyroBiasY = 0.0f; gyroBiasZ = 0.0f;
        prevTimestampUs = 0;
        initialized = false;
    }

    void reset() {
        q0 = 1.0f; q1 = 0.0f; q2 = 0.0f; q3 = 0.0f;
        pitch = 0.0f; roll = 0.0f; yaw = 0.0f;
        prevTimestampUs = 0;
        initialized = false;
    }

    void setGyroBias(float bx, float by, float bz) {
        gyroBiasX = bx; gyroBiasY = by; gyroBiasZ = bz;
    }

    void update(float ax, float ay, float az,
                float wx, float wy, float wz) {
        int64_t nowUs = esp_timer_get_time();
        if (!initialized) {
            prevTimestampUs = nowUs;
            initialized = true;
            return;
        }

        float dt = (float)(nowUs - prevTimestampUs) / 1000000.0f;
        prevTimestampUs = nowUs;
        if (dt <= 0.0f) return;

        // Remove estimated gyro bias
        wx -= gyroBiasX;
        wy -= gyroBiasY;
        wz -= gyroBiasZ;

        // Normalize accelerometer
        float normA = sqrtf(ax * ax + ay * ay + az * az);
        if (normA < 1e-9f) return;
        float invA = 1.0f / normA;
        ax *= invA; ay *= invA; az *= invA;

        float q0 = this->q0;
        float q1 = this->q1;
        float q2 = this->q2;
        float q3 = this->q3;

        // Quaternion derivative from gyro
        float qDot0 = 0.5f * (-q1 * wx - q2 * wy - q3 * wz);
        float qDot1 = 0.5f * ( q0 * wx + q2 * wz - q3 * wy);
        float qDot2 = 0.5f * ( q0 * wy - q1 * wz + q3 * wx);
        float qDot3 = 0.5f * ( q0 * wz + q1 * wy - q2 * wx);

        // Objective function
        float f1 = 2.0f * (q1 * q3 - q0 * q2) - ax;
        float f2 = 2.0f * (q0 * q1 + q2 * q3) - ay;
        float f3 = (q0 * q0 - q1 * q1 - q2 * q2 + q3 * q3) - az;

        // Gradient = J^T * f
        float s0 = (-2.0f * q2) * f1 + ( 2.0f * q1) * f2 + ( 2.0f * q0) * f3;
        float s1 = ( 2.0f * q3) * f1 + ( 2.0f * q0) * f2 + (-2.0f * q1) * f3;
        float s2 = (-2.0f * q0) * f1 + ( 2.0f * q3) * f2 + (-2.0f * q2) * f3;
        float s3 = ( 2.0f * q1) * f1 + ( 2.0f * q2) * f2 + ( 2.0f * q3) * f3;

        float normS = sqrtf(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3);
        if (normS > 1e-12f) {
            float invS = 1.0f / normS;
            s0 *= invS; s1 *= invS; s2 *= invS; s3 *= invS;
        }

        // Apply feedback
        qDot0 -= beta * s0;
        qDot1 -= beta * s1;
        qDot2 -= beta * s2;
        qDot3 -= beta * s3;

        // Integrate
        q0 += qDot0 * dt;
        q1 += qDot1 * dt;
        q2 += qDot2 * dt;
        q3 += qDot3 * dt;

        // Normalize quaternion
        float normQ = sqrtf(q0 * q0 + q1 * q1 + q2 * q2 + q3 * q3);
        if (normQ > 1e-12f) {
            float invQ = 1.0f / normQ;
            q0 *= invQ; q1 *= invQ; q2 *= invQ; q3 *= invQ;
        }

        this->q0 = q0;
        this->q1 = q1;
        this->q2 = q2;
        this->q3 = q3;

        // Euler extraction
        float sinp = 2.0f * (q0 * q2 - q1 * q3);
        if (sinp > 1.0f) sinp = 1.0f;
        else if (sinp < -1.0f) sinp = -1.0f;

        roll  = atan2f(2.0f * (q0 * q1 + q2 * q3),
                       1.0f - 2.0f * (q1 * q1 + q2 * q2));
        pitch = asinf(sinp);
        yaw   = atan2f(2.0f * (q0 * q3 + q1 * q2),
                       1.0f - 2.0f * (q2 * q2 + q3 * q3));
    }

    void getQuaternion(float &w, float &x, float &y, float &z) const {
        w = q0; x = q1; y = q2; z = q3;
    }
};

#endif // FUSION_H