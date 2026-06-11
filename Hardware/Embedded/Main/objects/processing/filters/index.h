#ifndef FILTERS_H
#define FILTERS_H
#include <Arduino.h>


class ButterworthFilter{
  public:
    float a[3], b[3];
    float f_c;
    float Xn1, Yn1;
    float Xn2, Yn2;

    ButterworthFilter(float Fc){
        f_c = Fc / 2.0f;
        float wc = tan(PI*f_c);
        float c2 = wc*wc;
        float norm = 1 + sqrt(2)*wc + c2;

        b[0] = c2/norm;
        b[1] = 2*c2/norm;
        b[2] = c2/norm;

        a[0] = 1.0;
        a[1] = -2*(c2 - 1)/norm;
        a[2] = -(1 - sqrt(2)*wc + c2)/norm;
        reset();
    }

    float compute(const float Xn){
        const float Yn = (b[0]*Xn + b[1]*Xn1 + b[2]*Xn2 + a[1]*Yn1 + a[2]*Yn2);
        Yn2 = Yn1; Yn1 = Yn;
        Xn2 = Xn1; Xn1 = Xn;
        return Yn;
    }

    void reset(){
        Xn1 = 0; Xn2 = 0;
        Yn1 = 0; Yn2 = 0;
    }
};


class LowPassFilter{
  private:
    float    _Fc;
    float    _b[5], _a[5];
    float    _x[5], _y[5];
    uint32_t _dt_us, _last_us;
    Listener timer = Listener(0);

  public:
    LowPassFilter(): _Fc(0), _dt_us(0), _last_us(0){
        memset(_b, 0, sizeof(_b));
        memset(_a, 0, sizeof(_a));
        memset(_x, 0, sizeof(_x));
        memset(_y, 0, sizeof(_y));
    }

    void setup(float Fc, float dt) {
        _dt_us = (uint32_t) (dt * 1e6f);
        timer.set((uint32_t) (dt * 1000.0f));
        _Fc = Fc;

        memset(_b, 0, sizeof(_b));
        memset(_a, 0, sizeof(_a));
        memset(_x, 0, sizeof(_x));
        memset(_y, 0, sizeof(_y));

        if(Fc <= 0.0f) 
            return;

        const float W  = 2.0f * M_PI * Fc;
        const float k  = 2.0f / dt;
        const float c  = (W - k) / (W + k);
        const float g  = W / (W + k);
        const float g4 = g * g * g * g;
        const float c2 = c * c, c3 = c2 * c, c4 = c3 * c;

        _b[0] = g4;        _b[1] = 4.0f * g4; _b[2] = 6.0f * g4;
        _b[3] = 4.0f * g4; _b[4] = g4;

        _a[1] = 4.0f * c;  _a[2] = 6.0f * c2;
        _a[3] = 4.0f * c3; _a[4] = c4;
    }

    float update(float input) {
        if(_Fc <= 0.0f) 
            return input;

        if(!timer.ready())
            return _y[0];

        const uint32_t now = micros();
        if (now - _last_us < _dt_us) return _y[0];
        _last_us = now;

        for (int i = 4; i > 0; i--) { _x[i] = _x[i-1]; _y[i] = _y[i-1]; }
        _x[0] = input;

        float out = 0.0f;
        for (int i = 0; i < 5; i++) out += _b[i] * _x[i];
        for (int i = 1; i < 5; i++) out -= _a[i] * _y[i];

        return _y[0] = out;
    }

    void reset() {
        memset(_x, 0, sizeof(_x));
        memset(_y, 0, sizeof(_y));
        _last_us = 0;
    }
};

#endif