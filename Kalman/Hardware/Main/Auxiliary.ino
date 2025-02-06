
void plot(float value, int timeout){
    static unsigned long startTime = millis();

    if(millis() - startTime < timeout)
        return;

    startTime = millis();
    Serial.println(value);
}
