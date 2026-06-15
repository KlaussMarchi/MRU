#ifndef MRU_FUSION_H
#define MRU_FUSION_H

#include <cmath>
#include "esp_timer.h"

class MRUFusion{
  private:
    float q0, q1, q2, q3;
    float qm0, qm1, qm2, qm3;

    float betaMin = 0.00032693024568649024f;
    float betaMax = 0.019747285524989195f;
    float accelMin = 4.662600178397143f;
    float accelMax = 22.66454534254048f;
    float adaptRate = 27.97519429327775f;
    float beta = 0.0024281299479735565f;

    float hpCutoff = 0.12327990803946247f;
    float heaveGain = 0.72345060737447f;
    
    float velZ = 0.0f, velZ_prev = 0.0f, velZ_hp = 0.0f, velZ_hp_prev = 0.0f;
    float posZ = 0.0f, posZ_prev = 0.0f, posZ_hp = 0.0f, posZ_hp_prev = 0.0f;

    uint64_t lastTimeUs;
    bool initialized;

    float pitch = 0.0f;
    float roll = 0.0f;
    float yaw = 0.0f;
    float heave = 0.0f;

    void eulerToQuaternion(float r, float p, float y, float& qw, float& qx, float& qy, float& qz) {
        float cr = cosf(r * 0.5f);
        float sr = sinf(r * 0.5f);
        float cp = cosf(p * 0.5f);
        float sp = sinf(p * 0.5f);
        float cy = cosf(y * 0.5f);
        float sy = sinf(y * 0.5f);

        qw = cr * cp * cy + sr * sp * sy;
        qx = sr * cp * cy - cr * sp * sy;
        qy = cr * sp * cy + sr * cp * sy;
        qz = cr * cp * sy - sr * sp * cy;
    }

    void quaternionMultiply(float aw, float ax, float ay, float az,
                            float bw, float bx, float by, float bz,
                            float& rw, float& rx, float& ry, float& rz) {
        rw = aw * bw - ax * bx - ay * by - az * bz;
        rx = aw * bx + ax * bw + ay * bz - az * by;
        ry = aw * by - ax * bz + ay * bw + az * bx;
        rz = aw * bz + ax * by - ay * bx + az * bw;
    }

    void rotateVector(float vx, float vy, float vz, float qw, float qx, float qy, float qz, float& rx, float& ry, float& rz) {
        float tw, tx, ty, tz;
        quaternionMultiply(qw, qx, qy, qz, 0.0f, vx, vy, vz, tw, tx, ty, tz);
        quaternionMultiply(tw, tx, ty, tz, qw, -qx, -qy, -qz, tw, rx, ry, rz);
    }

    void computeAngles() {
        pitch = asinf(2.0f * (q0 * q2 - q1 * q3));
        roll = atan2f(2.0f * (q0 * q1 + q2 * q3), 1.0f - 2.0f * (q1 * q1 + q2 * q2));
        yaw = atan2f(2.0f * (q1 * q2 + q0 * q3), 1.0f - 2.0f * (q2 * q2 + q3 * q3));

        pitch *= 57.2957795131f;
        roll *= 57.2957795131f;
        yaw *= 57.2957795131f;
    }

    void highPassFilter(float input, float& prevInput, float& output, float& prevOutput, float dt) {
        float rc = 1.0f / (2.0f * M_PI * hpCutoff);
        float alpha = rc / (rc + dt);
        output = alpha * (prevOutput + input - prevInput);
        prevInput = input;
        prevOutput = output;
    }

public:
    MRUFusion() {
        q0 = 1.0f; q1 = 0.0f; q2 = 0.0f; q3 = 0.0f;
        initialized = false;

        float mRoll = 177.59264662073775f * (M_PI / 180.0f);
        float mPitch = 0.9334347884032834f * (M_PI / 180.0f);
        float mYaw = 0.5190293009816779f * (M_PI / 180.0f);
        eulerToQuaternion(mRoll, mPitch, mYaw, qm0, qm1, qm2, qm3);
    }

    void update(float ax, float ay, float az, float gx, float gy, float gz) {
        uint64_t currentTimeUs = esp_timer_get_time();
        
        if (!initialized) {
            lastTimeUs = currentTimeUs;
            initialized = true;
            return;
        }

        float dt = (currentTimeUs - lastTimeUs) / 1000000.0f;
        lastTimeUs = currentTimeUs;

        if (dt <= 0.0f) return;

        float rotAx, rotAy, rotAz;
        float rotGx, rotGy, rotGz;
        rotateVector(ax, ay, az, qm0, qm1, qm2, qm3, rotAx, rotAy, rotAz);
        rotateVector(gx, gy, gz, qm0, qm1, qm2, qm3, rotGx, rotGy, rotGz);

        float aNorm = sqrtf(rotAx * rotAx + rotAy * rotAy + rotAz * rotAz);
        if (aNorm > 0.0f) {
            float errG = fabsf(aNorm - 9.80665f);
            float targetBeta;
            if (errG < accelMin) targetBeta = betaMin;
            else if (errG > accelMax) targetBeta = betaMax;
            else {
                targetBeta = betaMin + (betaMax - betaMin) * ((errG - accelMin) / (accelMax - accelMin));
            }
            beta += (targetBeta - beta) * adaptRate * dt;

            float nx = rotAx / aNorm;
            float ny = rotAy / aNorm;
            float nz = rotAz / aNorm;

            float qDot1 = 0.5f * (-q1 * rotGx - q2 * rotGy - q3 * rotGz);
            float qDot2 = 0.5f * (q0 * rotGx + q2 * rotGz - q3 * rotGy);
            float qDot3 = 0.5f * (q0 * rotGy - q1 * rotGz + q3 * rotGx);
            float qDot4 = 0.5f * (q0 * rotGz + q1 * rotGy - q2 * rotGx);

            float s0 = -2.0f * q2 * (2.0f * (q1 * q3 - q0 * q2) - nx) + 2.0f * q1 * (2.0f * (q0 * q1 + q2 * q3) - ny);
            float s1 = 2.0f * q3 * (2.0f * (q1 * q3 - q0 * q2) - nx) + 2.0f * q0 * (2.0f * (q0 * q1 + q2 * q3) - ny) - 4.0f * q1 * (1.0f - 2.0f * (q1 * q1 + q2 * q2) - nz);
            float s2 = -2.0f * q0 * (2.0f * (q1 * q3 - q0 * q2) - nx) + 2.0f * q3 * (2.0f * (q0 * q1 + q2 * q3) - ny) - 4.0f * q2 * (1.0f - 2.0f * (q1 * q1 + q2 * q2) - nz);
            float s3 = 2.0f * q1 * (2.0f * (q1 * q3 - q0 * q2) - nx) + 2.0f * q2 * (2.0f * (q0 * q1 + q2 * q3) - ny);

            float sNorm = sqrtf(s0 * s0 + s1 * s1 + s2 * s2 + s3 * s3);
            if (sNorm > 0.0f) {
                s0 /= sNorm;
                s1 /= sNorm;
                s2 /= sNorm;
                s3 /= sNorm;
            }

            qDot1 -= beta * s0;
            qDot2 -= beta * s1;
            qDot3 -= beta * s2;
            qDot4 -= beta * s3;

            q0 += qDot1 * dt;
            q1 += qDot2 * dt;
            q2 += qDot3 * dt;
            q3 += qDot4 * dt;

            float qNorm = sqrtf(q0 * q0 + q1 * q1 + q2 * q2 + q3 * q3);
            q0 /= qNorm;
            q1 /= qNorm;
            q2 /= qNorm;
            q3 /= qNorm;
        }

        computeAngles();

        float awx, awy, awz;
        rotateVector(rotAx, rotAy, rotAz, q0, -q1, -q2, -q3, awx, awy, awz);
        float azLinear = awz - 9.80665f;

        velZ += azLinear * dt;
        highPassFilter(velZ, velZ_prev, velZ_hp, velZ_hp_prev, dt);

        posZ += velZ_hp * dt;
        highPassFilter(posZ, posZ_prev, posZ_hp, posZ_hp_prev, dt);

        heave = posZ_hp * heaveGain;
    }

    float getPitch() const { return pitch; }
    float getRoll() const { return roll; }
    float getYaw() const { return yaw; }
    float getHeave() const { return heave; }
};

#endif


/*
MRUFusion fusion;

void loop() {
    // ax, ay, az em m/s^2
    // gx, gy, gz em rad/s
    fusion.update(ax, ay, az, gx, gy, gz);
    
    float pitch = fusion.getPitch();
    float roll = fusion.getRoll();
    float yaw = fusion.getYaw();
    float heave = fusion.getHeave();
}
*/