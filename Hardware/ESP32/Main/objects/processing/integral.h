#ifndef INTEGRAL_H
#define INTEGRAL_H
#include "../../global/functions.h"
#include "../../global/constants.h"


struct Integral{
    float Xn1, Yn1;

    float compute(float Xn){
        static unsigned long startTime = espMillis();

        if(espMillis() - startTime < DT_INTERVAL)
            return Yn1;
        
        startTime = espMillis();
        const float Yn = Xn*(0.025000) + Xn1*(0.025000) + Yn1*(1.000000);
        Xn1 = Xn; Yn1 = Yn;
        return Yn;
    }
};

#endif
