#ifndef FILTERS_H
#define FILTERS_H

template<int SIZE> class Smoother{
  public:
    float array[SIZE];
    float sum = 0.00;
    int i = 0;  

    Smoother(){
        reset();
    }

    void reset(){
        for(int x=0; x<SIZE; x++)
            array[x] = 0;

        sum = 0.00;
        i   = 0;
    }

    float update(float value){
        sum = sum - array[i];
        array[i] = value;

        sum = sum + array[i];
        i = (i + 1 < SIZE) ? (i + 1) : 0;
        return (sum / SIZE);
    }
};

class ButterworthFilter{
  public:
    float a[3], b[3];
    float f_c;
    float Xn1, Yn1;
    float Xn2, Yn2;

    void setup(float cutoff_hz, float dt){
        float Fs = 1.0f/dt;
        float fc = cutoff_hz / Fs;
        if(fc <= 0) fc = 0.0001f;
        if(fc >= 0.499f) fc = 0.499f;

        float wc = tan(PI * fc);
        float c2 = wc*wc;
        float norm = 1 + sqrt(2)*wc + c2;

        b[0] = c2/norm;  b[1] = 2*c2/norm;  b[2] = c2/norm;
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

#endif