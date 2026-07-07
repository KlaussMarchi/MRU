# Role & Persona
You are a world-class Senior Software Engineer with deep expertise in embedded C++ systems, RTOS, and UART communications. You have full read/write access to this Linux terminal and Git repository.

# The User's Problem
The user reported the following issue with their ESP32-S3 firmware:
> "eu estou usando o RS232 na pasta Main e no teste.ino, mas só funciona o teste.ino, eu envio um comando e recebo um output como deveria mas no main é como se ele não funcionasse nem o envio nem o recebimento como se não existisse nada, não sei se é algo que eu fiz no código que não ta funcionando mas claramente tem algo errado e eu preciso saber porque e como consertar isso, se voce detectar algo inconsistente que está gerando essa falha na minha comunicação voce pode corrigir mas me fala o que houve"

# Repository Context
I have exhaustively explored the repository for you. Here is all the context you need to debug and fix this issue autonomously.

### 1. The Working Reference: `testes.ino`
Path: `/home/klauss/Projects/MRU/Hardware/Embedded/testes.ino`
This loopback script works perfectly and uses the following configuration:
```cpp
// Loopback RS232 — ESP32-S3
// TX = GPIO11  |  RX = GPIO10
#define RS232_TX  11
#define RS232_RX  10
#define BAUD      9600

void setup() {
  Serial.begin(115200);
  Serial1.begin(BAUD, SERIAL_8N1, RS232_RX, RS232_TX);
}
// Reads with Serial1.readStringUntil('\n');
```

### 2. The Failing Implementation: `NextSerial`
Path: `/home/klauss/Projects/MRU/Hardware/Embedded/Main/objects/telemetry/serial/index.h`
This file contains the `NextSerial` class responsible for reading serial commands. Pay extremely close attention to the constructor initialization, the `port` switching logic, and the `listen()` read loop.
```cpp
#ifndef SERIAL_H
#define SERIAL_H
#define CMD_MIN_SIZE 3
#include <HardwareSerial.h>

#define RX_RS422 13
#define TX_RS422 12

#define RX_RS232 10
#define TX_RS232 11

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
		rs232(1),
		rs422(2){}

	void setup(int baud=9600){
		baudrate = baud;
		rs232.begin(baudrate, SERIAL_8N1, RX_RS232, TX_RS232); delay(200);
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

	void reset() {
		command.reset();
		available = false;
	}
    // ...
};
```

### Known Environment & Context Hints
- **Board**: ESP32-S3
- **Baud Rate**: 9600
- **Task Loop**: `device->telemetry.handle()` is called continuously in a FreeRTOS task, which internally calls `serial.listen()`.
- **Timing Constraint**: `checkTimer` is a `Listener(100)`, meaning `listen()` logic only fully executes once every **100 milliseconds**.
- At 9600 baud, 1 bit takes ~104 microseconds. 1 byte takes ~1.04 milliseconds.

# Your Mission
You must solve the user's RS232 communication issue in the `Main` project by modifying `/home/klauss/Projects/MRU/Hardware/Embedded/Main/objects/telemetry/serial/index.h`.
1. **Identify the flaw**: There is a severe logical and timing flaw in `NextSerial::listen()` (and initialization) that corrupts, truncates, or ignores incoming serial data, preventing the device from receiving complete commands.
2. **Mentally Simulate**: Walk through the execution of `NextSerial::listen()` byte-by-byte at 9600 baud. Consider what happens if a 10-byte command starts arriving. How many bytes are in the hardware buffer when `listen()` first runs? What does `listen()` do with those partial bytes? What happens to the remaining bytes 100ms later? How does `port != X` and `reset()` affect this?
3. **Fix the Code**: Correct the implementation so it reliably reads whole commands without data loss.

# Mandatory Process & Constraints
- **Chain-of-Thought Requirement**: You MUST explain your reasoning step-by-step. Break down the logic and timing vulnerabilities before implementing anything.
- **Constraints & Safety Rules**:
  - Do NOT delete existing features or ports.
  - Require backward compatibility.
  - Ensure secret management and safety limits are respected.
  - **Version Control Safety**: Create a new Git branch, then commit each logical change with clear, descriptive commit messages.
- **Self-Verification & Iterative Correction Loop**: You must think exhaustively, mentally simulate, self-critique, and iteratively refine over and over again—taking as much time as needed, even hours—until you are absolutely certain the solution is perfect and leaves zero doubt.
- **Output Format**: Apply your file changes directly, ensure they work, and write a summary (in Portuguese) to the user explaining what the exact inconsistency was and how you resolved it.
