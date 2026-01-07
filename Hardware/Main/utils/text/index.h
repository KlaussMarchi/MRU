#ifndef TEXT_H
#define TEXT_H
#include <Arduino.h>
#include <cstring>


template<int SIZE> class Text{
  public:
    static const int limit = (SIZE - 1);
    char buffer[SIZE];
    int index;
    
    Text(void)
        {reset();}

    Text(char letter)
        {reset(); append(letter);}

    Text(const char* str) 
        {reset(); concat(str);}

    Text(const String& str) 
        {reset(); concat(str);}

    Text& operator+=(char c)
        {append(c); return *this;}

    Text& operator+=(const char* str)
        {concat(str); return *this;}

    Text& operator+=(const String& str)
        {concat(str); return *this;}

    void reset(){
        index = 0;
        buffer[0] = '\0';
    }

    const char* get() const {
        return buffer;
    }

    bool available() const {
        return index > 0;
    }

    void append(char c) {
        if(index >= limit)
            return;

        buffer[index++] = c;
        buffer[index]   = '\0';
    }

    void concat(const char* str) {
        while(*str && index < limit)
            append(*str++);
    }

    void concat(const String& str){
        for(int i=0; i<str.length(); i++)
            append(str.charAt(i));
    }

    void concat(char letter){
        append(letter);
    }

    void set(const char* value){
        reset();
        concat(value);
    }

    void set(const String& value){
        reset();
        concat(value);
    }

    void set(int pos, char value) {
        if(pos < 0 || pos >= limit)
            return;

        buffer[pos] = value;
    }

    void print(bool breakLine=true) const {
        breakLine ? Serial.println(buffer) : Serial.print(buffer);
    }

    String toString() const {
        return String(buffer);
    }

    bool contains(const char* key) const {
        return (find(key) != -1);
    }

    bool equals(const char* str) const {
        int len = 0;
        while (str[len] != '\0')
            len++;

        for(int x=0; x<index; x++)
            if(x >= len || buffer[x] != str[x]) 
                return false;
    
        return (len == index);
    }

    char charAt(int pos) const {
        return (pos >= 0 && pos < index) ? buffer[pos] : '\0';
    }

    int length() const {
        return index;
    }

    int find(const char* key) const {
        const char* p = strstr(buffer, key);
        return p ? int(p - buffer) : -1;
    }

    int find(char key) const {
        for(int x=0; x<index; x++)
            if(buffer[x] == key)
                return x;

        return -1;
    }

    bool isBlank(char c) const {
        return (c == ' ' || c == '\t' || c == '\r' || c == '\n');
    }

    bool isEmpty() const {
        if(length() == 0)
            return true;

        for(int x=0; x<index; x++)
            if(!isBlank(buffer[x]))
                return false;

        return true;
    }

    Text<SIZE> substring(int start, int end) const {
        Text<SIZE> out;
        if(start < 0)   start = 0;
        if(end > index) end = index;
        
        for(int i = start; i < end; ++i) 
            out.append(buffer[i]);
        
        return out;
    }

    void strip(){
        int start = 0;
        while (start < index && isBlank(buffer[start]))
            start++;
        
        int end = index - 1;
        while(end >= start && isBlank(buffer[end]))
            end--;
        
        int newLen = end - start + 1;
        if(newLen <= 0)
            {reset(); return;}

        memmove(buffer, buffer + start, newLen);
        index = newLen;
        buffer[index] = '\0';
    }

    void replace(const char* key, const char* value) {
        const int kLen = strlen(key);
        const int vLen = strlen(value);
        char temp[SIZE];
        int tIdx = 0;
        int rIdx = 0;

        while (rIdx < index && tIdx < limit){
            const bool c1 = (kLen > 0);
            const bool c2 = (rIdx <= index - kLen);
            const bool c3 = (strncmp(buffer + rIdx, key, kLen) == 0);

            if(c1 && c2 && c3){
                for (int j = 0; j < vLen && tIdx < limit; ++j)
                    temp[tIdx++] = value[j];
                
                rIdx += kLen;
                continue;
            } 
            
            temp[tIdx++] = buffer[rIdx++];
        }

        temp[tIdx] = '\0';
        memcpy(buffer, temp, tIdx + 1);
        index = tIdx;
    }

    void remove(char target){
        int write_index = 0;

        for(int read_index=0; read_index<index; read_index++){
            if(buffer[read_index] == target)
                continue;

            buffer[write_index++] = buffer[read_index];
        }
        
        index = write_index;
        buffer[index] = '\0';
    }

    void clean(){
        remove(' ');
        remove('\r');
        remove('\n');
        remove('\t');
        
        if(length() == 0)
            reset();
    }
};

#endif 
