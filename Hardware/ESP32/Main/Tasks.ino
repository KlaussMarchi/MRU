
void protocolCheck(){
    if(!serport.available)
        return;

    String data = serport.getData();

    if(data == "stream"){
        Serial.println("Stream Started!");
        variables.stream = true;
    }
}

void sendLogsCheck(){
    static unsigned long startTime = espMillis();

    if(espMillis() - startTime < DT_INTERVAL || !variables.stream)
        return;
    
    startTime = espMillis();
    auto data = getMRU();
    
    if(variables.print_on)
        printJson(data);
}

