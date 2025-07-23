#include <Servo.h>


class AsyncServo{
    public:
    Servo servo = Servo();
    const float velocity;
    volatile float target;
    float current;
    int pin;
    
    AsyncServo(int pin_, float vel=15): 
        pin(pin_), 
        velocity(vel){}

    void setup(){
        servo.attach(pin);
        set(0);
        target = 0;
    }

    void set(const float angle){
        servo.write(angle);
    }

    void update(const float value){
        target = constrain(value, 0, 180);
        Serial.println("angle update: " + String(target) + "º");
    }

    float get(){
        return current;
    }

    void handle(){
        static unsigned long startTime = millis();
        static const int dt = 50;

        if(millis() - startTime < dt)
            return;
        
        startTime = millis();
        const float angle = velocity * (dt / 1000.00); // º/s * s = º

        if(abs(target - current) < angle){
            current = target;
            return set(current);
        }
            
        if(target > current){
            current += angle;
            return set(current);
        }

        current -= angle;
        set(current);
    }
};

AsyncServo servo = AsyncServo(10, 60);

void setup(){
    Serial.begin(9600);
    servo.setup();

    Serial.println("iniciado, digite no terminal para iniciar");
    delay(1500);

    while(!Serial.available())
        continue;
}

void loop(){
    static unsigned long startTime;
    static int index = 0;
    static const int size = 12;
    static const int steps[size] = {90, 135, 40, 120, 75, 50, 95, 135, 40, 60, 90, 120}; 
    static const int step = steps[0];
    servo.handle();

    if(millis() - startTime < 5000)
        return;

    startTime = millis();
    index = (index < size - 1) ? index + 1 : 0;
    servo.update(steps[index]);
}
