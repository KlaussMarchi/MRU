#include <FastAccelStepper.h>
#include <math.h>
#include "esp_timer.h"


// EIXO DA MESA MOVIDO POR MOTOR DE PASSO, COM FIM DE CURSO NOS DOIS EXTREMOS
class Motor{
  private:
	const float STEPS_PER_DEGREE = 40.00f;
	const float LIMITE_MIN       = -40.0f;
	const float LIMITE_MAX       =  40.0f;
	const float HOME_STEP        = 3.0f;      // GRAUS POR TENTATIVA ATÉ O FC_MAX
	const float HOME_SEARCH      = 360.0f;    // CURSO MÁXIMO ANTES DE DECLARAR FALHA

	const uint32_t SPEED_HZ_DEFAULT = 8000;
	const uint32_t ACCEL_DEFAULT    = 6000;
	const uint32_t SPEED_HZ_HOME    = 800;
	const uint32_t ACCEL_HOME       = 2000;
	const uint32_t DEBOUNCE         = 50;     // ms

	FastAccelStepperEngine* engine;
	FastAccelStepper* stepper = nullptr;
	uint8_t stepPin;
	uint8_t dirPin;
	uint8_t fcMinPin;
	uint8_t fcMaxPin;
	float recuo;
	uint32_t fcDebounceStart = 0;
	long lastTarget = 0;

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
		return digitalRead(fcMinPin) == HIGH || digitalRead(fcMaxPin) == HIGH;
	}

	void wait(){
		while(stepper->isRunning())
			delayMicroseconds(100);
	}

  public:
	float current   = 0.0f;
	float target    = 0.0f;
	uint32_t speed  = SPEED_HZ_DEFAULT;
	bool emFalha    = false;

	Motor(FastAccelStepperEngine* engine, uint8_t stepPin, uint8_t dirPin, uint8_t fcMinPin, uint8_t fcMaxPin, float recuo):
		engine(engine),
		stepPin(stepPin),
		dirPin(dirPin),
		fcMinPin(fcMinPin),
		fcMaxPin(fcMaxPin),
		recuo(recuo){}

	void setup(){
		pinMode(fcMinPin, INPUT_PULLUP);
		pinMode(fcMaxPin, INPUT_PULLUP);
		stepper = engine->stepperConnectToPin(stepPin);
		emFalha = !stepper;

		if(emFalha)
			return;

		stepper->setDirectionPin(dirPin, true);
		stepper->setAutoEnable(true);
		stepper->setSpeedInHz(speed);
		stepper->setAcceleration(ACCEL_DEFAULT);
		stepper->setCurrentPosition(0);
	}

	void handle(){
		if(emFalha || checkFault())
			return;

		current  = get();
		long cmd = degreesToSteps(clampDeg(target));

		if(cmd == lastTarget)
			return;

		lastTarget = cmd;
		stepper->moveTo(cmd);
	}

	void goTo(float angle){
		target = angle;
		handle();

		while(!emFalha && stepper->isRunning()){
			checkFault();
			delay(1);
		}

		current = get();
	}

	void reset(){
		if(emFalha)
			return home();

		goTo(0.0f);
	}

	void home(){
		if(!stepper)
			return;

		stepper->setSpeedInHz(SPEED_HZ_HOME);
		stepper->setAcceleration(ACCEL_HOME);

		for(float searched=0; digitalRead(fcMaxPin) != HIGH; searched+=HOME_STEP){
			if(searched >= HOME_SEARCH){
				emFalha = true;
				return;
			}

			stepper->move(degreesToSteps(HOME_STEP));
			wait();
		}

		stepper->forceStopAndNewPosition(stepper->getCurrentPosition());
		stepper->move(degreesToSteps(-recuo));
		wait();

		stepper->setCurrentPosition(0);
		stepper->setSpeedInHz(speed);
		stepper->setAcceleration(ACCEL_DEFAULT);
		current         = 0.0f;
		target          = 0.0f;
		lastTarget      = 0;
		fcDebounceStart = 0;
		emFalha         = false;
	}

	bool checkFault(){
		if(!fcAcionado()){
			fcDebounceStart = 0;
			return emFalha;
		}

		if(fcDebounceStart == 0)
			fcDebounceStart = millis();

		if(millis() - fcDebounceStart < DEBOUNCE)
			return emFalha;

		stop();
		return emFalha = true;
	}

	void stop(){
		if(!stepper || !stepper->isRunning())
			return;

		stepper->forceStopAndNewPosition(stepper->getCurrentPosition());
	}

	float get(){
		return stepper ? stepsToDegrees(stepper->getCurrentPosition()) : 0.0f;
	}
};


// ENSAIO CÍCLICO DA MESA: PITCH, ROLL E REPOUSO, TRANSMITINDO TEMPO, PITCH E ROLL
class Movement{
  private:
	const uint8_t STEP_ROLL_PIN  = 18;
	const uint8_t DIR_ROLL_PIN   = 19;
	const uint8_t STEP_PITCH_PIN = 21;
	const uint8_t DIR_PITCH_PIN  = 22;

	const uint8_t FC_ROLL_MIN_PIN  = 25;
	const uint8_t FC_ROLL_MAX_PIN  = 26;
	const uint8_t FC_PITCH_MIN_PIN = 33;
	const uint8_t FC_PITCH_MAX_PIN = 32;

	const float RECUO_ROLL_HOME  = 61.0f;
	const float RECUO_PITCH_HOME = 40.0f;
	const float RAMP             = 2.0f;               // S DE ENTRADA E SAÍDA DE CADA SENOIDE
	const int64_t STAGE          = 100*1000000LL;      // US POR ETAPA: PITCH, ROLL, REPOUSO

	FastAccelStepperEngine engine;
	int64_t startTime = 0;

  public:
	Motor pitch = Motor(&engine, STEP_PITCH_PIN, DIR_PITCH_PIN, FC_PITCH_MIN_PIN, FC_PITCH_MAX_PIN, RECUO_PITCH_HOME);
	Motor roll  = Motor(&engine, STEP_ROLL_PIN, DIR_ROLL_PIN, FC_ROLL_MIN_PIN, FC_ROLL_MAX_PIN, RECUO_ROLL_HOME);

	float ROLL_AMPLITUDE   = 15.00f;
	float PITCH_AMPLITUDE  = 15.00f;
	float frequency        = 0.30f;
	float dt               = 0.01f;
	bool autostart         = true;
	bool AUTO_HOME_ON_BOOT = true;

	void setup(){
		engine.init();
		roll.setup();
		pitch.setup();

		if(AUTO_HOME_ON_BOOT){
			roll.home();
			pitch.home();
		}

		delay(700);

		while(!autostart && !Serial.available())
			delay(100);

		while(Serial.available())
			Serial.read();

		startTime = esp_timer_get_time();
	}

	void handle(){
		if(pitch.emFalha || roll.emFalha)
			return stop();

		int64_t elapsed = (esp_timer_get_time() - startTime) % (3*STAGE);
		int stage       = elapsed / STAGE;
		float t         = (elapsed % STAGE) * 1e-6f;

		pitch.target = stage == 0 ? getAngle(t, PITCH_AMPLITUDE) : 0.0f;
		roll.target  = stage == 1 ? getAngle(t, ROLL_AMPLITUDE)  : 0.0f;
		pitch.handle();
		roll.handle();
	}

	void reset(){
		roll.reset();
		pitch.reset();
		startTime = esp_timer_get_time();
	}

	void stop(){
		pitch.stop();
		roll.stop();
	}

	void listen(){
		if(!Serial.available())
			return;

		String command = Serial.readStringUntil('\n');

		if(command.indexOf("reset") != -1)
			return ESP.restart();

		if(command.indexOf("home") != -1)
			return reset();
	}

	double getTime(){
		return (esp_timer_get_time() - startTime) * 1e-6;
	}

	// SENOIDE COM ENVELOPE EM COSSENO PARA PARTIR E CHEGAR EM 0 SEM TRANCO
	float getAngle(float t, float amplitude){
		float duration = STAGE * 1e-6f;
		float envelope = t < RAMP            ? 0.5f*(1 - cosf(PI*t/RAMP)) :
		                 t > duration - RAMP ? 0.5f*(1 - cosf(PI*(duration - t)/RAMP)) : 1.0f;
		return amplitude * envelope * sinf(2*PI*frequency*t);
	}

	void print(){
		static int64_t lastPrintTime = 0;

		if(esp_timer_get_time() - lastPrintTime < (int64_t)(dt*1000000))
			return;

		lastPrintTime = esp_timer_get_time();
		char buffer[64];
		int len = snprintf(buffer, sizeof(buffer), "{\"t\":%.3f,\"pitch\":%.2f,\"roll\":%.2f}\n", getTime(), pitch.get(), roll.get());
		Serial.write((uint8_t*) buffer, len);
	}
};


Movement movement;


void setup(){
	Serial.begin(115200);
	Serial.setTimeout(10);    // ms
	delay(700);
	movement.setup();
}

void loop(){
	movement.listen();
	movement.handle();
	movement.print();
}