#ifndef SERIAL_H
#define SERIAL_H
#include <Arduino.h>
#include "../../../globals/constants.h"
#include "../../../globals/functions.h"
#include "../../../utils/text/index.h"
#include "../../../utils/listener/index.h"
#include "../../../utils/time/index.h"
#define CMD_MIN_SIZE 5


template<int CMD_MAX_SIZE> class NextSerial{
  public:
    Text<CMD_MAX_SIZE> command;
    bool available = false;
    int timeout    = 5000;
    Stream* uart = &Serial;
    unsigned long lastAckTime;
    int port  = 1;
    int RX, TX;
    
    NextSerial(int rx, int tx):
        RX(rx), TX(tx){}
    
    void setup(){
        Serial2.begin(115200, SERIAL_8N1, RX, TX);
        Serial.printf("Serial2 Started at RX=%d e TX=%d\n", RX, TX);

        Serial.write("$MICACK!");
        delay(100);
        
        Serial2.write("$MICACK!");
        delay(100);
    }
    
    void send(const char* msg, bool breakLine=true){
        uart->write(msg);

        if(breakLine)
            uart->write("\r\n");
    }

    void send(const String& msg, bool breakLine=true){
        uart->write(msg.c_str());

        if(breakLine)
            uart->write("\r\n");
    }

    void print(){
        Serial.println(available ? "(serial) received: " + command.toString() : "nothing received");
    }

    void await(const int ms){
        const unsigned long startTime = Time::get();

        while(Time::get() - startTime < ms)
            listen();
    }
    
    void listen(){
        static Listener timer = Listener(100);
        
        if(!timer.ready())
            return;
        
        if(Serial.available() >= CMD_MIN_SIZE  && port != 1)
            {uart = &Serial;  port = 1; Serial.println("port changed to 1");}

        if(Serial2.available() >= CMD_MIN_SIZE && port != 2)
            {uart = &Serial2; port = 2; Serial.println("port changed to 2");}

        const int size  = uart->available();
        const bool junk = (size < CMD_MIN_SIZE || size > CMD_MAX_SIZE);

        if(size == 0)
            return;
        
        if(!junk)
            reset();
        
        const unsigned long startTime = Time::get();
        while(uart->available() && Time::get() - startTime < timeout){
            const char letter = (char) uart->read();
            
            if(junk)
                continue;

            command.concat(letter);
            delay(1);
        }
        
        available   = (command.length() > 5 && !command.isEmpty());
        lastAckTime = available ? Time::get() : lastAckTime;
    }

    void clean(){
        command.remove('\r');
        command.remove('\n');
        command.remove('\t');

        if(command.length() < 5 || command.length() > CMD_MAX_SIZE)
            reset();
    }

    void clear(bool _reset=false){
        while(uart->available())
            read();

        if(_reset)
            reset();
    }

    char read(){
        char letter = (char) uart->read();

        if(!uart->available())
            delayMicroseconds(500);

        return letter;
    }

    void reset(){
        command.reset();
        available = false;
    }
};

#endif