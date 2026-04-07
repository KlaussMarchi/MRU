#ifndef KERNEL_H
#define KERNEL_H
#include <HardwareSerial.h>
#include "../../../utils/time/index.h"


class KernelSensor{
  private:
    // Comando alterado para Calibrated HR Data (0x81)
    static const int PKT_LEN = 60; 
    unsigned long lastUpdate;
    uint8_t packet[PKT_LEN];
    HardwareSerial* uart;
    bool header = false;
    int index;
    
  public:
    int32_t ax, ay, az;
    int32_t wx, wy, wz;
    int32_t q1, q2, q3, q4;
    int32_t pitch, roll, yaw;
    byte mode = ORIENTATION_MODE;

    unsigned long lastAck = Time::get();
    bool working = false;
    float temperature;
    int tx_pin, rx_pin;
    
    KernelSensor(int tx, int rx){
        uart = new HardwareSerial(1);
        tx_pin = tx;
        rx_pin = rx;
    }
    
    void setup(){
        uart->begin(115200, SERIAL_8N1, rx_pin, tx_pin);
        
        Serial.printf("Kernel Started at tx=%d and rx=%d\n", tx_pin, rx_pin);
        lastUpdate = Time::get();
        reset();
    }

    void setMode(){
        const uint8_t CMD_MODE[9] = {
            0xAA, 0x55, 0x00, 0x00, 0x07, 
            0x00, 0x81, 0x88, 0x00
        }; 

        const uint8_t CMD_ALIGN[26] = {
            0xAA, 0x55, 0x00, 0x00, 0x18, 0x00, // Header + Comprimento (24 bytes)
            0xB2, 0xFF, 0x3A, 0x02, 0x0C, 0x00, // Cmd SaveFlash + ID Alignment_Angles
            0x00, 0x00, 0x00, 0x00,             // Heading = 0.0
            0x00, 0x00, 0xB4, 0xC2,             // Pitch = -90.0
            0x00, 0x00, 0x00, 0x00,             // Roll = 0.0
            0x87, 0x03                          // Checksum cravado
        };
        
        Serial.println("Activation CMD Sent (Calibrated HR)");
        uart->write(CMD_MODE, 9);
        delay(1000);

        Serial.println("Alignment CMD Sent (Align Custom)");
        uart->write(CMD_ALIGN, 26);
        delay(1000);
    }

    int16_t extract_i16(int pos){ // Leitura de 16 bits (2 bytes)
        return (int16_t) (packet[pos] | (packet[pos+1] << 8));
    }

    uint16_t extract_u16(int pos){
        return (uint16_t) (packet[pos] | (packet[pos+1] << 8));
    }

    int32_t extract_i32(int pos){
        return (int32_t) (
            ((uint32_t)packet[pos]) | 
            ((uint32_t)packet[pos+1] << 8) | 
            ((uint32_t)packet[pos+2] << 16) | 
            ((uint32_t)packet[pos+3] << 24)
        );
    }

    bool timeout(){
        return (header && Time::get() - lastUpdate > 100);
    }

    bool checksum(){
        // O Checksum no pacote HR de 60 bytes fica na posição 58
        uint16_t recv_checksum = extract_u16(58);
        uint16_t calc_checksum = 0;
        
        for(int i = 2; i < 58; i++) 
            calc_checksum += packet[i];

        if(calc_checksum == recv_checksum)
            return true;

        Serial.println("Checksum inválido!");
        return false;
    }

    void handle(){
        if(timeout())
            return reset();

        if(!uart->available())
            return;
        
        uint8_t newByte = uart->read();
        lastUpdate      = Time::get();

        if(!header && newByte == 0xAA){
            packet[0] = 0xAA;
            index = 1;
            return;
        }

        if(!header && newByte == 0x55 && index == 1){
            packet[1] = 0x55;
            header = true;
            index  = 2;
            return;
        }

        if(index < PKT_LEN)
            packet[index++] = newByte;

        if(index >= PKT_LEN)
            working = update();

        if(working)
            lastAck = Time::get();
    }

    bool update(){
        if(!checksum())
            {reset(); return false;}
        
        // Byte 0: Header 0 (0xAA)
        // Byte 1: Header 1 (0x55)
        // Byte 2: Tipo da Mensagem

        // Byte 3: Identificador de Dados
        // Bytes 4 e 5: Tamanho da Mensagem
        // Byte 6 em diante: Aqui começa o Payload (Byte 0 da Tabela 5.10)

        // orientação (4 Bytes cada - posições 6 a 17)
        yaw = extract_i32(6);     // yaw   (bytes 6..9)
        pitch = extract_i32(10);  // pitch (bytes 10..13)
        roll  = extract_i32(14);  // roll  (bytes 14..17)

        // giroscópio (4 Bytes cada - posições 18 a 29)
        wx = extract_i32(18);   // wx (bytes 18..21)
        wy = extract_i32(22);   // wy (bytes 22..25)
        wz = extract_i32(26);   // wz (bytes 26..29)
        
        // aceleração (4 Bytes cada - posições 30 a 41)
        ax = extract_i32(30);  // ax (bytes 30..33)
        ay = extract_i32(34);  // ay (bytes 34..37)
        az = extract_i32(38);   // az (bytes 38..41)
        
        // temperatura (2 Bytes - posições 56 a 57)
        temperature = ((float) extract_i16(56)) / 10.00;
        
        reset();
        return true;
    }

    void reset(){
        header = false;
        index  = 0;
    }
};

#endif