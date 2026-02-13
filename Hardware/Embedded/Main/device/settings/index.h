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
    
    template<typename T> T get(const char* key) const {
        return params.template get<T>(key);
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
        params.data["telemetry"] = 0;
        params.data["ssid"] = "123456789";
        params.data["pass"] = "123456789";
        params.data["server_ip"] = "192.168.1.0";
    }
};

#endif