#ifndef ARRAY_H
#define ARRAY_H
#include <Arduino.h>
#include <Preferences.h>
#include "../time/index.h"

template<int SIZE> struct Array{
    // Removida inicialização direta para evitar problemas de ordem de boot
    unsigned long startTime;
    static const int length = SIZE;

    Preferences preferences;
    float array[SIZE];
    float junk = 0.00; 
    
    int index   = 0;
    int timeout = 1000;
    float mean, std, rel;
    bool isFull = false;

    Array(){
        index = 0;
        junk  = 0;
        timeout = 1000;
        reset();
    }

    void update(){
        mean = getMean();
        std  = getStd(mean);
        rel  = getRel(mean, std);
    }

    void reset(){
        startTime = Time::get(); 
        index = 0;
        fill(junk);
        isFull = false;
        mean = 0; rel = 0; std  = 0;
    }

    float get(int i){
        if(abs(i) >= length)
            i = 0;

        if(i < 0)
            i = length - abs(i);
        
        return array[i];
    }

    void setJunk(float value){
        junk = value;
        reset();
    }

    void setTimeout(int value){
        timeout = value;
    }

    void fill(float value){
        for(int x=0; x<length; x++)
            array[x] = value;

        index = 0;
    }

    bool ready(){
        if(Time::get() - startTime < timeout)
            return false;

        startTime = Time::get();
        return true;
    }

    bool stable(float limit, bool calculate=false){
        if(calculate)
            update();

        return (rel <= limit);
    }

    int getSize(){
        int size = 0;
        for(int x=0; x<length; x++)
            if(array[x] != junk)
                size++;
        
        return size;
    }

    void append(float value){
        array[index++] = value;
        
        if(index >= length){
            index  = 0;
            isFull = true;
        }
    }

    float getMean(int first=0, int last=length){
        float sum   = 0.0;
        int counter = 0;

        for(int x=first; x<last; x++){
            sum     = sum + array[x];
            counter = counter + 1;
        }
        
        if(counter == 0) return 0;
        return (sum / counter);
    }

    float getStd(){
        return getStd(getMean());
    }

    float getStd(float meanVal){
        float sum = 0.0; 
        
        for(int x=0; x<length; x++)
            sum += (array[x] - meanVal) * (array[x] - meanVal);
        
        // Divisão por N-1 (ddof=1)
        float variance = sum / (length - 1);
        return sqrt(variance);
    }

    float getRel(float meanVal, float stdVal){
        if(!isFull || meanVal == 0)
            return 9999.9;

        return (stdVal / sqrt(length) / meanVal) * 100;
    }
    
    int getMin(){
        float value = 999999;
        for(int i=0; i<length; i++)
            if(get(i) < value)
                value = get(i);
        return value;
    }
    
    float getMax(){
        float value = -999999; // Inicia com negativo para garantir que ache o max real
        for(int i=0; i<length; i++)
            if(get(i) > value)
                value = get(i);
        return value;
    }

    float getMedian(){
        float temp[SIZE]; 
        int count = length;
        
        if(count == 0) return 0;
        
        for(int i = 0; i < count; i++)
            temp[i] = get(i);
        
        // Bubble Sort
        for(int i = 0; i < count - 1; i++){
            for(int j = 0; j < count - i - 1; j++){
                if(temp[j] > temp[j+1]) {
                    float swap = temp[j]; 
                    temp[j] = temp[j+1];
                    temp[j+1] = swap;
                }
            }
        }
        
        return temp[count / 2];
    }
    
    void print(){
        Serial.print(F("(array) values: ["));
        for(int i = 0; i < length; i++){
            Serial.print(array[i]);
            if(i < length - 1) Serial.print(F(", "));
        }
        Serial.println(F("]"));
    }
    
    void download(const char* folder){
        preferences.begin(folder, false);
        preferences.getBytes("buffer", array, sizeof(array));
        index = preferences.getInt("index", 0);
        preferences.end();
    }
    
    void save(const char* folder){
        preferences.begin(folder, false);
        preferences.putBytes("buffer", array, sizeof(array));
        preferences.putInt("index", index);
        preferences.end();
    }
};

#endif