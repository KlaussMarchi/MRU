#ifndef SETTINGS_H
#define SETTINGS_H

class Settings{
  public:
    Json<2048> params;

    void import(){
        params.download("preferences");
        
        if(params.empty())
            erase();
        
        params.print();
    }
    
    template<typename T> T get(const char* key, T default_value = T()) const {
        if(!params.exist(key))
            return default_value;

        T value = params.template get<T>(key);

        if constexpr (std::is_same<T, String>::value) {
            String lower = value;
            lower.toLowerCase();
            
            if(lower.isEmpty() || lower == "null" || lower == "nan")
                return default_value;
        }
        else if constexpr (std::is_floating_point<T>::value) {
            if(isnan(value))
                return default_value;
        }
        else if constexpr (std::is_pointer<T>::value) {
            if(value == nullptr)
                return default_value;
        }

        return value;
    }
    
    void save(){
        params.save("preferences");
    }

    bool isEnabled(const char* key){
        String value = params.template get<String>(key);
        value.trim();
        
        return (value == "false") ? false : 
               (value == "true")  ? true  : (value.toInt() > 0);
    }

    void erase(){
        Serial.println("Standard Settings Imported");
        params.clear();
        reset();
        save();
    }
    
    void reset(){
        params.data["server"] = "http://192.168.249.12:8000/api/";
        params.data["telemetry"]   = 0;
        params.data["kernel_mode"] = 0;
        params.data["ssid"] = "123456789";
        params.data["pass"] = "123456789";
        params.data["server_ip"] = "192.168.1.0";
        params.data["protocol"] = 0;
        params.data["autostream"] = false;
    }
};

#endif