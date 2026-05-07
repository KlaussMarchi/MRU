#ifndef SERIAL_H
#define SERIAL_H
#include <Arduino.h>
#include "../../../globals/constants.h"
#include "../../../globals/functions.h"
#include "../../../utils/text/index.h"
#include "../../../utils/listener/index.h"
#include "../../../utils/time/index.h"
#define CMD_MIN_SIZE 2


template<int CMD_MAX_SIZE> class NextSerial{
  private:
    Listener checkTimer = Listener(100);

  public:
    Text<CMD_MAX_SIZE> command;
    bool available    = false;
    const int timeout = 1000;
    Stream* uart      = &Serial2;
    unsigned long lastAckTime;
    int port = 2;
    int RX, TX;
    
    NextSerial(int rx, int tx):
        RX(rx), TX(tx){}
    
    void setup(){
        Serial2.begin(115200, SERIAL_8N1, RX, TX);
        Serial.printf("Serial2 Started at RX=%d e TX=%d\n", RX, TX);
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
        if(!checkTimer.ready())
            return;
        
        if(Serial.available() && port != 1)
            {uart = &Serial; port = 1; Serial.println("port changed to 1");}

        if(Serial2.available() && port != 2)
            {uart = &Serial2; port = 2; Serial.println("port changed to 2");}
        
        if(!uart->available())
            return;
        
        const unsigned long startTime = Time::get();
        reset();

        while(uart->available() && Time::get() - startTime < timeout){
            command.concat((char) uart->read());

            if(!uart->available())
                delayMicroseconds(2000);
        }
        
        clean();
        available   = command.length() > 0;
        lastAckTime = available ? Time::get() : lastAckTime;

        if(!available)
            clear(true);
    }

    void clean(){
        command.remove('\r');
        command.remove('\n');
        command.remove('\t');

        if(command.isEmpty() || command.length() < CMD_MIN_SIZE || command.length() > CMD_MAX_SIZE)
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