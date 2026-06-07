#ifndef GYRO_CALIB
#define GYRO_CALIB

class GyroCalibrator {
  private:
    float sum_x = 0.0f, sum_y = 0.0f, sum_z = 0.0f;
    int samples_collected = 0;
    
  public:
    bool calibrated = false;
    int target_samples = 500;

    float bias_x = 0.0f;
    float bias_y = 0.0f;
    float bias_z = 0.0f;

    void update(float wx, float wy, float wz){
        if(calibrated) 
            return;

        sum_x += wx;
        sum_y += wy;
        sum_z += wz;
        samples_collected++;

        if(samples_collected >= target_samples){
            bias_x = sum_x / samples_collected;
            bias_y = sum_y / samples_collected;
            bias_z = sum_z / samples_collected;
            calibrated = true;
        }
    }

    void apply(float& wx, float& wy, float& wz) const {
        if (!calibrated) return;
        wx -= bias_x;
        wy -= bias_y;
        wz -= bias_z;
    }
};

#endif