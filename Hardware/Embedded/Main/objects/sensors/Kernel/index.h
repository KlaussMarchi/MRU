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

// FATORES DO ICD QUE LEVAM CADA CAMPO DO PACOTE A m/s^2, graus/s, graus, QUATERNION UNITARIO E graus C
struct KernelScale{
	float accel, gyro, angle, quat, temperature;
};


// UM PARAMETRO DA FLASH DO KERNEL (TABELA 5.24 DO ICD): ID, TAMANHO EM BYTES E VALOR
struct KernelParameter{
	uint16_t id;
	uint8_t size;
	uint16_t value;
};


class KernelSensor {
  private:
	unsigned long lastUpdate;
	uint8_t rx_buffer[60];
	HardwareSerial* uart;

  public:
	static constexpr float G0      = 9.8106f;    // m/s^2 POR g, NOTA DO ICD 1.42
	static constexpr float RATE    = 200.0f;     // Hz DE SAIDA: DIVISOR DE 2000, MEDIA DE 10 AMOSTRAS INTERNAS
	static constexpr uint32_t BAUD = 460800;     // HR DE 60 BYTES A 200 Hz OCUPA 29% (FORMULA 5.1 DO ICD)
	static constexpr int ANSWER    = 300;        // ms DE ESPERA PELA RESPOSTA DO ReadRAM
	static constexpr uint32_t BAUDS[4] = {BAUD, 115200, 230400, 921600};    // ONDE PROCURAR O KERNEL: O NOSSO, O DE FABRICA E OS VIZINHOS
	static constexpr uint16_t ALIGNMENT = 0x023A;    // Alignment_Angles: PROA, PITCH E ROLL EM float

	static constexpr KernelScale SCALE[3] = {
		{G0*1e-6f,   1e-5f, 1e-3f, 0.0f,  0.1f},    // HR: g*1e6, graus/s*1e5, graus*1e3
		{0.0f,       0.0f,  1e-2f, 1e-4f, 0.1f},    // QT: graus*1e2, quaternion*1e4
		{G0/4000.0f, 0.02f, 1e-2f, 0.0f,  0.1f}     // OR: g*4000, graus/s*50, graus*1e2
	};

	// O QUE O FIRMWARE GARANTE NA FLASH DO KERNEL A CADA BOOT, O BAUD PRIMEIRO PORQUE ELE LIMITA A TAXA
	static constexpr KernelParameter PARAMETERS[4] = {
		{0x03B2, 1, 0x09},    			 // Baud_Rate: 460800, VALE DEPOIS DO CommitBaudRate
		{0x0012, 2, (uint16_t) RATE},    // Data_Rate em Hz
		{0x03D0, 1, 0x01},    // Output_Variant: MEDIA DAS AMOSTRAS DE 2 kHz, O ANTI-ALIASING DA DECIMACAO
		{0x03D7, 1, 0x02}     // LPF_Bandwidth: 66 Hz ANTES DA MEDIA, BEM ACIMA DO MOVIMENTO DO NAVIO
	};

	int32_t ax, ay, az;
	int32_t wx, wy, wz;
	int32_t q0, q1, q2, q3;
	int32_t pitch, roll, yaw;
	int16_t temperature;
	float alignment[3] = {NAN, NAN, NAN};    // O QUE O KERNEL APLICA DESDE QUE LIGOU; NAN SE ELE NAO RESPONDEU

	KernelModelOrientation ort;
	KernelModelQuaternion qt;
	KernelModelHR hr;

	byte mode = HR_MODE;
	bool header;
	int index;

	int64_t packetStartTime = esp_timer_get_time();
	int64_t lastAckTime     = 0;    // NENHUM PACOTE AINDA: O PROCESSAMENTO ESPERA O PRIMEIRO

	bool working = false;
	uint32_t baud = BAUD;
	int tx_pin, rx_pin;

	KernelSensor(int tx, int rx):
		uart(new HardwareSerial(1)), ort(uart), qt(uart), hr(uart){
			tx_pin = tx;
			rx_pin = rx;
		}

	void setup(){
		if(mode > OR_MODE)    // CONFIGURACAO FORA DOS TRES MODOS: A TABELA DE ESCALA SAIRIA DO VETOR
			mode = HR_MODE;

		uart->setRxBufferSize(4096);    // ~80 ms DE PACOTES A 460800: O LACO PODE ATRASAR SEM PERDER AMOSTRA

		if(connect()){
			configure();
			ask(ALIGNMENT, 12, alignment);    // ANTES DO STREAM: COM ELE RODANDO A RESPOSTA SE PERDE NOS PACOTES
		}

		Serial.println("Kernel Mode: " + toString());
		Serial.printf("Kernel Align: proa %.1f, pitch %.1f, roll %.1f\n", alignment[0], alignment[1], alignment[2]);
		Serial.printf("pins tx=%d and rx=%d | %lu bps | %.0f Hz\n", tx_pin, rx_pin, (unsigned long) baud, RATE);
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

			ax = hr.ax; ay = hr.ay; az = hr.az;
			wx = hr.wx; wy = hr.wy; wz = hr.wz;

			pitch = hr.pitch; roll = hr.roll; yaw = hr.yaw;
			temperature = hr.temperature;
		}

		if(mode == QT_MODE){
			memcpy(qt.packet, rx_buffer, qt.PKT_LEN);
			working = qt.update();

			q0 = qt.q0; q1 = qt.q1; q2 = qt.q2; q3 = qt.q3;
			pitch = qt.pitch; roll = qt.roll; yaw = qt.yaw;
			temperature = qt.temperature;
		}

		if(mode == OR_MODE){
			memcpy(ort.packet, rx_buffer, ort.PKT_LEN);
			working = ort.update();

			ax = ort.ax; ay = ort.ay; az = ort.az;
			wx = ort.wx; wy = ort.wy; wz = ort.wz;

			pitch = ort.pitch; roll = ort.roll; yaw = ort.yaw;
			temperature = ort.temperature;
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

	// PROCURA O BAUD EM QUE O KERNEL RESPONDE, PARANDO ANTES O STREAM QUE UM BOOT ANTERIOR DEIXOU RODANDO
	bool connect(){
		const uint8_t stop[1] = {0xFE};
		uint16_t value = 0;

		uart->begin(BAUD, SERIAL_8N1, rx_pin, tx_pin);

		for(const uint32_t candidate : BAUDS){
			uart->updateBaudRate(candidate);
			baud = candidate;
			command(stop, 1);
			delay(50);

			if(ask(PARAMETERS[1].id, PARAMETERS[1].size, &value))
				return true;
		}

		Serial.println("Kernel nao respondeu em nenhum baud");
		uart->updateBaudRate(BAUD);
		baud = BAUD;
		return false;
	}

	// GRAVA NA FLASH DO KERNEL SO O PARAMETRO QUE DIFERE: A FLASH TEM CICLOS LIMITADOS
	void configure(){
		const uint8_t commit[1] = {0xC2};    // CommitBaudRate: O BAUD NOVO VALE SEM DESLIGAR

		for(const KernelParameter& parameter : PARAMETERS){
			uint16_t value = 0;

			if(ask(parameter.id, parameter.size, &value) && value == parameter.value)
				continue;

			const uint8_t payload[8] = {0xB2, 0xFF, (uint8_t) parameter.id, (uint8_t) (parameter.id >> 8), parameter.size, 0x00, (uint8_t) parameter.value, (uint8_t) (parameter.value >> 8)};
			command(payload, 6 + parameter.size);
			Serial.printf("Kernel: parametro 0x%04X gravado com %u\n", parameter.id, parameter.value);
			delay(200);

			if(parameter.id != PARAMETERS[0].id)
				continue;

			command(commit, 1);
			delay(100);
			uart->updateBaudRate(BAUD);
			baud = BAUD;
		}
	}

	// LE UM PARAMETRO DA RAM DO KERNEL NO TIPO DELE, LSB PRIMEIRO; A RESPOSTA E AA 55 01 B1, TAMANHO, VALOR E SOMA
	bool ask(const uint16_t id, const uint8_t size, void* value){
		const uint8_t header[4]  = {0xAA, 0x55, 0x01, 0xB1};
		const uint8_t payload[6] = {0xB1, 0xFF, (uint8_t) id, (uint8_t) (id >> 8), size, 0x00};
		uint8_t packet[20];    // ATE 12 BYTES DE VALOR: OS TRES float DO ALIGN
		int length = 0;

		while(uart->available())
			uart->read();

		command(payload, 6);
		const unsigned long startTime = Time::get();

		while(length < 8 + size && Time::get() - startTime < ANSWER){
			if(!uart->available())
				continue;

			packet[length] = uart->read();

			if(length < 4 && packet[length] != header[length]){    // FORA DO CABECALHO: RECOMECA, TALVEZ JA NESTE BYTE
				length    = (packet[length] == 0xAA) ? 1 : 0;
				packet[0] = 0xAA;
				continue;
			}

			length++;
		}

		if(length < 8 + size)
			return false;

		uint16_t checksum = 0;

		for(int i = 2; i < 6 + size; i++)
			checksum += packet[i];

		if(checksum != (packet[6 + size] | (packet[7 + size] << 8)))
			return false;

		memcpy(value, packet + 6, size);
		return true;
	}

	// AA 55 00 00, TAMANHO, PAYLOAD E A SOMA DOS BYTES A PARTIR DO TERCEIRO (TABELA 5.2 DO ICD)
	void command(const uint8_t* payload, const int size){
		const uint16_t length = size + 6;
		uint16_t checksum = 0;
		uint8_t packet[32];

		packet[0] = 0xAA; packet[1] = 0x55; packet[2] = 0x00; packet[3] = 0x00;
		packet[4] = length & 0xFF; packet[5] = length >> 8;
		memcpy(packet + 6, payload, size);

		for(int i = 2; i < 6 + size; i++)
			checksum += packet[i];

		packet[6 + size] = checksum & 0xFF;
		packet[7 + size] = checksum >> 8;
		uart->write(packet, 8 + size);
	}

	// CAMPOS DO PACOTE NO TIPO ORIGINAL, NA ORDEM DO STREAMER; O KERNEL NAO TEM HEAVE
	int read(double* values) const {
		values[0] = temperature;
		values[1] = pitch; values[2] = roll; values[3] = yaw;

		if(mode == QT_MODE){
			values[4] = q0; values[5] = q1; values[6] = q2; values[7] = q3;
			values[8] = 0;
			return 9;
		}

		values[4] = ax; values[5] = ay; values[6] = az;
		values[7] = wx; values[8] = wy; values[9] = wz;
		values[10] = 0;
		return 11;
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

	void align(byte position = ALIGN_DOWN){
		uint8_t payload[18] = {0xB2, 0xFF, 0x3A, 0x02, 0x0C, 0x00, 0,0,0,0, 0,0,0,0, 0,0,0,0};    // Alignment_Angles: proa, pitch e roll em float

		if(position == ALIGN_UPSIDE_DOWN){
			payload[6]  = 0x00; payload[7]  = 0x00; payload[8]  = 0x34; payload[9]  = 0x43; // H=180
			payload[14] = 0x00; payload[15] = 0x00; payload[16] = 0x34; payload[17] = 0x43; // R=180
		}

		else if (position == ALIGN_DOWN) {
			payload[10] = 0x00; payload[11] = 0x00; payload[12] = 0xB4; payload[13] = 0xC2; // P=-90
		}

		else if (position == ALIGN_UP) {
			payload[10] = 0x00; payload[11] = 0x00; payload[12] = 0xB4; payload[13] = 0x42; // P=90
		}

		command(payload, 18);
		delay(1000);
	}

	void reset() {
		header = false;
		index  = 0;
	}

	bool timeout(){
		return (header && (Time::get() - lastUpdate > 100));
	}

	String toString(){
		if(mode == HR_MODE)  return "HR Mode";
		if(mode == QT_MODE)  return "Quaternion Mode";
		if(mode == OR_MODE)  return "Orientation Mode";
		return "Unknown Mode";
	}
};

#endif
