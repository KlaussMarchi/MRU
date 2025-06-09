
float flilter(const float Xn){
    static unsigned long startTime = millis();
    static const int dt = 100; // ms
    static float Xn1, Xn2;
    static float Yn1, Yn2;

    if(millis() - startTime < dt)
        return Yn1;

    startTime = millis();
    const float Yn = Xn*(0.027481) + Xn1*(0.000000) + Xn2*(-0.027481) + Yn1*(1.942707) + Yn2*(-0.945038);
    Xn2 = Xn1; Xn1 = Xn;
    Yn2 = Yn1; Yn1 = Yn;
    return Yn;
}

void setup(){
    Serial.begin(9600);
}

void loop(){
    static float setpoint = 0.0;

    if(Serial.available())
        setpoint = Serial.readString().toFloat();

    float output = filter(setpoint);
    plotStates(setpoint, output);
}

void plotStates(float setpoint, float output){
    static unsigned long startTime;
    static unsigned long attTime;

    if(millis() - startTime < 200)
        return;

    startTime = millis();
    Serial.println(String(setpoint) + "," + String(output) + ",0");
}
