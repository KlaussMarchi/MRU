#include <Arduino.h>
#include <fcntl.h>
#include <pty.h>
#include <termios.h>
#include <poll.h>
#include <sys/stat.h>
#include <random>
#define ARDUINOJSON_ENABLE_ARDUINO_STREAM 0
#include "../Main/Main.ino"

static const std::string STATE = getenv("MRU_STATE") ? getenv("MRU_STATE") : "/tmp/mru-host";    // PASTA COM OS PTY, A NVS, AS PARTICOES E AS FALHAS PEDIDAS
static constexpr int64_t PERIOD = 5000;      // us DO KERNEL A 200 Hz
static constexpr size_t BACKLOG = 4096;      // BYTES DO RX DA UART1
static char** arguments;


static std::string readFile(const std::string& path){
	std::ifstream file(path);
	std::stringstream buffer;
	buffer << file.rdbuf();
	std::string text = buffer.str();

	while(!text.empty() && isspace(text.back()))
		text.pop_back();

	return text;
}

static void writeFile(const std::string& path, const std::string& text){
	std::ofstream file(path);
	file << text;
}


PtyPort::PtyPort(const char* variable, bool blocks, const char* name): blocking(blocks){
	if(getenv(variable)){
		fd = atoi(getenv(variable));
		return;
	}

	int slave;
	char path[128];
	termios settings;

	if(openpty(&fd, &slave, path, nullptr, nullptr) != 0)
		exit(1);

	tcgetattr(slave, &settings);
	cfmakeraw(&settings);
	tcsetattr(slave, TCSANOW, &settings);
	fcntl(fd, F_SETFD, fcntl(fd, F_GETFD) & ~FD_CLOEXEC);
	setenv(variable, std::to_string(fd).c_str(), 1);
	mkdir(STATE.c_str(), 0755);
	writeFile(STATE + "/" + name, path);
}

void PtyPort::pump(){
	pollfd request{fd, POLLIN, 0};

	while(poll(&request, 1, 0) > 0 && (request.revents & POLLIN)){
		uint8_t bytes[512];
		const ssize_t size = ::read(fd, bytes, sizeof(bytes));

		if(size <= 0)
			break;

		inbox.insert(inbox.end(), bytes, bytes + size);
	}
}

int PtyPort::available(){
	std::lock_guard<std::mutex> guard(lock);
	pump();
	return inbox.size();
}

int PtyPort::read(){
	std::lock_guard<std::mutex> guard(lock);
	pump();

	if(inbox.empty())
		return -1;

	const int value = inbox.front();
	inbox.pop_front();
	return value;
}

// O USB NAO BLOQUEIA, COMO O setTxTimeoutMs(0), E TAMBEM VAI PARA O stderr COMO LOG DO TESTE
size_t PtyPort::write(const uint8_t* bytes, size_t size){
	size_t sent = 0;

	if(this == &Serial){
		fwrite(bytes, 1, size, stderr);
		fflush(stderr);
	}

	while(sent < size){
		pollfd request{fd, POLLOUT, 0};

		if(poll(&request, 1, blocking ? 200 : 0) <= 0)
			break;

		const ssize_t count = ::write(fd, bytes + sent, size - sent);

		if(count <= 0)
			break;

		sent += count;
	}

	return size;
}

PtyPort Serial("MRU_USB_FD", false, "usb");
static PtyPort rs232("MRU_RS232_FD", true, "rs232");
static PtyPort rs422("MRU_RS422_FD", true, "rs422");


// O KERNEL NO PC: ReadRAM, stop E O PACOTE HR A 200 Hz; O ARQUIVO kernel ESCOLHE A FALHA: ok, dead, silent, bad OU frozen
class FakeKernel{
  private:
	std::mutex lock;
	std::deque<uint8_t> outbox;
	std::vector<uint8_t> inbox;
	std::mt19937 random{7};
	std::normal_distribution<double> gauss{0, 1};
	bool streaming = false;
	int64_t next = 0;
	int64_t asked = 0;
	std::string fault = "ok";
	int32_t held[9];
	bool holding = false;

	const std::string& getFault(){
		const int64_t now = esp_timer_get_time();

		if(now - asked < 100000)
			return fault;

		asked = now;
		fault = readFile(STATE + "/kernel");

		if(fault.empty())
			fault = "ok";

		return fault;
	}

	void answer(const uint16_t id, const int size){
		const float align[3] = {0, -90, 0};
		uint8_t value[20] = {0};
		value[0] = (id == 0x03B2) ? 9 : (id == 0x0012) ? 200 : (id == 0x03D0) ? 1 : (id == 0x03D7) ? 2 : 0;

		if(id == 0x023A)
			memcpy(value, align, sizeof(align));

		std::vector<uint8_t> packet = {0xAA, 0x55, 0x01, 0xB1, (uint8_t) (8 + size), 0};
		packet.insert(packet.end(), value, value + size);
		uint16_t checksum = 0;

		for(size_t i = 2; i < packet.size(); i++)
			checksum += packet[i];

		packet.push_back(checksum & 0xFF);
		packet.push_back(checksum >> 8);
		outbox.insert(outbox.end(), packet.begin(), packet.end());
	}

	void parse(){
		while(inbox.size() >= 8){
			const int length = inbox[4] | (inbox[5] << 8);

			if(inbox[0] != 0xAA || inbox[1] != 0x55 || length < 7 || length > 64){
				inbox.erase(inbox.begin());
				continue;
			}

			if((int) inbox.size() < length + 2)
				return;

			handle(inbox[6]);
			inbox.erase(inbox.begin(), inbox.begin() + length + 2);
		}
	}

	void handle(const uint8_t command){
		if(getFault() == "dead")
			return;

		if(command == 0xB1)
			answer(inbox[8] | (inbox[9] << 8), inbox[10]);

		if(command == 0xFE)
			streaming = false;

		if(command == 0x81){
			streaming = true;
			next = esp_timer_get_time();
		}
	}

	void getValues(int32_t* values, const double time){
		values[0] = 1000*(90.0 + 0.004*gauss(random));
		values[1] = 1000*(5*sin(2*PI*0.3*time) + 0.004*gauss(random));
		values[2] = 1000*(0.004*gauss(random));

		for(int i = 3; i < 6; i++)
			values[i] = 1e5*(0.05*gauss(random));

		values[6] = 1e6*(0.001*gauss(random));
		values[7] = 1e6*(0.001*gauss(random));
		values[8] = 1e6*(1.0 + 0.001*gauss(random));
	}

	void emit(){
		const std::string& current = getFault();

		if(!streaming || current == "silent" || current == "dead")
			return;

		for(const int64_t now = esp_timer_get_time(); next <= now; next += PERIOD){
			int32_t values[9];
			getValues(values, next*1e-6);

			if(current == "frozen" && holding)
				memcpy(values, held, sizeof(values));

			memcpy(held, values, sizeof(values));
			holding = true;
			send(values, current == "bad" && random()%3 == 0);
		}

		if(outbox.size() > BACKLOG)
			outbox.erase(outbox.begin(), outbox.end() - BACKLOG);
	}

	void send(const int32_t* values, const bool corrupt){
		const int16_t temperature = 352;
		uint8_t packet[60] = {0xAA, 0x55, 0x01, 0x95, 0x3C, 0x00};
		uint16_t checksum = 0;
		memcpy(packet + 6, values, 36);
		memcpy(packet + 56, &temperature, 2);

		for(int i = 2; i < 58; i++)
			checksum += packet[i];

		checksum ^= corrupt ? 0x55 : 0;
		packet[58] = checksum & 0xFF;
		packet[59] = checksum >> 8;
		outbox.insert(outbox.end(), packet, packet + 60);
	}

  public:
	void write(const uint8_t* bytes, size_t size){
		std::lock_guard<std::mutex> guard(lock);
		inbox.insert(inbox.end(), bytes, bytes + size);
		parse();
	}

	int available(){
		std::lock_guard<std::mutex> guard(lock);
		emit();
		return outbox.size();
	}

	int read(){
		std::lock_guard<std::mutex> guard(lock);

		if(outbox.empty())
			return -1;

		const int value = outbox.front();
		outbox.pop_front();
		return value;
	}
};

static FakeKernel fakeKernel;

HardwareSerial::HardwareSerial(int number): pty((number == 0) ? &rs232 : (number == 2) ? &rs422 : nullptr){}
int HardwareSerial::available(){ return pty ? pty->available() : fakeKernel.available(); }
int HardwareSerial::read(){ return pty ? pty->read() : fakeKernel.read(); }

size_t HardwareSerial::write(const uint8_t* bytes, size_t size){
	if(pty)
		return pty->write(bytes, size);

	fakeKernel.write(bytes, size);
	return size;
}


static esp_partition_t running = {"app0"};
static esp_partition_t invalid = {"app1"};

static std::string getOta(const std::string& key, const std::string& fallback){
	const std::string value = readFile(STATE + "/ota_" + key);
	return value.empty() ? fallback : value;
}

static void setOta(const std::string& key, const std::string& value){
	writeFile(STATE + "/ota_" + key, value);
}

// O BOOTLOADER: NEW VIRA PENDING NO BOOT; PENDING QUE BOOTA DE NOVO SEM SE CONFIRMAR E ROLLBACK
static void boot(){
	std::string partition = getOta("boot", "app0");
	const std::string state = getOta("state_" + partition, "undefined");

	if(state == "new")
		setOta("state_" + partition, "pending");

	if(state == "pending"){
		setOta("state_" + partition, "aborted");
		setOta("invalid", partition);
		partition = (partition == "app0") ? "app1" : "app0";
		setOta("boot", partition);
		fprintf(stderr, "[bootloader] rollback para %s\n", partition.c_str());
	}

	strncpy(running.label, partition.c_str(), sizeof(running.label) - 1);
}

const esp_partition_t* esp_ota_get_running_partition(){
	return &running;
}

const esp_partition_t* esp_ota_get_last_invalid_partition(){
	const std::string label = getOta("invalid", "");

	if(label.empty())
		return nullptr;

	strncpy(invalid.label, label.c_str(), sizeof(invalid.label) - 1);
	return &invalid;
}

esp_err_t esp_ota_get_state_partition(const esp_partition_t* partition, esp_ota_img_states_t* state){
	const std::string value = getOta(std::string("state_") + partition->label, "undefined");
	*state = (value == "pending") ? ESP_OTA_IMG_PENDING_VERIFY : (value == "valid") ? ESP_OTA_IMG_VALID : ESP_OTA_IMG_UNDEFINED;
	return ESP_OK;
}

esp_err_t esp_ota_mark_app_valid_cancel_rollback(){
	setOta(std::string("state_") + running.label, "valid");
	return ESP_OK;
}

esp_reset_reason_t esp_reset_reason(){
	return getenv("MRU_RESET") ? (esp_reset_reason_t) atoi(getenv("MRU_RESET")) : ESP_RST_POWERON;
}


// REINICIAR E exec DO MESMO BINARIO: OS PTY FICAM, A MEMORIA RECOMECA
static void relaunch(const int reason){
	char path[512];
	const ssize_t size = readlink("/proc/self/exe", path, sizeof(path) - 1);
	path[max<ssize_t>(size, 0)] = 0;
	setenv("MRU_RESET", std::to_string(reason).c_str(), 1);
	execv(path, arguments);
	_exit(1);
}

void EspClass::restart(){
	fprintf(stderr, "[esp] restart\n");
	relaunch(ESP_RST_SW);
}

EspClass ESP;


bool UpdateClass::begin(size_t size){
	if(size != UPDATE_SIZE_UNKNOWN && size > ESP.getFreeSketchSpace()){
		error = "Not Enough Space";
		return false;
	}

	abort();
	file = fopen((STATE + "/ota.bin").c_str(), "wb");
	expected = size;
	error = "No Error";
	return file != nullptr;
}

size_t UpdateClass::write(const uint8_t* bytes, size_t size){
	if(readFile(STATE + "/flash") == "fail"){
		error = "Flash Write Failed";
		return 0;
	}

	received += fwrite(bytes, 1, size, file);
	fflush(file);
	return size;
}

bool UpdateClass::end(bool evenIfRemaining){
	const std::string other = (std::string(running.label) == "app0") ? "app1" : "app0";

	if(file)
		fclose(file);

	file = nullptr;

	if(!evenIfRemaining && received != expected){
		error = "Bad Size Given";
		return false;
	}

	setOta("boot", other);
	setOta("state_" + other, "new");
	return true;
}

void UpdateClass::abort(){
	if(file)
		fclose(file);

	file = nullptr;
	received = 0;
}

UpdateClass Update;


std::string Preferences::getPath(const char* key) const {
	return STATE + "/nvs_" + space + "_" + key;
}

bool Preferences::remove(const char* key){
	return unlink(getPath(key).c_str()) == 0;
}

bool Preferences::isKey(const char* key){
	return access(getPath(key).c_str(), F_OK) == 0;
}

size_t Preferences::putBytes(const char* key, const void* value, size_t size){
	std::ofstream file(getPath(key), std::ios::binary);
	file.write((const char*) value, size);
	return size;
}

size_t Preferences::getBytes(const char* key, void* value, size_t size){
	std::ifstream file(getPath(key), std::ios::binary);

	if(!file)
		return 0;

	file.read((char*) value, size);
	return file.gcount();
}

size_t Preferences::getBytesLength(const char* key){
	std::ifstream file(getPath(key), std::ios::binary | std::ios::ate);
	return file ? (size_t) file.tellg() : 0;
}

String Preferences::getString(const char* key, const String& fallback){
	std::ifstream file(getPath(key), std::ios::binary);

	if(!file)
		return fallback;

	std::stringstream buffer;
	buffer << file.rdbuf();
	std::string text = buffer.str();

	if(!text.empty() && text.back() == 0)
		text.pop_back();

	return String(text);
}


int xTaskCreatePinnedToCore(void(*task)(void*), const char*, int, void* parameter, int, TaskHandle_t*, int){
	std::thread(task, parameter).detach();
	return 1;
}

// A FALHA crash: O FIRMWARE NOVO CAI 3 s DEPOIS DO BOOT, AINDA EM PROVA
static void crashIfAsked(){
	if(readFile(STATE + "/crash") != "boot" || getOta(std::string("state_") + running.label, "") != "pending")
		return;

	std::thread([]{
		delay(3000);
		fprintf(stderr, "[esp] panic\n");
		relaunch(ESP_RST_PANIC);
	}).detach();
}


int main(int, char** argv){
	arguments = argv;
	boot();
	crashIfAsked();
	setup();

	while(true)
		loop();
}
