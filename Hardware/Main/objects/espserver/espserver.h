#ifndef ESPSERVER_H
#define ESPSERVER_H

#include <WiFi.h>
#include <esp_wifi.h>
#include <HTTPClient.h>
#include "../../global/variables.h"
#include "../../global/functions.h"
#include "../../global/constants.h"


struct EspServer {
    WiFiServer server;
    WiFiClient client;
    String request;
    bool available = false;

    void connect(const char* ssid, const char* pass) {
        unsigned long startTime = espMillis();
        WiFi.mode(WIFI_STA);

        esp_wifi_set_protocol(WIFI_IF_STA, WIFI_PROTOCOL_11B | WIFI_PROTOCOL_11G | WIFI_PROTOCOL_11N);
        esp_wifi_set_bandwidth(WIFI_IF_STA, WIFI_BW_HT20);
        esp_wifi_set_ps(WIFI_PS_NONE);
        WiFi.setTxPower(WIFI_POWER_19_5dBm);
        WiFi.begin(ssid, pass);

        while((espMillis() - startTime) < 2000) {
            if (WiFi.status() == WL_CONNECTED)
                break;
            
            delay(100);
        }

        if(WiFi.status() == WL_CONNECTED) {
            Serial.print("Conectado! IP do ESP32: ");
            Serial.println(WiFi.localIP());
        } 
        else {
            Serial.print("Falha ao conectar no Wi-Fi");
            Serial.println();
        }

        server.begin();
    }

    void listen(){
        static unsigned long startTime = espMillis();

        if(espMillis() - startTime < 30)
            return;

        startTime = espMillis();
        client    = server.available();

        if(!client)
            return;

        request = "";

        while(client.available()){
            char letter = client.read();
            request.concat(letter);
        }
        
        available = request.length() > 2;
    }

    void send(const String& data) {
        client.print(
            "HTTP/1.1 200 OK\r\n"
            "Access-Control-Allow-Origin: *\r\n"
            "Content-Type: text/plain\r\n"
            "Connection: close\r\n"
            "\r\n"
        );

        client.print(data);
    }

    bool getRequested(const char* route){
        String prefix = String("GET /") + route;
        return request.startsWith(prefix);
    }
};


inline EspServer espserver;
#endif
