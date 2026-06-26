#ifndef SERIAL_H
#define SERIAL_H
#define CMD_MIN_SIZE 3
#include <HardwareSerial.h>

#define RX_RS422 13
#define TX_RS422 12

#define RX_RS232 10
#define TX_RS232 11

// ── Hardware UART allocation (ESP32-S3 has 3 UARTs: 0, 1, 2) ──────────────
//   UART0 -> RS232  (this class)        pins RX=10 / TX=11
//   UART1 -> Kernel IMU sensor          (objects/sensors/Kernel) — RESERVED
//   UART2 -> RS422  (this class)        pins RX=13 / TX=12
//
// RS232 used to live on UART1 — the SAME peripheral the Kernel sensor opens
// (objects/sensors/Kernel/index.h: `new HardwareSerial(1)`). Since
// sensors.setup() runs AFTER telemetry.setup() (see device/index.h), the
// Kernel's begin(115200, rx=3, tx=4) silently re-mapped UART1 and left
// GPIO10/11 dead — RS232 stopped sending AND receiving. Keeping RS232 on its
// own UART (UART0, free because `Serial` is USB-CDC/HWCDC on the S3) fixes it.
#define UART_RS232 0
#define UART_RS422 2


template<int CMD_MAX_SIZE> class NextSerial {
  private:
	Listener checkTimer = Listener(100);
	HardwareSerial rs232;
	HardwareSerial rs422;

  public:
	Stream* uart = &rs232;
	int port = 1;

	Text<CMD_MAX_SIZE> command;
	const int timeout = 1000;
	int baudrate = 9600;

	unsigned long lastAckTime = 0;
	bool available = false;

	NextSerial():
		rs232(UART_RS232),
		rs422(UART_RS422){}

	void setup(int baud=9600){
		baudrate = baud;

		rs232.begin(baudrate, SERIAL_8N1, RX_RS232, TX_RS232); delay(200);
		//rs422.begin(baudrate, SERIAL_8N1, RX_RS422, TX_RS422); delay(200);

		Serial.printf("RS422 Started at tx=%d - rx=%d\n", TX_RS422, RX_RS422);
		Serial.printf("RS232 Started at tx=%d - rx=%d\n", TX_RS232, RX_RS232);
		Serial.println("Baudrate: " + String(baudrate) + "\n");
	}

	void send(const char* msg, bool breakLine = true){
		uart->write(msg);

		if(breakLine)
			uart->write("\r\n");
	}

	void send(const String& msg, bool breakLine = true){
		uart->write(msg.c_str());

		if(breakLine)
			uart->write("\r\n");
	}

	void print() {
		Serial.println(available ? "(serial) received: " + command.toString() : "nothing received");
	}

	void await(const int ms) {
		const unsigned long startTime = Time::get();

		while(Time::get() - startTime < ms)
			listen();
	}

	void listen(){
		if(!checkTimer.ready())
			return;

		if(Serial.available() > CMD_MIN_SIZE && port != 1){
			Serial.println("port changed to 1 (USB COM)");
			uart = &Serial; 
			port = 1;
			reset();
		}

		else if(rs422.available() > CMD_MIN_SIZE && port != 2){
			Serial.println("port changed to 2 (RS422 COM)");
			uart = &rs422; 
			port = 2; 
			reset();
		}

		else if(rs232.available() > CMD_MIN_SIZE && port != 3){
			Serial.println("port changed to 3 (RS232 COM)");
			uart = &rs232; 
			port = 3; 
			reset();
		}

		if(!uart->available())
			return;

		const unsigned long startTime = Time::get();
		reset();

		while(uart->available() && Time::get() - startTime < timeout) {
			command.concat((char) uart->read());

			if(!uart->available())
				delayMicroseconds(2000);
		}

		clean();
		available   = command.length() > 0;
		lastAckTime = available ? Time::get() : lastAckTime;

		if(!available)
			clear(true);
	}

	void clean() {
		command.remove('\r');
		command.remove('\n');
		command.remove('\t');

		if(command.isEmpty() || command.length() < CMD_MIN_SIZE || command.length() > CMD_MAX_SIZE)
			reset();
	}

	void clear(bool _reset = false) {
		while(uart->available())
			read();

		if(_reset)
			reset();
	}

	char read() {
		char letter = (char) uart->read();

		if(!uart->available())
			delayMicroseconds(500);

		return letter;
	}

	void reset() {
		command.reset();
		available = false;
	}
};

#endif