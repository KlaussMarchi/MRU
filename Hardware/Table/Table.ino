#include <FastAccelStepper.h>
#include <math.h>
#include "esp_timer.h"


class Motor{
  private:
    const uint8_t STEP_ROLL_PIN  = 18;
    const uint8_t DIR_ROLL_PIN   = 19;
    const uint8_t STEP_PITCH_PIN = 21;
    const uint8_t DIR_PITCH_PIN  = 22;

    const float STEPS_PER_DEGREE = 40.00f;
    const uint32_t MAX_SPEED_HZ  = 8000;
    const int32_t ACCELERATION   = 6000;

    FastAccelStepperEngine engine;
    FastAccelStepper *rollMotor  = nullptr;
    FastAccelStepper *pitchMotor = nullptr;

    long degreesToSteps(float degrees){
        return lround(degrees * STEPS_PER_DEGREE);
    }

    float stepsToDegrees(long steps){
        return float(steps / STEPS_PER_DEGREE);
    }

    FastAccelStepper* connect(uint8_t stepPin, uint8_t dirPin){
        FastAccelStepper *stepper = engine.stepperConnectToPin(stepPin);

        if(!stepper)
            return nullptr;

        stepper->setDirectionPin(dirPin);
        stepper->setSpeedInHz(MAX_SPEED_HZ);
        stepper->setAcceleration(ACCELERATION);
        return stepper;
    }

  public:
    bool setup(){
        engine.init();
        rollMotor  = connect(STEP_ROLL_PIN, DIR_ROLL_PIN);
        pitchMotor = connect(STEP_PITCH_PIN, DIR_PITCH_PIN);
        return isReady();
    }

    bool isReady(){
        return bool(rollMotor && pitchMotor);
    }

    bool isRunning(){
        if(!isReady())
            return false;

        return rollMotor->isRunning() || pitchMotor->isRunning();
    }

    void setTarget(float rollDeg, float pitchDeg){
        if(!isReady())
            return;

        rollMotor->moveTo(degreesToSteps(rollDeg));
        pitchMotor->moveTo(degreesToSteps(pitchDeg));
    }

    float getRoll(){
        if(!rollMotor)
            return 0.0f;

        return stepsToDegrees(rollMotor->getCurrentPosition());
    }

    float getPitch(){
        if(!pitchMotor)
            return 0.0f;

        return stepsToDegrees(pitchMotor->getCurrentPosition());
    }

    void reset(){
        setTarget(0.0f, 0.0f);

        while(isRunning())
            delay(1);
    }
};

class Movement{
  private:
    Motor& motor;

    const float AMPLITUDE        = 15.0f;
    const int64_t UPDATE_PERIOD  = 5000;
    const int64_t PRINT_PERIOD   = 100000;

    int64_t startTime      = 0;
    int64_t lastUpdateTime = 0;
    int64_t lastPrintTime  = 0;

    float t     = 0.0f;
    float roll  = 0.0f;
    float pitch = 0.0f;

    bool setPeriod(int64_t &last, int64_t period, int64_t now){
        if(now - last < period)
            return false;

        last = now;
        return true;
    }

    float getTime(){
        return (esp_timer_get_time() - startTime) / 1e6;
    }

    void update(){
        t = getTime();
        roll  = motor.getRoll();
        pitch = motor.getPitch();
        motor.setTarget(AMPLITUDE * sinf(t), AMPLITUDE * sinf(t));
    }

    void print(){
        char buffer[64];
        int len = snprintf(buffer, sizeof(buffer), "[%.3f,%.3f,%.3f]\n", t, pitch, roll);
        Serial.write((uint8_t*)buffer, len);
    }

  public:
    Movement(Motor& motorRef):
        motor(motorRef){}

    void start(){
        startTime = esp_timer_get_time();
        Serial.println("iniciando movimento...");
    }

    void handle(){
        int64_t now = esp_timer_get_time();

        if(setPeriod(lastUpdateTime, UPDATE_PERIOD, now))
            update();

        if(setPeriod(lastPrintTime, PRINT_PERIOD, now))
            print();
    }
};

Motor motor;
Movement movement(motor);

void setup(){
    Serial.begin(115200);
    delay(700);
    Serial.println("\nmotor setup");

    if(!motor.setup()){
        Serial.println("falha ao conectar os motores");
        
        while(true)
            delay(1000);
    }

    delay(700);

    while(!Serial.available())
        delay(100);

    while(Serial.available())
        Serial.read();

    movement.start();
}

void loop(){
    movement.handle();
    
    if(!Serial.available())
        return;
    
    if(Serial.readString().indexOf("reset") != -1)
        {motor.reset(); ESP.restart();}
}
