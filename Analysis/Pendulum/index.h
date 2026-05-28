#ifndef HEAVE_H
#define HEAVE_H

#include <math.h>

#ifndef DEG_TO_RAD
#define DEG_TO_RAD 0.017453292519943295f
#endif

class Biquad {
private:
    float b0, b1, b2, a1, a2, z1, z2;

public:
    Biquad() : b0(1), b1(0), b2(0), a1(0), a2(0), z1(0), z2(0) {}

    void set(float _b0, float _b1, float _b2, float _a1, float _a2) {
        b0 = _b0; b1 = _b1; b2 = _b2; a1 = _a1; a2 = _a2;
    }

    inline float process(float in) {
        float out = in * b0 + z1;
        z1 = in * b1 - a1 * out + z2;
        z2 = in * b2 - a2 * out;
        return out;
    }

    void reset() { z1 = z2 = 0; }
};

class LaplaceFilter {
private:
    Biquad stage[2];

public:
    void setup(float fs, float fc) {
        float wc = 2.0f * tanf(M_PI * fc / fs);
        float wc2 = wc * wc;
        
        float q[2] = {0.765367f, 1.847759f};
        for (int i = 0; i < 2; i++) {
            float d = 4.0f + 2.0f * q[i] * wc + wc2;
            stage[i].set(4.0f / d, -8.0f / d, 4.0f / d, (2.0f * wc2 - 8.0f) / d, (4.0f - 2.0f * q[i] * wc + wc2) / d);
        }
    }

    inline float process(float in) { return stage[1].process(stage[0].process(in)); }
    void reset() { stage[0].reset(); stage[1].reset(); }
};

class Heave {
private:
    LaplaceFilter accel_filter, vel_filter, pos_filter;
    float velocity = 0, position = 0, last_accel = 0, last_vel = 0, _dt;
    const float G = 9.80665f;

public:
    float value = 0;

    Heave(float dt = 0.01f, float fc = 0.05f) : _dt(dt) {
        float fs = 1.0f / dt;
        accel_filter.setup(fs, fc);
        vel_filter.setup(fs, fc);
        pos_filter.setup(fs, fc);
    }

    void update(float ax, float ay, float az, float pitch, float roll) {
        float p = pitch * DEG_TO_RAD;
        float r = roll * DEG_TO_RAD;

        float a_vert = (sinf(p) * ax) - (sinf(r) * cosf(p) * ay) - (cosf(r) * cosf(p) * az);
        float a_dyn = a_vert + G;

        float a_f = accel_filter.process(a_dyn);
        velocity += (a_f + last_accel) * 0.5f * _dt;
        last_accel = a_f;

        float v_f = vel_filter.process(velocity);
        position += (v_f + last_vel) * 0.5f * _dt;
        last_vel = v_f;

        value = pos_filter.process(position);
    }

    void reset() {
        velocity = position = last_accel = last_vel = value = 0;
        accel_filter.reset(); vel_filter.reset(); pos_filter.reset();
    }
};

#endif
