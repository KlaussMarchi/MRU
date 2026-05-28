#ifndef UPDATER_H
#define UPDATER_H
#include <Arduino.h>
#include <Update.h>
#include <SPI.h>


size_t base64Decode(const char* input, uint8_t* output, const int size){
    auto decodeChar = [](char c) -> int {
        if (c >= 'A' && c <= 'Z') return c - 'A';
        if (c >= 'a' && c <= 'z') return c - 'a' + 26;
        if (c >= '0' && c <= '9') return c - '0' + 52;
        if (c == '+') return 62;
        if (c == '/') return 63;
        return -1;
    };

    size_t outputIndex = 0;
    int val  = 0;
    int valb = -8; 

    for (size_t i = 0; i<size; i++){
        if (isspace(static_cast<unsigned char>(input[i])))
            continue;

        if (input[i] == '=')
            break;

        int d = decodeChar(input[i]);

        if (d == -1)
            continue;

        val  = (val << 6) + d;
        valb += 6;

        if (valb < 0)
            continue;
            
        output[outputIndex++] = static_cast<uint8_t>((val >> valb) & 0xFF);
        valb -= 8;
    }

    return outputIndex;
}


template <typename Parent> class Updater{
  private:
    Parent* device;
    int percent;

  public:
    
    Updater(Parent* dev): 
        device(dev){}

    void start(){
        const unsigned long startTime = Time::get();
        static const int CHUNK_SIZE   = (1.4)*2048; 
        
        device->telemetry.serial.send("__STARTING_UPDATE__", true); 
        finished(true);

        if(!Update.begin(UPDATE_SIZE_UNKNOWN)){
            device->telemetry.serial.send("error to begin", true);
            return;
        }

        while(!device->telemetry.serial.uart->available()){
            if(Time::get() - startTime < 35000)
                {delay(1); continue;}

            device->telemetry.serial.send("error to wait", true);
            return;
        }
        
        char* chunk      = new char[CHUNK_SIZE];
        uint8_t* decoded = new uint8_t[CHUNK_SIZE];

        bool start = false;
        int index  = 0;

        while(!finished(false)){
            if(!device->telemetry.serial.uart->available()){
                delay(1);
                continue;
            }
            
            char newChar = device->telemetry.serial.uart->read();
            
            if(!start){ // ESPERA O CHAR DE INICIALIZAÇÃO
                if(newChar != '$')
                    continue;
                
                start = true;
                index = 0;
                continue;
            }

            if(newChar != '!'){ // PREENCHE O VETOR COM UPDATE
                if(index < CHUNK_SIZE - 1){ 
                    chunk[index] = newChar;
                    index++;
                }

                continue;
            }

            const int length = index;
            size_t size    = base64Decode(chunk, decoded, length);
            size_t written = Update.write(decoded, size);
            device->telemetry.serial.send("__WRITTEN__", true);

            if(size == 0 || written != size){
                device->telemetry.serial.send("error to write size", true);
                delete[] chunk;
                delete[] decoded;
                return;
            }

            start = false;
            index = 0;
        }

        delete[] chunk;
        delete[] decoded;

        if(Update.end(true)){
            Serial.println("concluido! reiniciando");
            ESP.restart();
        }
        
        Serial.println("Erro ao atualizar");
    }

    bool finished(bool reset){
        static unsigned long lastUpdate;

        if(device->telemetry.serial.uart->available() || reset)
            lastUpdate = Time::get();

        return (Time::get() - lastUpdate > 10000);
    }    
};

#endif