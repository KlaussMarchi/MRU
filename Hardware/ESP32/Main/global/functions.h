#ifndef FUNCTIONS_H
#define FUNCTIONS_H
#include "constants.h"
#include "variables.h"

unsigned long espMillis(){
    return esp_timer_get_time()/1000;
}

bool strContains(const String &str, const String &substr){
    return (str.indexOf(substr) != -1);
}

String jsonToString(const JsonDocument& jsonObj){
    String jsonString;
    serializeJson(jsonObj, jsonString); 
    return jsonString;
}

bool stringToJson(String &jsonString, JsonDocument& doc){
    DeserializationError error = deserializeJson(doc, jsonString);

    if(error)
        return false;

    return true;
}

void printJson(JsonDocument& doc){
    serializeJson(doc, Serial);
    Serial.println();
}

#endif