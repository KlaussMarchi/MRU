#ifndef HEAVE_H
#define HEAVE_H

#include <math.h>

class Heave {
private:
    uint64_t lastTime;
    
    // Optimal parameters discovered by optimizer.py
    const float fc = 0.24420023692169276f;
    const float zeta = 0.7797975651763583f;
    const float px = 0.3560817875722976f;
    const float py = -0.9233830526072779f;
    const float pz = -0.14341305464217718f;
    const float scale = 0.20627889373308725f;
    const float offset = -0.7941257971234911f;
    
    // ODE State variables
    float h;
    float v;

public:
    float value;

    Heave() : value(0.0f), lastTime(0), h(0.0f), v(0.0f) {}

    // Requires timestamp in microseconds (e.g., from esp_timer_get_time())
    void update(float wx, float wy, float wz, float ax, float ay, float az, float pitch, float roll, uint64_t timestamp_us) {
        if (lastTime == 0) {
            lastTime = timestamp_us;
            return;
        }
        
        float dt = (timestamp_us - lastTime) / 1000000.0f;
        if (dt <= 0.0f) {
            return;
        }
        
        lastTime = timestamp_us;
        
        // Project acceleration to the primary heave axis
        float a_proj = px * ax + py * ay + pz * az;
        
        // Double Integrator with High-Pass Characteristics (Damped Oscillator)
        float omega_c = 2.0f * M_PI * fc;
        float omega_c_sq = omega_c * omega_c;
        float two_zeta_omega_c = 2.0f * zeta * omega_c;
        
        v += (a_proj - two_zeta_omega_c * v - omega_c_sq * h) * dt;
        h += v * dt;
        
        // The filter produces a zero-mean output. We apply the optimized linear fit parameters
        // to match the absolute magnitude and offset of the True Physical Heave.
        value = h * scale + offset;
    }
}; 

#endif