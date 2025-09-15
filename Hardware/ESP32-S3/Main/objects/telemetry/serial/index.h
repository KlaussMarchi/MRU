#ifndef SERIAL_H
#define SERIAL_H
#include <Arduino.h>
#include "../../../globals/constants.h"
#include "../../../globals/functions.h"
#include "../../../utils/text/index.h"
#include "../../../utils/listener/index.h"
#include "../../../utils/time/index.h"
#define CMD_MIN_SIZE 5


template<int CMD_SIZE> class NextSerial{
  public:
    Text<CMD_SIZE> command;
    bool available = false;
    int timeout    = 5000;
    Stream& uart;
    
    NextSerial(Stream& ser):
        uart(ser){}

    void send(const char* msg, bool breakLine=true){
        uart.write(msg);

        if(breakLine)
            uart.write("\r\n");
    }

    void send(const String& msg, bool breakLine=true){
        uart.write(msg.c_str());

        if(breakLine)
            uart.write("\r\n");
    }

    void print(){
        Serial.println(available ? "(serial) received: " + command.toString() : "nothing received");
    }

    void await(const int ms){
        const unsigned long startTime = Time::get();

        while(Time::get() - startTime < ms)
            listen();
    }

    void clean(){
        command.remove(' ');
        command.remove('\r');
        command.remove('\n');
        command.remove('\t');

        if(command.length() < 5 || command.length() > CMD_SIZE)
            reset();
    }
    
    void listen(){
        static Listener timer = Listener(100);
        
        if(!timer.ready())
            return;

        const int size  = uart.available();
        const bool junk = (size < CMD_MIN_SIZE || size > CMD_SIZE);

        if(size == 0)
            return;
        
        if(!junk)
            reset();
        
        const unsigned long startTime = Time::get();
        while(uart.available() && Time::get() - startTime < timeout){
            const char letter = (char) uart.read();
            
            if(junk)
                continue;

            command.concat(letter);
            delay(1);
        }
        
        available = (command.length() > 5 && !command.isEmpty());
    }

    void reset(){
        command.reset();
        available = false;
    }

};

#endif