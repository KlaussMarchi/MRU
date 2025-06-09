#include "../../../global/functions.h"
#include "../../processing/integral.h"


struct ProcessingMPU9250{
private:
    struct Acceleration{     
        struct Filter{
            float Xn1, Xn2;
            float Yn1, Yn2;

            float compute(const float Xn){
                static unsigned long startTime = espMillis();

                if(espMillis() - startTime < DT_INTERVAL)
                    return Yn1;
                
                startTime = espMillis();
                const float Yn = Xn*(0.133618) + Xn1*(-0.000000) + Xn2*(-0.133618) + Yn1*(1.669797) + Yn2*(-0.732763);
                Xn2 = Xn1; Xn1 = Xn;
                Yn2 = Yn1; Yn1 = Yn;
                return Yn;
            }
        };

        float x, y, z;
        Filter fx, fy, fz;
        
        void update(float ax, float ay, float az){
            x = fx.compute(ax);
            y = fy.compute(ay);
            z = fz.compute(az);
        }
    };

    struct Velocity{
        Integral intX, intY, intZ;
        float x, y, z;
        
        void update(float ax, float ay, float az){
            x = intX.compute(ax);
            y = intY.compute(ay);
            z = intZ.compute(az);
        }
    };

    struct Position{
        Integral intX, intY, intZ;
        float x, y, z;
        
        void update(float vx, float vy, float vz){
            x = intX.compute(vx);
            y = intY.compute(vy);
            z = intZ.compute(vz);
        }
    };

    struct Omega{
        struct Filter{
            float Xn1, Xn2;
            float Yn1, Yn2;

            float compute(const float Xn){
                static unsigned long startTime = espMillis();
                
                if(espMillis() - startTime < DT_INTERVAL)
                    return Yn1;

                startTime = espMillis();
                const float Yn = Xn*(0.063964) + Xn1*(0.127929) + Xn2*(0.063964) + Yn1*(1.168261) + Yn2*(-0.424118);
                Xn2 = Xn1; Xn1 = Xn;
                Yn2 = Yn1; Yn1 = Yn;
                return Yn;
            }
        };
        
        Filter fx, fy, fz;
        float x, y, z;

        void update(float wx, float wy, float wz){
            x = fx.compute(wx);
            y = fy.compute(wy);
            z = fz.compute(wz);
        }
    };
public:
    float pitch, roll, yaw;
    float time;
    Acceleration a;
    Velocity v;
    Position p;
    Omega w;

    void update(float ax, float ay, float az, float wx, float wy, float wz){
        static unsigned long startTime = espMillis();
        time = (espMillis() - startTime)/1000.00;

        a.update(ax, ay, az);
        w.update(wx, wy, wz);
        
        v.update(a.x, a.y, a.z);
        p.update(v.x, v.y, v.z);

        pitch = atan2(a.x, sqrt(a.y * a.y + a.z * a.z)) * RAD_TO_DEG;
        roll  = atan2(a.y, a.z) * RAD_TO_DEG;
    }
};

