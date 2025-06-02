
StaticJsonDocument<256>& getMRU(){
    static StaticJsonDocument<256> data;
    sensor1.update();
    sensor2.update();

    const float t = (espMillis() - variables.startTime)/1000.0;
    auto s1 = sensor1.getData(); 
    auto s2 = sensor2.getData();

    data["time"] = t;
    data["ax"] = 10*sin(t) + 2;
    data["ay"] = 10*cos(t) + 2;
    data["az"] = 30;
    data["gx"] = 10;
    data["gy"] = 20;
    data["gz"] = 30;
    return data;
}
