void handleRoutes(){
    if(!espserver.available)
        return;

    if(espserver.getRequested("INFO"))
        onInfoRequest();
    
    //espserver.client.stop();
    espserver.available = false;
}

void onInfoRequest(){
    auto data = getMRU();
    espserver.send(jsonToString(data));
}
