#include <FastAccelStepper.h>
#include <math.h>
#include "esp_timer.h"

class Motor {
  private:
    const uint8_t STEP_ROLL_PIN = 18;
    const uint8_t DIR_ROLL_PIN  = 19;
    
    const uint8_t STEP_PITCH_PIN = 21;
    const uint8_t DIR_PITCH_PIN  = 22;
    const float STEPS_PER_DEGREE = 40.00f;

    FastAccelStepperEngine engine;
    FastAccelStepper *rollMotor  = nullptr;
    FastAccelStepper *pitchMotor = nullptr;

    long degreesToSteps(float degrees){
        return lround(degrees * STEPS_PER_DEGREE);
    }

    float stepsToDegrees(long steps){
        return (float)steps / STEPS_PER_DEGREE;
    }

  public:
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
    }

    void setTarget(float rollDeg, float pitchDeg){
        if(!rollMotor || !pitchMotor) 
            return;
        
        rollMotor->moveTo(degreesToSteps(rollDeg));
        pitchMotor->moveTo(degreesToSteps(pitchDeg));
    }

    float getRoll() {
        if(!rollMotor) return 0.0f;
        return stepsToDegrees(rollMotor->getCurrentPosition());
    }

    float getPitch() {
        if(!pitchMotor) return 0.0f;
        return stepsToDegrees(pitchMotor->getCurrentPosition());
    }

    void reset(){
        if(!rollMotor || !pitchMotor) 
            return;
        
        rollMotor->moveTo(0);
        pitchMotor->moveTo(0);

        while(rollMotor->isRunning() || pitchMotor->isRunning())
            delay(1);
    }
};

Motor motor;
const float dt = 0.10f;
int64_t startTime = 0;

void setup() {
    Serial.begin(9600);
    delay(700);

    Serial.println("\nmotor setup");
    motor.setup();
    delay(700);

    while(!Serial.available())
        delay(100);

    while(Serial.available())
        Serial.read();

    startTime = esp_timer_get_time();
}

float getTime() {
    return (esp_timer_get_time() - startTime) * 1e-6f;
}

void loop() {
    static const int64_t timeout = (int64_t)(dt * 1000000.0f);
    static int64_t lastPrintTime = 0;

    float t = getTime();
    float rollAmplitude  = 5.00f;
    float pitchAmplitude = 5.00f;
    float frequency = 0.10f;

    float rollDeg  = 0.0f;
    float pitchDeg = 0.0f;

    float wx = 0.0f;
    float wy = 0.0f;
    float wz = 0.0f;

    // Metodologia dos testes:
    // 0 a 15s: Aquecimento/Folga (none)
    // 15 a 315s: Variando Pitch
    // 315 a 325s: Folga (none)
    // 325 a 625s: Variando Roll
    // > 625s: Estático (none/static)
    
    if(t >= 15.0f && t < 315.0f){
        float phase = 2.0f * PI * frequency * (t - 15.0f);
        pitchDeg = pitchAmplitude * sinf(phase);
        wy = pitchAmplitude * (2.0f * PI * frequency) * cosf(phase);
        wx = 0.0f;
        wz = 0.0f;
    }
    else if(t >= 325.0f && t < 625.0f){
        float phase = 2.0f * PI * frequency * (t - 325.0f);
        rollDeg = rollAmplitude * sinf(phase);
        wx = rollAmplitude * (2.0f * PI * frequency) * cosf(phase);
        wy = 0.0f;
        wz = 0.0f;
    }
    else{
        wx = 0.0f;
        wy = 0.0f;
        wz = 0.0f;
    }

    motor.setTarget(rollDeg, pitchDeg);
    int64_t currentTime = esp_timer_get_time();

    if(currentTime - lastPrintTime < timeout)
        return;

    lastPrintTime = currentTime;

    float angleRoll  = motor.getRoll();
    float anglePitch = motor.getPitch();

    float pitchRad = anglePitch * (PI / 180.0f);
    float rollRad  = angleRoll  * (PI / 180.0f);

    float GRAVITY = 9.80665f;
    float ax  = sinf(pitchRad) * GRAVITY;
    float ay  = -sinf(rollRad) * cosf(pitchRad) * GRAVITY;
    float az  = cosf(rollRad)  * cosf(pitchRad) * GRAVITY;
    float yaw = 108.0f;

    char buffer[256];
    int len = snprintf(buffer, sizeof(buffer), 
        "[%.3f,%.2f,%.2f,%.2f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f]\n", 
        t, anglePitch, angleRoll, yaw,
        ax, ay, az, 
        wx, wy, wz, 
        0.0f
    );

    if(Serial.available() && Serial.readString().indexOf("reset") != -1)
        ESP.restart();

    Serial.write((uint8_t*)buffer, len);
}