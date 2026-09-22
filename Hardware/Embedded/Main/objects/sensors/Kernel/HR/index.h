#ifndef KERNEL_MODEL_HR_H
#define KERNEL_MODEL_HR_H
#include <HardwareSerial.h>
#include <cstdint>


class KernelModelHR{
  private:
	HardwareSerial* uart;

	int32_t extract_i32(int pos){
		return (int32_t) (((uint32_t) packet[pos]) | ((uint32_t) packet[pos+1] << 8) | ((uint32_t) packet[pos+2] << 16) | ((uint32_t) packet[pos+3] << 24));
	}

	int16_t extract_i16(int pos){
		return (int16_t) (packet[pos] | (packet[pos+1] << 8));
	}

	uint16_t extract_u16(int pos){
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
		if(!checksumValid())
			{Serial.println("Checksum inválido no HR Data!"); return false;}

		yaw   = extract_i32(6);  // Orientation Angles 
		pitch = extract_i32(10); 
		roll  = extract_i32(14); 

		wx = extract_i32(18);    // Angular Rates 
		wy = extract_i32(22);
		wz = extract_i32(26);

		ax = extract_i32(30);    // Accelerations 
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
		const uint8_t CMD_MODE[9] = {0xAA, 0x55, 0x00, 0x00, 0x07, 0x00, 0x81, 0x88, 0x00}; 
		Serial.print("\nKernel Started -> "); 
		Serial.println("Activation CMD Sent");
		uart->write(CMD_MODE, 9);
		delay(1000);
	}
};

#endif
