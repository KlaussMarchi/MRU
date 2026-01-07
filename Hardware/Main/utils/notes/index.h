#ifndef NOTES_H
#define NOTES_H
#include <Arduino.h>
#include <LittleFS.h>


class Notes{
  public:
    const char* path;

    Notes(const char* PATH_NAME){
        path = PATH_NAME;
    }

    void setup(){
        if(LittleFS.begin()){
            Serial.println("LittleFS montado com sucesso!");
            return;
        }
        
        Serial.println("Erro ao montar LittleFS. Tentando formatar...");

        if(!LittleFS.format()){
            Serial.println("Falha ao formatar LittleFS!");
            return;
        }

        Serial.println("LittleFS formatado! Agora tentando inicializar novamente...");

        if(!LittleFS.begin()){
            Serial.println("Falha ao montar LittleFS após a formatação!");
            return;
        }

        Serial.println("LittleFS montado após formatação!");
    }

    int length(){
        File file = LittleFS.open(path, FILE_READ);
        
        if(!file)
            return -1;

        int size = file.size();
        file.close();
        return size;
    }

    String read(){
        File file = LittleFS.open(path, FILE_READ);

        if(!file){
            Serial.println("Erro ao abrir o arquivo para leitura");
            return ""; 
        }

        String content = file.readString();
        file.close();
        return content;
    }

    void append(const String& message){
        File file = LittleFS.open(path, FILE_APPEND);

        if(!file){
            Serial.println("Erro ao abrir o arquivo para adição");
            return;
        }

        if(!file.println(message))
            Serial.println("ERRO AO SALVAR TEXTO NO SPIFFS");

        file.close();
    }

    void write(const String& message) {
        File file = LittleFS.open(path, FILE_WRITE);
        
        if(!file){
            Serial.println("Erro ao abrir o arquivo para escrita");
            return;
        }

        if(!file.println(message))
            Serial.println("Erro ao escrever no arquivo");

        file.close();
    }

    String readlines(int n){
        File file = LittleFS.open(path, FILE_READ);
        if(!file){
            Serial.println("Erro ao abrir o arquivo para leitura em readlines");
            return "";
        }

        String result = "";
        for(int i = 0; i < n && file.available(); i++){
            String line = file.readStringUntil('\n');

            if(line.endsWith("\r"))
                line.remove(line.length() - 1);

            result += line;
            
            if(i < n - 1)
                result += '\n';
        }
        
        result.trim();
        file.close();
        return result;
    }
    
    bool droplines(int n){
        File file = LittleFS.open(path, FILE_READ);
        if(!file){
            Serial.println("Erro ao abrir o arquivo para leitura em droplines");
            return false;
        }

        File temp = LittleFS.open("/temp.txt", FILE_WRITE);
        if(!temp){
            Serial.println("Erro ao criar o arquivo temporário em droplines");
            file.close();
            return false;
        }

        for(int i = 0; i < n && file.available(); i++)
            file.readStringUntil('\n');
        
        const size_t bufferSize = 512;
        uint8_t buffer[bufferSize];
        while(file.available()){
            size_t bytesRead = file.read(buffer, bufferSize);
            temp.write(buffer, bytesRead);
        }

        file.close();
        temp.close();
        LittleFS.remove(path);
        LittleFS.rename("/temp.txt", path);
        return true;
    }
};

#endif