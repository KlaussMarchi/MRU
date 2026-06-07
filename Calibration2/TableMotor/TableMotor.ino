#include <FastAccelStepper.h>
#include <math.h>
#include "esp_timer.h"

class Motor{
  private:
    const uint8_t STEP_ROLL_PIN = 18;
    const uint8_t DIR_ROLL_PIN  = 19;
    
    const uint8_t STEP_PITCH_PIN = 21;
    const uint8_t DIR_PITCH_PIN  = 22;

    const float STEPS_PER_DEGREE = 40.00;
    FastAccelStepperEngine engine;
    FastAccelStepper *rollMotor = nullptr;
    FastAccelStepper *pitchMotor = nullptr;

    long degreesToSteps(float degrees){
        return lround(degrees * STEPS_PER_DEGREE);
    }

    float stepsToDegrees(long steps){
        return (float)steps / STEPS_PER_DEGREE;
    }

  public:
    float angle_roll  = 0.0;
    float angle_pitch = 0.0;
    int64_t startTime = 0;

    void setup(){
        engine.init();

        rollMotor  = engine.stepperConnectToPin(STEP_ROLL_PIN);
        pitchMotor = engine.stepperConnectToPin(STEP_PITCH_PIN);

        if(rollMotor){
            rollMotor->setDirectionPin(DIR_ROLL_PIN);
            rollMotor->setAutoEnable(true);
            rollMotor->setSpeedInHz(8000);
            rollMotor->setAcceleration(6000);
        }

        if(pitchMotor){
            pitchMotor->setDirectionPin(DIR_PITCH_PIN);
            pitchMotor->setAutoEnable(true);
            pitchMotor->setSpeedInHz(8000);
            pitchMotor->setAcceleration(6000);
        }

        startTime = esp_timer_get_time();
    }

    void handle(){
        float roll_amplitude  = 5.00;
        float pitch_amplitude = 5.00;
        float frequency = 0.10f;

        float t = getTime();
        float rollDeg  = 0.0;
        float pitchDeg = 0.0;

        // Metodologia dos testes:
        // 0 a 15s: Aquecimento/Folga (none)
        // 15 a 315s: Variando Pitch
        // 315 a 325s: Folga (none)
        // 325 a 625s: Variando Roll
        // > 625s: Estático (none/static)]

        if(t >= 15.0f && t < 315.0f)
            pitchDeg = pitch_amplitude * sinf(2.0f * PI * frequency * (t - 15.0f));
        else if(t >= 325.0f && t < 625.0f)
            rollDeg = roll_amplitude * sinf(2.0f * PI * frequency * (t - 325.0f));

        if(!rollMotor || !pitchMotor)
            return;

        rollMotor->moveTo(degreesToSteps(rollDeg));
        pitchMotor->moveTo(degreesToSteps(pitchDeg));

        angle_roll  = stepsToDegrees(rollMotor->getCurrentPosition());
        angle_pitch = stepsToDegrees(pitchMotor->getCurrentPosition());
    }

    float getTime() {
        return (esp_timer_get_time() - startTime) * 1e-6f;
    }

    void reset() {
        if(!rollMotor || !pitchMotor) 
            return;

        rollMotor->moveTo(0);
        pitchMotor->moveTo(0);

        while(rollMotor->isRunning() || pitchMotor->isRunning()){
            angle_roll  = stepsToDegrees(rollMotor->getCurrentPosition());
            angle_pitch = stepsToDegrees(pitchMotor->getCurrentPosition());
            delay(1); 
        }
    }
};

Motor motor;
const float dt = 0.10;

void setup() {
    Serial.begin(115200);
    motor.setup();
}

void loop(){
    static int64_t lastPrintTime = 0;
    motor.handle();

    int64_t currentTime = esp_timer_get_time();

    if (currentTime - lastPrintTime < (int64_t)(dt * 1000000.0f))
        return;

    lastPrintTime = currentTime;
    float t = motor.getTime();
    
    char buffer[128];
    int len = snprintf(buffer, sizeof(buffer), "{\"time\":%.3f,\"pitch\":%.2f,\"roll\":%.2f}\n", t, motor.angle_pitch, motor.angle_roll);
    Serial.write((uint8_t*)buffer, len);
}