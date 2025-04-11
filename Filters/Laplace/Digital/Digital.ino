
float filter(float input){
    static unsigned long startTime;
    static const byte xSize=3, ySize=3;
    static float Xn[xSize] = {0};
    static float Yn[ySize] = {0};

    if(millis() - startTime < 100)
        return Yn[0];

    startTime = millis();

    for(byte n=xSize-1; n>0; n--) 
        Xn[n] = Xn[n-1];
    
    for(byte n=ySize-1; n>0; n--) 
        Yn[n] = Yn[n-1];

    Xn[0] = input;
    Yn[0] = Xn[0]*(0.000944) + Xn[1]*(0.001888) + Xn[2]*(0.000944) + Yn[1]*(1.911226) + Yn[2]*(-0.915003);
    return Yn[0];
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
