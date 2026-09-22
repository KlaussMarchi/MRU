#ifndef KERNEL_MODEL_ORIENTATION_H
#define KERNEL_MODEL_ORIENTATION_H
#include <HardwareSerial.h>
#include <cstdint>


class KernelModelOrientation{
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

#endif
