#ifndef KERNEL_MODEL_QUATERNION_H
#define KERNEL_MODEL_QUATERNION_H
#include <HardwareSerial.h>
#include <cstdint>


class KernelModelQuaternion{
  private:
	HardwareSerial* uart;

	int16_t extract_i16(int pos){
		return (int16_t) (packet[pos] | (packet[pos+1] << 8));
	}

	uint16_t extract_u16(int pos){
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

	bool update(){
		if(!checksumValid()) 
			{Serial.println("Checksum inválido no Quaternion Data!"); return false;}

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

	bool checksumValid(){
		uint16_t recv_checksum = extract_u16(40);
		uint16_t calc_checksum = 0;

		for(int i = 2; i < 40; i++) 
			calc_checksum += packet[i];

		return (calc_checksum == recv_checksum);
	}
};

#endif
