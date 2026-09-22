#ifndef KERNEL_H
#define KERNEL_H
#include <HardwareSerial.h>
#include <cmath>
#include <cstdint>
#include <string>
#include "../../../utils/time/index.h"
#include "HR/index.h"
#include "quat/index.h"
#include "orient/index.h"


#define ALIGN_FORWARD     0   
#define ALIGN_DOWN        1  // cabeça pra cima (measure em pé) - com barriguinha 
#define ALIGN_UP          2  // cabeça pra baixo (cabo pra baixo) 
#define ALIGN_RESET       3 
#define ALIGN_UPSIDE_DOWN 4


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
	float heave = 0;

	float temperature;

	KernelModelOrientation ort;
	KernelModelQuaternion qt;
	KernelModelHR hr;

	byte mode = HR_MODE;
	bool calibrate = false;
	bool header;
	int index;

	int64_t packetStartTime = esp_timer_get_time();
	int64_t lastAckTime     = esp_timer_get_time();

	bool working = false;
	int tx_pin, rx_pin;

	KernelSensor(int tx, int rx): 
		uart(new HardwareSerial(1)), ort(uart), qt(uart), hr(uart){
			tx_pin = tx;
			rx_pin = rx;
		}

	void setup(){
		uart->begin(115200, SERIAL_8N1, rx_pin, tx_pin);
		Serial.println("Kernel Mode: " + toString());
		Serial.printf("pins tx=%d and rx=%d\n", tx_pin, rx_pin);
		lastUpdate = Time::get();

		if(mode == HR_MODE)
			hr.setup();

		if(mode == QT_MODE)
			qt.setup();

		if(mode == OR_MODE)
			ort.setup();

		reset();
	}

	void update(){
		if(mode == HR_MODE){
			memcpy(hr.packet, rx_buffer, hr.PKT_LEN);
			working = hr.update();

			ax_raw = hr.ax; ay_raw = hr.ay; az_raw = hr.az;
			wx_raw = hr.wx; wy_raw = hr.wy; wz_raw = hr.wz;

			pitch_raw   = hr.pitch; roll_raw = hr.roll; yaw_raw = hr.yaw;
			temperature = hr.temperature;

			if(!calibrate){
				ax = (ax_raw / 1000000.0f);
				ay = (ay_raw / 1000000.0f);
				az = (az_raw / 1000000.0f);

				wx = (wx_raw / 100000.0f);
				wy = (wy_raw / 100000.0f);
				wz = (wz_raw / 100000.0f);

				pitch = (pitch_raw / 1000.0f);
				roll  = (roll_raw  / 1000.0f);
				yaw   = (yaw_raw   / 1000.0f);
			}
		}

		if(mode == QT_MODE){
			memcpy(qt.packet, rx_buffer, qt.PKT_LEN);
			working = qt.update();

			q0_raw = qt.q0; q1_raw = qt.q1; q2_raw = qt.q2; q3_raw = qt.q3;
			pitch_raw = qt.pitch; roll_raw = qt.roll; yaw_raw = qt.yaw;
			temperature = qt.temperature;

			q0 = (q0_raw / 10000.0f);
			q1 = (q1_raw / 10000.0f);
			q2 = (q2_raw / 10000.0f);
			q3 = (q3_raw / 10000.0f);

			pitch = (pitch_raw / 100.0f);
			roll  = (roll_raw  / 100.0f);
			yaw   = (yaw_raw   / 100.0f);
		}

		if(mode == OR_MODE){
			memcpy(ort.packet, rx_buffer, ort.PKT_LEN);
			working = ort.update();

			ax_raw = ort.ax; ay_raw = ort.ay; az_raw = ort.az;
			wx_raw = ort.wx; wy_raw = ort.wy; wz_raw = ort.wz;

			pitch_raw = ort.pitch; roll_raw = ort.roll; yaw_raw = ort.yaw;
			temperature = ort.temperature;

			ax = (ax_raw / 4000.0f);
			ay = (ay_raw / 4000.0f);
			az = (az_raw / 4000.0f);

			wx = (wx_raw / 50.0f);
			wy = (wy_raw / 50.0f);
			wz = (wz_raw / 50.0f);

			pitch = (pitch_raw / 100.0f);
			roll  = (roll_raw  / 100.0f);
			yaw   = (yaw_raw   / 100.0f);
		}

		if(working)
			lastAckTime = packetStartTime;

		reset();
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

	int getLength(){
		if(mode == HR_MODE) 
			return hr.PKT_LEN;

		if(mode == QT_MODE)
			return qt.PKT_LEN;

		if(mode == OR_MODE)
			return ort.PKT_LEN;

		return 0;
	}

	bool timeout(){
		return (header && (Time::get() - lastUpdate > 100));
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
		heave = 0;
	}

	void reset() {
		header = false;
		index  = 0;
	}

	String toString(){
		if(mode == HR_MODE)  return calibrate ? "HR Mode (Calibration)" : "HR Mode";
		if(mode == QT_MODE)  return "Quaternion Mode";
		if(mode == OR_MODE)  return "Orientation Mode";
		return "Unknown Mode";
	}
};

#endif