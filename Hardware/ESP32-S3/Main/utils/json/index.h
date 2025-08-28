#ifndef JSON_H
#define JSON_H
#include <ArduinoJson.h>
#include <Preferences.h>


template<int SIZE> class Json{
  public:
    StaticJsonDocument<SIZE> data;

    void print() const{
        serializeJsonPretty(data, Serial);
        Serial.println('\n');
    }

    bool empty() const{
        return (data.template as<JsonObjectConst>().size() == 0);
    }

    bool parse(const char* jsonText){
        return !deserializeJson(data, jsonText);
    }

    bool parse(const String &jsonString){
        return !deserializeJson(data, jsonString);
    }

    void set(const char* key, const String &value){
        data[key] = value;
    }

    void set(const char* key, const char *value){
        data[key] = value;
    }
    
    void set(const char* key, int value){
        data[key] = value;
    }

    void set(const char* key, float value){
        data[key] = value;
    }

    void set(const char* key, bool value){
        data[key] = value;
    }

    void set(const char* key, const JsonDocument& other){
        data[key] = other.as<JsonVariantConst>();
    }
    
    bool download(const char* key){
        Preferences prefs;
        prefs.begin(key, false);
        String jsonString = prefs.getString("data", "{}");
        prefs.end();
        return parse(jsonString);
    }

    bool save(const char* key){
        Preferences prefs;
        prefs.begin(key, false);
        bool ok = prefs.putString("data", toString());
        prefs.end();
        return ok;
    }
    
    template <typename T>
    T get(const char* key) const{
        return data[key].template as<T>();
    }

    String toString() const{
        String output;
        serializeJson(data, output);
        return output;
    }
};


#endif