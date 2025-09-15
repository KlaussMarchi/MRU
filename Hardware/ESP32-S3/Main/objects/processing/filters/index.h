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


#endif