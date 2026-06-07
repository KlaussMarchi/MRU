#ifndef KERNEL_H
#define KERNEL_H
#include <HardwareSerial.h>
#include <cmath>
#include <cstdint>
#include "../../../utils/time/index.h"
#include "heave/index.h"
#include "orientation/index.h"
#include "gyrocal/index.h"


#define ALIGN_FORWARD     0   
#define ALIGN_DOWN        1  // cabeça pra cima (measure em pé) - com barriguinha 
#define ALIGN_UP          2  // cabeça pra baixo (cabo pra baixo) 
#define ALIGN_RESET       3 
#define ALIGN_UPSIDE_DOWN 4



class KernelModelHR{
  private:
    HardwareSerial* uart;

    int32_t extract_i32(int pos) {
        return (int32_t) (((uint32_t) packet[pos]) | ((uint32_t) packet[pos+1] << 8) | ((uint32_t) packet[pos+2] << 16) | ((uint32_t) packet[pos+3] << 24));
    }

    int16_t extract_i16(int pos) {
        return (int16_t) (packet[pos] | (packet[pos+1] << 8));
    }

    uint16_t extract_u16(int pos) {
        return (uint16_t) (packet[pos] | (packet[pos+1] << 8));
    }

  public:
    static const int PKT_LEN = 60; // Pacote do HR tem 60 bytes de comprimento 
    uint8_t packet[PKT_LEN];
    
    int32_t ax, ay, az;
    int32_t wx, wy, wz;
    int32_t pitch, roll, yaw;
    float temperature;

    KernelModelHR(HardwareSerial* uart){
        this->uart = uart;
    }

    bool update(){
        if(!checksumValid()){
            Serial.println("Checksum inválido no HR Data!");
            return false;
        }
        
        yaw   = extract_i32(6);  // Orientation Angles 
        pitch = extract_i32(10); 
        roll  = extract_i32(14); 

        wx = extract_i32(18); // Angular Rates 
        wy = extract_i32(22);
        wz = extract_i32(26);

        ax = extract_i32(30); // Accelerations 
        ay = extract_i32(34);
        az = extract_i32(38);

        temperature = ((float) extract_i16(56)) / 10.0f; // Temperatura 
        return true;
    }

    bool checksumValid(){
        uint16_t recv_checksum = extract_u16(58);
        uint16_t calc_checksum = 0;
        
        for(int i = 2; i < 58; i++) 
            calc_checksum += packet[i];

        return (calc_checksum == recv_checksum);
    }

    void setup(){
        const uint8_t CMD_MODE[9] = { 0xAA, 0x55, 0x00, 0x00, 0x07, 0x00, 0x81, 0x88, 0x00 }; 
        
        Serial.print("\nKernel Started "); 
        Serial.println("Activation CMD Sent");
        uart->write(CMD_MODE, 9);
        delay(1000);
    }
};

class KernelModelQuaternion{
  private:
    HardwareSerial* uart;

    int16_t extract_i16(int pos) {
        return (int16_t) (packet[pos] | (packet[pos+1] << 8));
    }

    uint16_t extract_u16(int pos) {
        return (uint16_t) (packet[pos] | (packet[pos+1] << 8));
    }

  public:
    static const int PKT_LEN = 42;
    uint8_t packet[PKT_LEN];
    
    uint16_t yaw;
    int16_t pitch, roll;
    int16_t q0, q1, q2, q3;
    float temperature;

    KernelModelQuaternion(HardwareSerial* uart){
        this->uart = uart;
    }

    void setup(){
        const uint8_t CMD_MODE[9] = { 0xAA, 0x55, 0x00, 0x00, 0x07, 0x00, 0x82, 0x89, 0x00 }; 
        
        Serial.println("Kernel Started in Quaternion Mode");
        Serial.println("Activation CMD Sent");
        uart->write(CMD_MODE, 9);
        delay(1000);
    }

    bool update() {
        if(!checksumValid()) {
            Serial.println("Checksum inválido no Quaternion Data!");
            return false;
        }
        
        yaw   = extract_u16(6);  // Heading
        pitch = extract_i16(8);  // Pitch
        roll  = extract_i16(10); // Roll

        q0 = extract_i16(12); // Quaternion de Orientação * 10000
        q1 = extract_i16(14); 
        q2 = extract_i16(16); 
        q3 = extract_i16(18); 

        temperature = ((float) extract_i16(38)) / 10.0f; // Temperatura
        return true;
    }

    bool checksumValid() {
        uint16_t recv_checksum = extract_u16(40);
        uint16_t calc_checksum = 0;
        
        for(int i = 2; i < 40; i++) 
            calc_checksum += packet[i];

        return (calc_checksum == recv_checksum);
    }
};

class KernelModelOrientation {
  private:
    HardwareSerial* uart;

    int16_t extract_i16(int pos) {
        return (int16_t) (packet[pos] | (packet[pos+1] << 8));
    }

    uint16_t extract_u16(int pos) {
        return (uint16_t) (packet[pos] | (packet[pos+1] << 8));
    }

  public:
    static const int PKT_LEN = 42;
    uint8_t packet[PKT_LEN];
    
    uint16_t yaw;
    int16_t pitch, roll;
    int16_t wx, wy, wz;
    int16_t ax, ay, az;
    float temperature;

    KernelModelOrientation(HardwareSerial* uart){
        this->uart = uart;
    }

    void setup(){
        const uint8_t CMD_MODE[9] = { 0xAA, 0x55, 0x00, 0x00, 0x07, 0x00, 0x33, 0x3A, 0x00 }; 
        
        Serial.println("Kernel Started in Orientation Mode");
        Serial.println("Activation CMD Sent");
        uart->write(CMD_MODE, 9);
        delay(1000);
    }

    bool update() {
        if(!checksumValid()) {
            Serial.println("Checksum inválido no Orientation Data!");
            return false;
        }
        
        yaw   = extract_u16(6);  // Heading
        pitch = extract_i16(8);  // Pitch
        roll  = extract_i16(10); // Roll

        wx = extract_i16(12); // Angular Rates
        wy = extract_i16(14); 
        wz = extract_i16(16); 

        ax = extract_i16(18); // Accelerations
        ay = extract_i16(20); 
        az = extract_i16(22); 

        temperature = ((float) extract_i16(38)) / 10.0f; // Temperatura
        return true;
    }

    bool checksumValid() {
        uint16_t recv_checksum = extract_u16(40);
        uint16_t calc_checksum = 0;
        
        for(int i = 2; i < 40; i++) 
            calc_checksum += packet[i];

        return (calc_checksum == recv_checksum);
    }
};

class KernelSensor {
  private:
    unsigned long lastUpdate;
    uint8_t rx_buffer[60];
    HardwareSerial* uart;
    
  public:
    int32_t ax_raw, ay_raw, az_raw;
    int32_t wx_raw, wy_raw, wz_raw;
    int32_t q0_raw, q1_raw, q2_raw, q3_raw; 
    int32_t pitch_raw, roll_raw, yaw_raw;

    float ax, ay, az;
    float wx, wy, wz;
    float q0, q1, q2, q3; 
    float pitch, roll, yaw;

    float temperature;
    float heave;

    Heave heaveFilter;
    OrientationParser parser;
    GyroCalibrator gyrocal;

    KernelModelOrientation ort;
    KernelModelQuaternion qt;
    KernelModelHR hr;
    
    byte mode = HR_MODE; 
    bool header;
    int index;

    int64_t packetStartTime = esp_timer_get_time();
    int64_t lastAckTime      = esp_timer_get_time();

    bool working = false;
    int tx_pin, rx_pin;
    
    KernelSensor(int tx, int rx): 
        uart(new HardwareSerial(1)), qt(uart), hr(uart), ort(uart){
            tx_pin = tx;
            rx_pin = rx;
        }
    
    void setup(){
        uart->begin(115200, SERIAL_8N1, rx_pin, tx_pin);
        Serial.printf("Kernel Started at tx=%d and rx=%d\n", tx_pin, rx_pin);
        lastUpdate = Time::get();

        if(mode == HR_MODE)
            hr.setup();
        
        if(mode == QT_MODE)
            qt.setup();

        if(mode == OR_MODE)
            ort.setup();
        
        reset();
    }

    void align(byte position = ALIGN_DOWN){
        uint8_t cmd[26] = { 0xAA, 0x55, 0x00, 0x00, 0x18, 0x00, 0xB2, 0xFF, 0x3A, 0x02, 0x0C, 0x00, 0,0,0,0, 0,0,0,0, 0,0,0,0, 0,0 };
        
        if(position == ALIGN_UPSIDE_DOWN){
            cmd[12] = 0x00; cmd[13] = 0x00; cmd[14] = 0x34; cmd[15] = 0x43; // H=180
            cmd[20] = 0x00; cmd[21] = 0x00; cmd[22] = 0x34; cmd[23] = 0x43; // R=180
        } 
        
        else if (position == ALIGN_DOWN) {
            cmd[16] = 0x00; cmd[17] = 0x00; cmd[18] = 0xB4; cmd[19] = 0xC2; // P=-90
        } 
        
        else if (position == ALIGN_UP) {
            cmd[16] = 0x00; cmd[17] = 0x00; cmd[18] = 0xB4; cmd[19] = 0x42; // P=90
        }
        
        uint16_t checksum = 0;
        for (int i = 2; i < 24; i++) 
            checksum += cmd[i];
        
        cmd[24] = checksum & 0xFF; cmd[25] = (checksum >> 8) & 0xFF; 
        uart->write(cmd, 26);
        delay(1000);
    }

    bool timeout() {
        return (header && (Time::get() - lastUpdate > 100));
    }

    void handle(){
        if(timeout())
            return reset();

        while(uart->available()){
            uint8_t newByte = uart->read();
            lastUpdate = Time::get();

            if(!header){
                if(index == 0 && newByte == 0xAA) {
                    rx_buffer[0] = 0xAA;
                    index = 1;
                    packetStartTime = esp_timer_get_time();
                } 
                else if(index == 1 && newByte == 0x55) {
                    rx_buffer[1] = 0x55;
                    header = true;
                    index = 2;
                } 
                else {
                    index = 0;
                }

                continue;
            }

            int targetLen = getLength();
            
            if(index < targetLen)
                rx_buffer[index++] = newByte;
            
            if(index >= targetLen)
                update();
        }
    }

    int getLength() {
        if (mode == HR_MODE || mode == HR_MODE_ADJ) 
            return hr.PKT_LEN;
        
        if (mode == QT_MODE)
            return qt.PKT_LEN;

        if (mode == OR_MODE) 
            return ort.PKT_LEN;

        return 0;
    }

    void update(){
        int64_t now_us = esp_timer_get_time();
        float dt = (packetStartTime - lastAckTime) * 1e-6f;

        if(mode == HR_MODE){
            memcpy(hr.packet, rx_buffer, hr.PKT_LEN);
            working = hr.update();

            ax_raw = hr.ax;
            ay_raw = hr.ay;
            az_raw = hr.az;

            wx_raw = hr.wx;
            wy_raw = hr.wy;
            wz_raw = hr.wz;

            pitch_raw = hr.pitch;
            roll_raw  = hr.roll;
            yaw_raw   = hr.yaw;
            temperature = hr.temperature;

            ax = ax_raw / 1000000.0f;
            ay = ay_raw / 1000000.0f;
            az = az_raw / 1000000.0f;

            wx = wx_raw / 100000.0f;
            wy = wy_raw / 100000.0f;
            wz = wz_raw / 100000.0f;

            pitch = pitch_raw / 1000.0f;
            roll  = roll_raw / 1000.0f;
            yaw   = yaw_raw / 1000.0f;
            
            heaveFilter.update(ax, ay, az, pitch, roll, dt);
            heave = heaveFilter.getHeave();
        }

        if(mode == HR_MODE_ADJ){
            memcpy(hr.packet, rx_buffer, hr.PKT_LEN);
            working = hr.update();

            ax_raw = hr.ax;
            ay_raw = hr.ay;
            az_raw = hr.az;

            wx_raw = hr.wx;
            wy_raw = hr.wy;
            wz_raw = hr.wz;

            pitch_raw = hr.pitch;
            roll_raw  = hr.roll;
            yaw_raw   = hr.yaw;
            temperature = hr.temperature;

            ax = ax_raw / 1000000.0f;
            ay = ay_raw / 1000000.0f;
            az = az_raw / 1000000.0f;

            wx = wx_raw / 100000.0f;
            wy = wy_raw / 100000.0f;
            wz = wz_raw / 100000.0f;

            if(!gyrocal.calibrated){
                gyrocal.update(wx, wy, wz);
                
                if(working) 
                    lastAckTime = esp_timer_get_time();
                
                reset();
                return;
            }

            gyrocal.apply(wx, wy, wz);

            if(!parser.initialized)
                parser.start(ax, ay, az);

            parser.update(wx * (M_PI/180.f), wy * (M_PI/180.f), wz * (M_PI/180.f), ax, ay, az);        
            pitch = parser.pitch;
            roll  = parser.roll;
            yaw   = parser.yaw;
            
            heaveFilter.update(ax, ay, az, pitch, roll, dt);
            heave = heaveFilter.getHeave();
        }
        
        if(mode == QT_MODE){
            memcpy(qt.packet, rx_buffer, qt.PKT_LEN);
            working = qt.update();

            q0_raw = qt.q0;
            q1_raw = qt.q1;
            q2_raw = qt.q2;
            q3_raw = qt.q3;
            
            pitch_raw = qt.pitch;
            roll_raw  = qt.roll;
            yaw_raw   = qt.yaw;
            temperature = qt.temperature;

            q0 = q0_raw / 10000.0f;
            q1 = q1_raw / 10000.0f;
            q2 = q2_raw / 10000.0f;
            q3 = q3_raw / 10000.0f;
            
            pitch = pitch_raw / 100.0f;
            roll  = roll_raw / 100.0f;
            yaw   = yaw_raw / 100.0f;
        }

        if(mode == OR_MODE){
            memcpy(ort.packet, rx_buffer, ort.PKT_LEN);
            working = ort.update();

            ax_raw = ort.ax;
            ay_raw = ort.ay;
            az_raw = ort.az;

            wx_raw = ort.wx;
            wy_raw = ort.wy;
            wz_raw = ort.wz;

            pitch_raw = ort.pitch;
            roll_raw  = ort.roll;
            yaw_raw   = ort.yaw;
            temperature = ort.temperature;

            // Assumindo KG = 50 e KA = 4000
            ax = ax_raw / 4000.0f;
            ay = ay_raw / 4000.0f;
            az = az_raw / 4000.0f;

            wx = wx_raw / 50.0f;
            wy = wy_raw / 50.0f;
            wz = wz_raw / 50.0f;

            pitch = pitch_raw / 100.0f;
            roll  = roll_raw / 100.0f;
            yaw   = yaw_raw / 100.0f;
        }

        if(working) 
            lastAckTime = packetStartTime;
        
        reset();
    }

    void reset() {
        header = false;
        index  = 0;
    }
};

#endif