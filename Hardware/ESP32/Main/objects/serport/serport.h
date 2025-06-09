#ifndef SERPORT_H
#define SERPORT_H
#include <Arduino.h>
#include "../../global/constants.h"
#include "../../global/variables.h"
#include "../../global/functions.h"

#define TX_PIN 33
#define RX_PIN 26


template<int MAX_SIZE> struct SerialPort{
    char data[MAX_SIZE];
    bool available;
    int CMD_SIZE;
    byte length;
    
    void setup(const int size=MAX_SIZE){
        if(variables.serial_debug)
            Serial2.begin(115200, SERIAL_8N1, TX_PIN, RX_PIN);
        
        available = false;
        CMD_SIZE  = size;
    }

    bool awaiting(){
        static unsigned long startTime = espMillis();
        
        if(espMillis() - startTime < 100)
            return false;

        startTime = espMillis();
        const int size = variables.serial.available();

        if(size >= 5 && size <= CMD_SIZE - 1)
            return true;
        
        while(variables.serial.available())
            variables.serial.read();

        return false;
    }
    
    void listen(){
        if(!awaiting())
            return;

        length = 0;

        while(variables.serial.available()){
            const char newByte  = (char) variables.serial.read();
            const bool junkByte = (newByte == ' ' || newByte == '\n' || newByte == '\r'); 

            if(!junkByte && length < MAX_SIZE - 1)
                data[length++] = newByte;
            
            if(newByte == '!' || newByte == '\n')
                break;

            delay(1);
        }

        if(length < 5)
            return;
        
        data[length] = '\0';
        available    = true;
    }

    String getData(){
        if(!available)
            return "";
        
        available = false;
        return String(data);
    }

    void send(const String& msg, bool breakLine=false){
        if(variables.serial_debug)
            return;

        variables.serial.write(msg.c_str());

        if(breakLine)
            variables.serial.write("\r\n");
    }
    
    String getRaw(){
        length = 0;

        while(variables.serial.available()){
            const char newByte  = (char) variables.serial.read();
            const bool junkByte = (newByte == ' ' || newByte == '\n' || newByte == '\r'); 
            delay(1);

            if(!junkByte && length < MAX_SIZE - 1)
                data[length++] = newByte;
        }

        data[length] = '\0';
        return String(data);
    }
};


inline SerialPort<200> serport;
#endif