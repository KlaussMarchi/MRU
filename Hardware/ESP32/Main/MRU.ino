
StaticJsonDocument<256>& getMRU(){
    static StaticJsonDocument<256> data;
    sensor1.update();
    sensor2.update();
    
    data["time"] = sensor1.info.time;
    data["ax"] = sensor1.info.a.x;
    data["ay"] = sensor1.info.a.y;
    data["az"] = sensor1.info.a.z;
    data["vx"] = sensor1.info.v.x;
    data["vy"] = sensor1.info.v.y;
    data["vz"] = sensor1.info.v.z;
    data["x"]  = sensor1.info.p.x;
    data["y"]  = sensor1.info.p.y;
    data["z"]  = sensor1.info.p.z;
    data["wx"] = sensor1.info.w.x;
    data["wy"] = sensor1.info.w.y;
    data["wz"] = sensor1.info.w.z;
    return data;
}
