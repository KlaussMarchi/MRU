
void protocolCheck(){
    if(!serport.available)
        return;

    String data = serport.getData();

    if(data == "stream")
        variables.stream = true;
}

void sendLogsCheck(){
    static unsigned long startTime = espMillis();

    if(espMillis() - startTime < 30 || !variables.stream)
        return;

    startTime = espMillis();
    auto data = getMRU();
    printJson(data);
}

