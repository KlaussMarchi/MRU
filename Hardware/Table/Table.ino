#include <FastAccelStepper.h>
#include <math.h>
#include "esp_timer.h"


class Motor{
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

    float getRoll(){
        if(!rollMotor) return 0.0f;
        return stepsToDegrees(rollMotor->getCurrentPosition());
    }

    float getPitch(){
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

class Movement{
  private:
    Motor& motor;
    int64_t lastPrintTime = 0;
    int64_t timeout = 0.1 * 1e6; 
    
  public:
    unsigned long startTime;
    float t, pitch, roll;

    Movement(Motor& motorRef): 
        motor(motorRef){}

    void start(){
        startTime = esp_timer_get_time();
    }

    unsigned long getTime(){
        return (esp_timer_get_time() - startTime) / 1000;
    }

    void handle(){
        int64_t currentTime = esp_timer_get_time();
        update();

        if(currentTime - lastPrintTime < timeout)
            return;

        lastPrintTime = currentTime;
        print();
    }

    void update(){
        t = getTime() / 1000.00; 
        const float targetRoll  = 15*sin(t);
        const float targetPitch = 15*sin(t); 
        
        roll  = motor.getRoll();
        pitch = motor.getPitch();
        motor.setTarget(targetRoll, targetPitch);
    }

    void print(){
        char buffer[256];
        int len = snprintf(buffer, sizeof(buffer), "[%.3f,%.3f,%.3f]\n", t, pitch, roll);
        Serial.write((uint8_t*)buffer, len);
    }
}; 

Motor motor;
Movement movement(motor); 


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

    movement.start();
}

void loop(){
    movement.handle();
}