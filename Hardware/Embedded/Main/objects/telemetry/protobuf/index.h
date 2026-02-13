#ifndef PROTOBUF_H
#define PROTOBUF_H
#include "../../../utils/time/index.h"
#include "../../../utils/text/index.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include <Wire.h>

#include <pb.h>
#include <pb_encode.h>
#include <telemetry.pb.h>

const uint16_t SERVER_PORT = 5005;


template <typename Parent> class Protobuf{
  private:
    Parent* device;
    WiFiUDP udp;

  public:
    unsigned long startTime;
    bool enabled = true;
    bool active  = false;
    int dt;
    Text<30> ssid;
    Text<30> pass;
    Text<30> server_ip;

    Protobuf(Parent* dev):
        device(dev){}

    void setup(){
        if(!enabled)
            return;

        ssid = device->settings.template get<String>("ssid");
        pass = device->settings.template get<String>("pass");
        server_ip = device->settings.template get<String>("server_ip");

        Serial.println();
        Serial.println("ssid: " + ssid.toString());
        Serial.println("pass: " + pass.toString());
        Serial.println("server_ip: " + server_ip.toString());
        Serial.println();
        
        const bool valid = (pass.length() > 5 && ssid.length() > 5 && server_ip.length() > 5);
        dt = (1.00/device->frequency)*1000;

        if(!valid){
            Serial.println("Configurações Protobuf Inválidas");
            enabled = false;
            return;
        }

        if(!connect()){
            Serial.println("Falha ao Conectar Protbuf com o Servidor");
            enabled = false;
            return;
        }
        
        udp.begin(0);
        startTime = Time::get();
        Serial.println("\rProtBuf Configurado!\n");
        delay(50);
    }

    bool connect(){
        WiFi.mode(WIFI_STA);
        WiFi.begin(ssid.get(), pass.get());
        Serial.print("Conectando ao WiFi");
        int index = 0;

        while(WiFi.status() != WL_CONNECTED){
            index = (index + 1);
            delay(500);
            
            if(index < 12)
                continue;
            
            Serial.println("WiFi não conectado....");
            return false;
        }

        Serial.println("\nWiFi conectado!");
        Serial.print("IP: ");
        Serial.println(WiFi.localIP());
        return true;
    }

    void handle(){
        static Listener timer = Listener(dt);
        static bool started   = false;
        static int fails = 0;

        if(!started)
            {started = true; Serial.println("transmissão protbuf iniciada");}

        if(!timer.ready())
            return;
        
        uint8_t buffer[256];
        pb_ostream_t stream = pb_ostream_from_buffer(buffer, sizeof(buffer));

        ProtoData msg = ProtoData_init_zero;
        msg.device_id = (uint32_t) 1;
        msg.time = (float) ((Time::get() - startTime)/1000.00f);

        msg.ax = (float) device->sensors.kernel.a.x;
        msg.ay = (float) device->sensors.kernel.a.y;
        msg.az = (float) device->sensors.kernel.a.z;

        msg.wx = (float) device->sensors.kernel.w.x;
        msg.wy = (float) device->sensors.kernel.w.y;
        msg.wz = (float) device->sensors.kernel.w.z;

        msg.pitch = (float) device->sensors.kernel.o.pitch;
        msg.roll  = (float) device->sensors.kernel.o.roll;
        msg.yaw   = (float) device->sensors.kernel.o.yaw;

        if(!pb_encode(&stream, ProtoData_fields, &msg)) {
            Serial.print("Erro Protobuf encode: ");
            Serial.println(PB_GET_ERROR(&stream));
            return;
        }

        size_t len = stream.bytes_written;

        if(!udp.beginPacket(server_ip.get(), SERVER_PORT)){
            Serial.println("Falha em beginPacket");
            return;
        }

        udp.write(buffer, len);

        if(!udp.endPacket()){
            fails = (fails + 1);
            
            if(fails > 100){
                Serial.println("Falha ao enviar pacote UDP");
                fails = 0;
            }
        }
    }

    void set(bool value){
        startTime = Time::get();
        active    = (value && enabled);
    }
};

#endif
