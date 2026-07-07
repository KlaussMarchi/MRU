#include <FastAccelStepper.h>
#include <math.h>
#include "esp_timer.h"

class Motor {
  private:
    const uint8_t STEP_ROLL_PIN  = 18;
    const uint8_t DIR_ROLL_PIN   = 19;
    const uint8_t STEP_PITCH_PIN = 21;
    const uint8_t DIR_PITCH_PIN  = 22;

    const uint8_t FC_ROLL_MIN_PIN  = 25;
    const uint8_t FC_ROLL_MAX_PIN  = 26;
    const uint8_t FC_PITCH_MIN_PIN = 33;
    const uint8_t FC_PITCH_MAX_PIN = 32;

    const float STEPS_PER_DEGREE  = 40.00f;
    const float LIMITE_MIN        = -40.0f;
    const float LIMITE_MAX        =  40.0f;
    const float RECUO_ROLL_HOME   = 61.0f;
    const float RECUO_PITCH_HOME  = 40.0f;

    const uint32_t SPEED_HZ_DEFAULT = 8000;
    const uint32_t ACCEL_DEFAULT    = 6000;
    const uint32_t SPEED_HZ_HOME    = 800;
    const uint32_t ACCEL_HOME       = 2000;

    FastAccelStepperEngine engine;
    FastAccelStepper *rollMotor  = nullptr;
    FastAccelStepper *pitchMotor = nullptr;

    bool emFalha = false;
    uint32_t fcDebounceStart = 0;

    long degreesToSteps(float degrees){
        return lround(degrees * STEPS_PER_DEGREE);
    }

    float stepsToDegrees(long steps){
        return (float)steps / STEPS_PER_DEGREE;
    }

    float clampDeg(float deg){
        return constrain(deg, LIMITE_MIN, LIMITE_MAX);
    }

    bool fcAcionado(){
        return digitalRead(FC_ROLL_MIN_PIN)  == HIGH ||
               digitalRead(FC_ROLL_MAX_PIN)  == HIGH ||
               digitalRead(FC_PITCH_MIN_PIN) == HIGH ||
               digitalRead(FC_PITCH_MAX_PIN) == HIGH;
    }

    void homeEixo(FastAccelStepper *m, uint8_t fcPin, float recuo, const char *nome){
        Serial.printf("HOMING: buscando FC_MAX %s...\n", nome);
        while(digitalRead(fcPin) != HIGH){
            m->move(degreesToSteps(3.0f));
            while(m->isRunning()) delayMicroseconds(100);
        }
        m->forceStopAndNewPosition(m->getCurrentPosition());
        Serial.printf("HOMING: FC %s tocado — recuando %.1f deg\n", nome, recuo);
        m->move(degreesToSteps(-recuo));
        while(m->isRunning()) delayMicroseconds(100);
        m->setCurrentPosition(0);
        Serial.printf("HOMING: %s zerado\n", nome);
    }

  public:
    void setup(bool autoHome = true){
        pinMode(FC_ROLL_MIN_PIN,  INPUT_PULLUP);
        pinMode(FC_ROLL_MAX_PIN,  INPUT_PULLUP);
        pinMode(FC_PITCH_MIN_PIN, INPUT_PULLUP);
        pinMode(FC_PITCH_MAX_PIN, INPUT_PULLUP);

        engine.init();
        rollMotor  = engine.stepperConnectToPin(STEP_ROLL_PIN);
        pitchMotor = engine.stepperConnectToPin(STEP_PITCH_PIN);

        if(rollMotor){
            rollMotor->setDirectionPin(DIR_ROLL_PIN);
            rollMotor->setAutoEnable(true);
            rollMotor->setSpeedInHz(SPEED_HZ_DEFAULT);
            rollMotor->setAcceleration(ACCEL_DEFAULT);
            rollMotor->setCurrentPosition(0);
        }

        if(pitchMotor){
            pitchMotor->setDirectionPin(DIR_PITCH_PIN, true);
            pitchMotor->setAutoEnable(true);
            pitchMotor->setSpeedInHz(SPEED_HZ_DEFAULT);
            pitchMotor->setAcceleration(ACCEL_DEFAULT);
            pitchMotor->setCurrentPosition(0);
        }

        if(autoHome)
            home();
    }

    void home(){
        if(!rollMotor || !pitchMotor) return;

        rollMotor->setSpeedInHz(SPEED_HZ_HOME);
        rollMotor->setAcceleration(ACCEL_HOME);
        pitchMotor->setSpeedInHz(SPEED_HZ_HOME);
        pitchMotor->setAcceleration(ACCEL_HOME);

        homeEixo(rollMotor,  FC_ROLL_MAX_PIN,  RECUO_ROLL_HOME,  "roll");
        homeEixo(pitchMotor, FC_PITCH_MAX_PIN, RECUO_PITCH_HOME, "pitch");

        rollMotor->setSpeedInHz(SPEED_HZ_DEFAULT);
        rollMotor->setAcceleration(ACCEL_DEFAULT);
        pitchMotor->setSpeedInHz(SPEED_HZ_DEFAULT);
        pitchMotor->setAcceleration(ACCEL_DEFAULT);

        emFalha = false;
        Serial.println("Mesa nivelada.");
    }

    void setTarget(float rollDeg, float pitchDeg){
        if(!rollMotor || !pitchMotor || emFalha) return;
        rollMotor->moveTo(degreesToSteps(clampDeg(rollDeg)));
        pitchMotor->moveTo(degreesToSteps(clampDeg(pitchDeg)));
    }

    void setTarget(float rollDeg, float pitchDeg, float wRollRadS, float wPitchRadS){
        if(!rollMotor || !pitchMotor || emFalha) return;

        float velRollDegS  = fabs(wRollRadS)  * (180.0f / PI);
        float velPitchDegS = fabs(wPitchRadS) * (180.0f / PI);

        uint32_t sR = (uint32_t) constrain(velRollDegS  * STEPS_PER_DEGREE, 50.0f, (float)SPEED_HZ_DEFAULT);
        uint32_t sP = (uint32_t) constrain(velPitchDegS * STEPS_PER_DEGREE, 50.0f, (float)SPEED_HZ_DEFAULT);

        rollMotor->setSpeedInHz(sR);
        pitchMotor->setSpeedInHz(sP);
        rollMotor->moveTo(degreesToSteps(clampDeg(rollDeg)));
        pitchMotor->moveTo(degreesToSteps(clampDeg(pitchDeg)));
    }

    float getRoll(){
        if(!rollMotor) return 0.0f;
        return stepsToDegrees(rollMotor->getCurrentPosition());
    }

    float getPitch(){
        if(!pitchMotor) return 0.0f;
        return stepsToDegrees(pitchMotor->getCurrentPosition());
    }

    void stop(){
        if(rollMotor)  rollMotor->forceStopAndNewPosition(rollMotor->getCurrentPosition());
        if(pitchMotor) pitchMotor->forceStopAndNewPosition(pitchMotor->getCurrentPosition());
    }

    void zero(){
        if(rollMotor)  rollMotor->forceStopAndNewPosition(0);
        if(pitchMotor) pitchMotor->forceStopAndNewPosition(0);
    }

    bool isInFault() const { return emFalha; }

    bool checkFault(){
        if(fcAcionado()){
            if(fcDebounceStart == 0) fcDebounceStart = millis();
            else if(millis() - fcDebounceStart >= 50){
                stop();
                emFalha = true;
                Serial.println("ERRO: Fim de curso acionado!");
                fcDebounceStart = 0;
                return true;
            }
        } else {
            fcDebounceStart = 0;
        }
        return emFalha;
    }

    void printInfo(){
        if(!rollMotor || !pitchMotor) return;
        Serial.printf("Roll=%.2f deg  Pitch=%.2f deg\n", getRoll(), getPitch());
    }

    void printFC(){
        Serial.printf("FC_ROLL_MIN : %s\n", digitalRead(FC_ROLL_MIN_PIN)  ? "ACIONADO" : "livre");
        Serial.printf("FC_ROLL_MAX : %s\n", digitalRead(FC_ROLL_MAX_PIN)  ? "ACIONADO" : "livre");
        Serial.printf("FC_PITCH_MIN: %s\n", digitalRead(FC_PITCH_MIN_PIN) ? "ACIONADO" : "livre");
        Serial.printf("FC_PITCH_MAX: %s\n", digitalRead(FC_PITCH_MAX_PIN) ? "ACIONADO" : "livre");
    }

    void reset(){
        if(!rollMotor || !pitchMotor) return;
        rollMotor->moveTo(0);
        pitchMotor->moveTo(0);
        while(rollMotor->isRunning() || pitchMotor->isRunning())
            delay(1);
    }

    void printHelp(){
        Serial.println("Comandos: r+10 p-10 ra45 pa-20 s z info fc home ?");
    }

    void processSerial(String cmd){
        cmd.trim();
        cmd.toLowerCase();
        if(cmd.length() == 0) return;

        if(cmd == "?")    { printHelp();  return; }
        if(cmd == "info") { printInfo();  return; }
        if(cmd == "fc")   { printFC();    return; }
        if(cmd == "s")    { stop();       Serial.println("Parado."); printInfo(); return; }
        if(cmd == "z")    { zero();       Serial.println("Zero definido aqui."); return; }
        if(cmd == "home") { home();       return; }

        if(cmd.length() < 2){ Serial.println("Comando invalido."); return; }

        char eixo = cmd.charAt(0);
        if(eixo != 'r' && eixo != 'p'){ Serial.println("Eixo invalido."); return; }

        FastAccelStepper *m = (eixo == 'r') ? rollMotor : pitchMotor;
        if(!m) return;

        bool absoluto = (cmd.charAt(1) == 'a');
        String valorStr = absoluto ? cmd.substring(2) : cmd.substring(1);
        if(valorStr.length() == 0){ Serial.println("Faltou o valor em graus."); return; }

        float graus = valorStr.toFloat();
        float alvo;
        if(absoluto){
            alvo = clampDeg(graus);
        } else {
            float atual = stepsToDegrees(m->getCurrentPosition());
            alvo = clampDeg(atual + graus);
        }
        m->moveTo(degreesToSteps(alvo));
        Serial.printf("%s -> %.2f deg\n", (eixo == 'r') ? "Roll" : "Pitch", alvo);
    }
};

float ROLL_AMPLITUDE  = 15.00f;
float PITCH_AMPLITUDE = 15.00f;
float frequency       = 0.30f;
const bool autostart  = true;
const bool AUTO_HOME_ON_BOOT = true;

Motor motor;
const float dt = 0.10f;
int64_t startTime = 0;

void setup() {
    Serial.begin(115200);
    delay(700);

    Serial.println("\nmotor setup");
    motor.setup(AUTO_HOME_ON_BOOT);
    delay(700);

    while(!autostart && !Serial.available())
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

    if(motor.checkFault()){
        if(Serial.available() && Serial.readString().indexOf("reset") != -1)
            ESP.restart();
        return;
    }

    if(Serial.available()){
        String cmd = Serial.readStringUntil('\n');
        if(cmd.indexOf("reset") != -1){ ESP.restart(); return; }
        motor.processSerial(cmd);
    }

    float t = getTime();
    float rollDeg  = 0.0f;
    float pitchDeg = 0.0f;

    float wx = 0.0f;
    float wy = 0.0f;
    float wz = 0.0f;

    if(t >= 15.0f && t < 315.0f){
        float phase = 2.0f * PI * frequency * (t - 15.0f);
        pitchDeg = PITCH_AMPLITUDE * sinf(phase);
        wy = PITCH_AMPLITUDE * (2.0f * PI * frequency) * cosf(phase);
        wx = 0.0f;
        wz = 0.0f;
    }
    else if(t >= 325.0f && t < 625.0f){
        float phase = 2.0f * PI * frequency * (t - 325.0f);
        rollDeg = ROLL_AMPLITUDE * sinf(phase);
        wx = ROLL_AMPLITUDE * (2.0f * PI * frequency) * cosf(phase);
        wy = 0.0f;
        wz = 0.0f;
    }
    else{
        wx = 0.0f;
        wy = 0.0f;
        wz = 0.0f;
    }

    motor.setTarget(rollDeg, pitchDeg, wx, wy);

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

    Serial.write((uint8_t*) buffer, len);
}