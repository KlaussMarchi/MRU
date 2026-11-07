#ifndef UPDATER_H
#define UPDATER_H
#include <Arduino.h>
#include <Update.h>
#include <esp_ota_ops.h>

// O CORE MARCA O FIRMWARE NOVO COMO BOM ANTES DO setup(): ASSIM ELE FICA EM PROVA ATE O confirm(), E SE CAIR ANTES O BOOTLOADER VOLTA PARA O ANTERIOR
extern "C" bool verifyRollbackLater(){
	return true;
}


size_t base64Decode(const char* input, uint8_t* output, const int size){
	auto decodeChar = [](char c) -> int {
		if (c >= 'A' && c <= 'Z') return c - 'A';
		if (c >= 'a' && c <= 'z') return c - 'a' + 26;
		if (c >= '0' && c <= '9') return c - '0' + 52;
		if (c == '+') return 62;
		if (c == '/') return 63;
		return -1;
	};

	size_t outputIndex = 0;
	int val  = 0;
	int valb = -8;

	for(int i = 0; i < size; i++){
		if(input[i] == '=')
			break;

		const int d = decodeChar(input[i]);

		if(d == -1)
			return 0;

		val  = ((val << 6) + d) & 0xFFFFFF;
		valb += 6;

		if(valb < 0)
			continue;

		output[outputIndex++] = static_cast<uint8_t>((val >> valb) & 0xFF);
		valb -= 8;
	}

	return outputIndex;
}


// CRC-32 IEEE EM PEDACOS: crc VEM DO PEDACO ANTERIOR, 0 NO PRIMEIRO
uint32_t updateCRC(const uint8_t* bytes, const size_t size, const uint32_t crc = 0){
	uint32_t value = ~crc;

	for(size_t i = 0; i < size; i++){
		value ^= bytes[i];

		for(int k = 0; k < 8; k++)
			value = (value >> 1) ^ (0xEDB88320 & (0 - (value & 1)));
	}

	return ~value;
}


// ATUALIZACAO PELA PORTA ATIVA: A PARTICAO EM USO SO MUDA DEPOIS DE CONFERIR TAMANHO E CRC, E QUALQUER ERRO VOLTA AO NORMAL SEM REINICIAR; O PROTOCOLO ESTA NO README
template <typename Parent> class Updater{
  private:
	Parent* device;
	bool confirmed = false;
	uint32_t size  = 0;
	uint32_t crc   = 0;
	uint32_t total = 0;
	uint32_t next  = 0;
	uint32_t sum   = 0;

  public:
	static constexpr int CHUNK = 2048;                 // BYTES POR BLOCO
	static constexpr int FRAME = (CHUNK/3 + 1)*4 + 32;    // BASE64 DO BLOCO, SEQUENCIA E CRC
	static constexpr unsigned long WAIT    = 15000;    // ms SEM RECEBER NADA: O APP SUMIU, VOLTA AO NORMAL
	static constexpr unsigned long CONFIRM = 10000;    // ms RODANDO SEM CAIR PARA O FIRMWARE NOVO SAIR DA PROVA

	bool active = false;    // A thread0 PARA ENQUANTO A FLASH E ESCRITA

	Updater(Parent* dev):
		device(dev){}

	void handle(){
		if(!confirmed && Time::get() > CONFIRM)
			confirm();
	}

	// CHEGOU ATE AQUI SEM CAIR, OU VAI REINICIAR POR COMANDO: O FIRMWARE EM USO E BOM E O REINICIO NAO PODE VIRAR ROLLBACK
	void confirm(){
		const esp_partition_t* running = esp_ota_get_running_partition();
		esp_ota_img_states_t state;
		confirmed = true;

		if(running == nullptr || esp_ota_get_state_partition(running, &state) != ESP_OK || state != ESP_OTA_IMG_PENDING_VERIFY)
			return;

		esp_ota_mark_app_valid_cancel_rollback();
		device->health.log('I', "firmware novo confirmado depois de %lu s", (unsigned long) (Time::get()/1000));
	}

	void start(const char* command){
		const char* field = strstr(command, "update:");
		char* end = nullptr;
		size = field ? strtoul(field + 7, &end, 10) : 0;
		crc  = (end && *end == ':') ? strtoul(end + 1, nullptr, 16) : 0;

		if(size == 0)
			return reply("$UPDATE ERROR:pedido invalido!");

		confirm();    // QUEM CONSEGUE PEDIR UMA ATUALIZACAO ESTA RODANDO: O REINICIO DELA NAO PODE VIRAR ROLLBACK

		if(!Update.begin(size))
			return reply((String("$UPDATE ERROR:") + Update.errorString() + "!").c_str());

		char* frame      = new char[FRAME + 1];
		uint8_t* decoded = new uint8_t[CHUNK + 4];
		total = next = sum = 0;
		active = true;
		delay(20);    // A thread0 SAI DO QUE ESTAVA FAZENDO
		device->health.log('I', "atualizacao: %lu bytes", (unsigned long) size);
		reply((String("$UPDATE READY:") + String(CHUNK) + "!").c_str());
		receive(frame, decoded);

		delete[] frame;
		delete[] decoded;
	}

	void receive(char* frame, uint8_t* decoded){
		Stream* uart   = device->telemetry.serial.uart;
		unsigned long last = Time::get();
		int length = -1;    // FORA DE UM QUADRO

		while(Time::get() - last < WAIT){
			if(!uart->available()){
				delay(1);
				continue;
			}

			const char letter = uart->read();
			last = Time::get();

			if(letter == '$'){    // UM QUADRO NOVO DESCARTA O QUE SOBROU DO ANTERIOR
				length = 0;
				continue;
			}

			if(length < 0 || letter == '\r' || letter == '\n')
				continue;

			if(letter != '!'){
				if(length < FRAME)
					frame[length] = letter;

				length++;
				continue;
			}

			if(length > FRAME){
				length = -1;
				retry("tamanho");
				continue;
			}

			frame[length] = '\0';
			length = -1;

			if(process(frame, decoded))
				return;
		}

		fail("sem dados por 15 s");
	}

	// true QUANDO A ATUALIZACAO TERMINOU, BEM OU MAL
	bool process(char* frame, uint8_t* decoded){
		if(strcmp(frame, "update_abort") == 0){
			device->health.log('W', "atualizacao cancelada pelo app");
			reply("$UPDATE ABORTED!");
			stop();
			return true;
		}

		if(strcmp(frame, "update_end") == 0)
			return finish();

		char* first  = strchr(frame, ',');
		char* second = first ? strchr(first + 1, ',') : nullptr;

		if(second == nullptr){
			reply("$UPDATE BUSY!");    // OUTRO COMANDO NO MEIO: A PORTA E DA ATUALIZACAO
			return false;
		}

		const uint32_t sequence = strtoul(frame, nullptr, 10);
		const uint32_t checksum = strtoul(first + 1, nullptr, 16);

		if(next > 0 && sequence == next - 1){    // O OK ANTERIOR SE PERDEU E O APP REPETIU: JA ESTA GRAVADO
			acknowledge(sequence);
			return false;
		}

		if(sequence != next){
			retry("ordem");
			return false;
		}

		const size_t bytes = base64Decode(second + 1, decoded, strlen(second + 1));

		if(bytes == 0 || bytes > CHUNK || updateCRC(decoded, bytes) != checksum){
			retry("crc");
			return false;
		}

		if(Update.write(decoded, bytes) != bytes){
			fail(Update.errorString());
			return true;
		}

		sum    = updateCRC(decoded, bytes, sum);
		total += bytes;
		next++;
		acknowledge(sequence);
		return false;
	}

	bool finish(){
		if(total != size || sum != crc){
			fail(total != size ? "tamanho nao confere" : "crc da imagem nao confere");
			return true;
		}

		if(!Update.end()){
			fail(Update.errorString());
			return true;
		}

		device->health.log('I', "atualizacao gravada: %lu bytes, reiniciando", (unsigned long) total);
		reply("$UPDATE DONE!");
		delay(300);
		device->reset();
		return true;
	}

	void fail(const char* reason){
		device->health.log('E', "atualizacao falhou: %s", reason);
		reply((String("$UPDATE ERROR:") + reason + "!").c_str());
		stop();
	}

	// O FIRMWARE EM USO CONTINUA: O BURACO NOS PACOTES NAO VIRA PULO NOS FILTROS NEM TRAVADA NO DIARIO
	void stop(){
		Update.abort();
		device->processing.reset();
		device->health.reset();
		active = false;
	}

	void acknowledge(const uint32_t sequence){
		reply((String("$UPDATE OK:") + String(sequence) + ":" + String(total) + "!").c_str());
	}

	void retry(const char* reason){
		reply((String("$UPDATE RETRY:") + String(next) + ":" + reason + "!").c_str());
	}

	void reply(const char* message){
		device->telemetry.serial.send(message);
	}
};

#endif
