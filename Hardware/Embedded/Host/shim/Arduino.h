#ifndef ARDUINO_SHIM_H
#define ARDUINO_SHIM_H
#include <algorithm>
#include <atomic>
#include <cmath>
#include <cstdarg>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <fstream>
#include <mutex>
#include <sstream>
#include <string>
#include <thread>
#include <unistd.h>
#include <time.h>

using std::max;
using std::min;
using std::isnan;
using std::isfinite;

#define PI 3.1415926535897932384626433832795
#define HEX 16
#define DEC 10
#define HIGH 1
#define LOW 0
#define OUTPUT 1
#define INPUT_PULLUP 2
#define CHANGE 3
#define SERIAL_8N1 0
#define IRAM_ATTR
#define RTC_NOINIT_ATTR
#define F(x) x
#define ESP32 1
#define radians(x) ((x)*PI/180.0)
#define degrees(x) ((x)*180.0/PI)
#define constrain(x,a,b) ((x)<(a)?(a):((x)>(b)?(b):(x)))
#define UPDATE_SIZE_UNKNOWN 0xFFFFFFFF
#define ESP_OK 0
#define portMUX_INITIALIZER_UNLOCKED {}

typedef uint8_t byte;
typedef int esp_err_t;
typedef void* TaskHandle_t;


inline int64_t esp_timer_get_time(){
	timespec now;
	clock_gettime(CLOCK_MONOTONIC, &now);
	static const int64_t origin = (int64_t) now.tv_sec*1000000 + now.tv_nsec/1000;
	return (int64_t) now.tv_sec*1000000 + now.tv_nsec/1000 - origin + 1;
}

inline unsigned long millis(){ return esp_timer_get_time()/1000; }
inline void delay(unsigned long ms){ usleep(ms*1000); }
inline void delayMicroseconds(unsigned us){ usleep(us); }
inline void noInterrupts(){}
inline void interrupts(){}
inline void pinMode(int, int){}
inline void digitalWrite(int, int){}
inline int digitalRead(int){ return 0; }
inline int digitalPinToInterrupt(int pin){ return pin; }
inline void attachInterrupt(int, void(*)(), int){}


// O String DO ARDUINO SOBRE std::string, SO COM O QUE O FIRMWARE USA
class String{
  public:
	std::string s;

	String(){}
	String(const char* text): s(text ? text : ""){}
	String(const std::string& text): s(text){}
	String(char letter): s(1, letter){}
	String(int value, int base = DEC){ format(value, base); }
	String(unsigned value, int base = DEC){ format(value, base); }
	String(long value, int base = DEC){ format(value, base); }
	String(unsigned long value, int base = DEC){ format(value, base); }
	String(float value, int digits = 2){ format(value, digits); }
	String(double value, int digits = 2){ format(value, digits); }

	void format(double value, int digits){
		char buffer[64];
		snprintf(buffer, sizeof(buffer), "%.*f", digits, value);
		s = buffer;
	}

	template<class T> void format(T value, int base){
		char buffer[64];
		snprintf(buffer, sizeof(buffer), (base == HEX) ? "%llx" : "%lld", (long long) value);
		s = buffer;
	}

	const char* c_str() const { return s.c_str(); }
	unsigned length() const { return s.size(); }
	bool isEmpty() const { return s.empty(); }
	long toInt() const { return atol(s.c_str()); }
	float toFloat() const { return atof(s.c_str()); }
	char charAt(unsigned i) const { return (i < s.size()) ? s[i] : 0; }
	char operator[](unsigned i) const { return charAt(i); }
	bool startsWith(const char* text) const { return s.rfind(text, 0) == 0; }
	bool reserve(unsigned size){ s.reserve(size); return true; }
	bool concat(const char* text, unsigned size){ s.append(text, size); return true; }
	bool concat(const char* text){ s.append(text); return true; }
	bool concat(char letter){ s.push_back(letter); return true; }
	String substring(unsigned a) const { return (a < s.size()) ? s.substr(a) : ""; }
	String substring(unsigned a, unsigned b) const { return (a < s.size()) ? s.substr(a, b - a) : ""; }
	String& operator+=(const String& other){ s += other.s; return *this; }
	String& operator+=(const char* other){ s += other; return *this; }
	String& operator+=(char other){ s += other; return *this; }
	bool operator==(const String& other) const { return s == other.s; }
	bool operator==(const char* other) const { return s == other; }
	bool operator!=(const char* other) const { return s != other; }

	int indexOf(char letter, unsigned from = 0) const {
		const auto position = s.find(letter, from);
		return (position == std::string::npos) ? -1 : position;
	}

	int indexOf(const char* text, unsigned from = 0) const {
		const auto position = s.find(text, from);
		return (position == std::string::npos) ? -1 : position;
	}

	void toLowerCase(){
		for(auto& letter : s)
			letter = tolower(letter);
	}

	void trim(){
		const auto first = s.find_first_not_of(" \t\r\n");
		const auto last  = s.find_last_not_of(" \t\r\n");
		s = (first == std::string::npos) ? "" : s.substr(first, last - first + 1);
	}
};

inline String operator+(const String& a, const String& b){ return String(a.s + b.s); }
inline String operator+(const String& a, const char* b){ return String(a.s + b); }
inline String operator+(const char* a, const String& b){ return String(std::string(a) + b.s); }


class Print{
  public:
	virtual ~Print(){}
	virtual size_t write(const uint8_t* bytes, size_t size) = 0;
	virtual size_t write(uint8_t letter){ return write(&letter, 1); }
	size_t write(const char* text){ return write((const uint8_t*) text, strlen(text)); }
	size_t write(const char* text, size_t size){ return write((const uint8_t*) text, size); }
	size_t print(const char* text){ return write(text); }
	size_t print(const String& text){ return write(text.c_str()); }
	size_t print(char letter){ return write((uint8_t) letter); }
	size_t print(int value){ return print(String(value)); }
	size_t print(float value){ return print(String(value)); }
	size_t println(){ return write("\r\n"); }
	size_t println(const char* text){ print(text); return println(); }
	size_t println(const String& text){ print(text); return println(); }
	size_t println(char letter){ print(letter); return println(); }
	size_t println(int value){ print(value); return println(); }

	size_t printf(const char* format, ...){
		char buffer[512];
		va_list args;
		va_start(args, format);
		const int size = vsnprintf(buffer, sizeof(buffer), format, args);
		va_end(args);
		return write((const uint8_t*) buffer, min(size, 511));
	}
};


class Stream : public Print{
  public:
	using Print::write;
	virtual int available() = 0;
	virtual int read() = 0;
};


// UMA PORTA NUM PTY: O MASTER FICA ABERTO ATRAVES DO exec, COMO O CONVERSOR QUE NAO DESLIGA QUANDO O ESP REINICIA
class PtyPort : public Stream{
  private:
	std::deque<uint8_t> inbox;
	std::mutex lock;
	int fd = -1;
	bool blocking;
	void pump();

  public:
	using Print::write;
	PtyPort(const char* variable, bool blocks, const char* name);
	int available() override;
	int read() override;
	size_t write(const uint8_t* bytes, size_t size) override;
	void setTxTimeoutMs(int){}
	void setRxBufferSize(int){}
	void begin(int, ...){}
};


class HardwareSerial : public Stream{
  private:
	PtyPort* pty = nullptr;

  public:
	using Print::write;
	explicit HardwareSerial(int number);
	void setRxBufferSize(int){}
	void begin(uint32_t, int = 0, int = -1, int = -1){}
	void updateBaudRate(uint32_t){}
	int available() override;
	int read() override;
	size_t write(const uint8_t* bytes, size_t size) override;
};


class EspClass{
  public:
	uint64_t getEfuseMac(){ return 0x0000A1B2C3D4E5F6ULL; }
	uint32_t getFreeHeap(){ return 251000; }
	uint32_t getMinFreeHeap(){ return 198000; }
	uint32_t getFreeSketchSpace(){ return 1310720; }
	void restart();
};


// A NVS EM UM ARQUIVO POR CHAVE, PARA SOBREVIVER AO REINICIO
class Preferences{
  private:
	std::string space;
	std::string getPath(const char* key) const;

  public:
	bool begin(const char* name, bool = false){ space = name; return true; }
	void end(){}
	bool clear(){ return true; }
	bool remove(const char* key);
	bool isKey(const char* key);
	size_t putBytes(const char* key, const void* value, size_t size);
	size_t getBytes(const char* key, void* value, size_t size);
	size_t getBytesLength(const char* key);
	String getString(const char* key, const String& fallback = "");
	size_t putString(const char* key, const String& value){ return putBytes(key, value.c_str(), value.length() + 1); }
	size_t putUInt(const char* key, uint32_t value){ return putBytes(key, &value, sizeof(value)); }
	size_t putInt(const char* key, int32_t value){ return putBytes(key, &value, sizeof(value)); }
	size_t putBool(const char* key, bool value){ return putBytes(key, &value, sizeof(value)); }
	uint32_t getUInt(const char* key, uint32_t fallback = 0){ getBytes(key, &fallback, sizeof(fallback)); return fallback; }
	int32_t getInt(const char* key, int32_t fallback = 0){ getBytes(key, &fallback, sizeof(fallback)); return fallback; }
	bool getBool(const char* key, bool fallback = false){ getBytes(key, &fallback, sizeof(fallback)); return fallback; }
};


class UpdateClass{
  private:
	FILE* file = nullptr;
	size_t expected = 0;
	size_t received = 0;
	const char* error = "No Error";

  public:
	bool begin(size_t size = UPDATE_SIZE_UNKNOWN);
	size_t write(const uint8_t* bytes, size_t size);
	bool end(bool evenIfRemaining = false);
	void abort();
	const char* errorString(){ return error; }
};


struct esp_partition_t{
	char label[8];
};

struct portMUX_TYPE{
	std::atomic<bool> flag{false};
};

typedef enum {ESP_OTA_IMG_NEW, ESP_OTA_IMG_PENDING_VERIFY, ESP_OTA_IMG_VALID, ESP_OTA_IMG_INVALID, ESP_OTA_IMG_ABORTED, ESP_OTA_IMG_UNDEFINED = -1} esp_ota_img_states_t;
typedef enum {ESP_RST_UNKNOWN, ESP_RST_POWERON, ESP_RST_EXT, ESP_RST_SW, ESP_RST_PANIC, ESP_RST_INT_WDT, ESP_RST_TASK_WDT, ESP_RST_WDT, ESP_RST_DEEPSLEEP, ESP_RST_BROWNOUT, ESP_RST_SDIO} esp_reset_reason_t;

const esp_partition_t* esp_ota_get_running_partition();
const esp_partition_t* esp_ota_get_last_invalid_partition();
esp_err_t esp_ota_get_state_partition(const esp_partition_t* partition, esp_ota_img_states_t* state);
esp_err_t esp_ota_mark_app_valid_cancel_rollback();
esp_reset_reason_t esp_reset_reason();
int xTaskCreatePinnedToCore(void(*task)(void*), const char*, int, void* parameter, int, TaskHandle_t*, int);

inline void portENTER_CRITICAL(portMUX_TYPE* mux){ while(mux->flag.exchange(true)){} }
inline void portEXIT_CRITICAL(portMUX_TYPE* mux){ mux->flag.store(false); }

extern PtyPort Serial;
extern EspClass ESP;
extern UpdateClass Update;

#endif
