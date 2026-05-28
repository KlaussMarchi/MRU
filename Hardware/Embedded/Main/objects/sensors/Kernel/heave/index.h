#ifndef HEAVE_H
#define HEAVE_H

#include <cmath>

#ifndef M_PI
#define M_PI 3.14159265358979323846f
#endif

class Heave {
private:
    float hpAccel;
    float prevAccel;
    float velocity;
    float position;
    
    float omegaN;
    float zeta;
    float tauHP;
    bool initialized;

public:
    Heave(float cutoffPeriod = 30.0f, float hpCutoffFreq = 0.01f) {
        hpAccel = 0.0f;
        prevAccel = 0.0f;
        velocity = 0.0f;
        position = 0.0f;
        initialized = false;

        float fcIntegrator = 1.0f / cutoffPeriod;
        omegaN = 2.0f * M_PI * fcIntegrator;
        zeta = 0.70710678f; 
        tauHP = 1.0f / (2.0f * M_PI * hpCutoffFreq);
    }

    void update(float ax, float ay, float az, float pitch, float roll, float dt) {
        if (dt <= 0.0f) return;

        float pitchRad = pitch * (M_PI / 180.0f);
        float rollRad  = roll  * (M_PI / 180.0f);

        float sinPitch = std::sin(pitchRad);
        float cosPitch = std::cos(pitchRad);
        float sinRoll  = std::sin(rollRad);
        float cosRoll  = std::cos(rollRad);

        float azGlobal = -ax * sinPitch + ay * cosPitch * sinRoll + az * cosPitch * cosRoll;
        float azMs2 = azGlobal * 9.80665f; 

        if (!initialized) {
            prevAccel = azMs2;
            initialized = true;
        }

        float alpha = tauHP / (tauHP + dt);
        hpAccel = alpha * hpAccel + alpha * (azMs2 - prevAccel);
        prevAccel = azMs2;

        float accelDamped = hpAccel - 2.0f * zeta * omegaN * velocity - omegaN * omegaN * position;
        
        velocity += accelDamped * dt;
        position += velocity * dt;
    }

    float getHeave() const {
        return position;
    }
};

#endif
