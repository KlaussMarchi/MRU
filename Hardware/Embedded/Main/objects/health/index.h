#ifndef HEALTH_H
#define HEALTH_H
#include <Arduino.h>
#include <ArduinoJson.h>
#include <esp_system.h>
#include <esp_ota_ops.h>
#include <esp_attr.h>
#include <stdarg.h>

#define LOG_SIZE 32
#define LOG_TEXT 80
#define LOG_MAGIC 0x4D52554C


struct LogEntry{
	float time;
	char level;
	char text[LOG_TEXT];
};


// NA MEMORIA RTC O DIARIO SOBREVIVE A panic, WATCHDOG E REINICIO: O QUE ACONTECEU ANTES DE CAIR AINDA ESTA LA NO BOOT SEGUINTE
RTC_NOINIT_ATTR static LogEntry logEntries[LOG_SIZE];
RTC_NOINIT_ATTR static uint32_t logWritten;
RTC_NOINIT_ATTR static uint32_t logMagic;


// O QUE O MRU SABE DE SI: O DIARIO DOS ULTIMOS EVENTOS E OS SINAIS DE VIDA QUE O APP LE PARA DIZER POR QUE NAO HA DADOS
template <typename Parent> class Health{
  private:
	Parent* device;
	portMUX_TYPE lock = portMUX_INITIALIZER_UNLOCKED;
	uint32_t flushed = 0;
	int64_t lastLoop = 0;
	Listener timer   = Listener(1000);
	uint32_t lastPackets = 0;
	uint32_t lastErrors  = 0;
	uint32_t lastSkipped = 0;
	int32_t lastSum      = 0;
	int same             = 0;

  public:
	static constexpr int STALL = 100;    // ms DE TRAVADA DA thread0 QUE MERECEM REGISTRO: A 200 Hz JA PERDE 20 PACOTES
	static constexpr int FROZEN = 3;     // s COM OS VALORES CRUS IDENTICOS: NO MODO OR, DE POUCA RESOLUCAO, UM SEGUNDO IGUAL PODE SER ACASO
	static constexpr float TEMPERATURE[2] = {-40.0f, 85.0f};    // graus C DE OPERACAO DO KERNEL-120

	bool verbose = false;    // OS EVENTOS TAMBEM SAEM PELA PORTA ATIVA; DESLIGADO NO BOOT PARA NAO MISTURAR COM QUEM SO LE O STREAM
	bool silent  = false;
	bool frozen  = false;
	bool invalid = false;
	bool hot     = false;
	int stall    = 0;        // ms, A MAIOR DESDE O BOOT
	int rate     = 0;        // PACOTES DO KERNEL NO ULTIMO SEGUNDO
	uint32_t invalids = 0;   // SEGUNDOS COM NaN NA SAIDA DO PROCESSAMENTO

	Health(Parent* dev):
		device(dev){}

	void setup(){
		const esp_reset_reason_t reason = esp_reset_reason();
		const bool kept = (logMagic == LOG_MAGIC) && (reason == ESP_RST_SW || reason == ESP_RST_PANIC || reason == ESP_RST_INT_WDT || reason == ESP_RST_TASK_WDT || reason == ESP_RST_WDT);

		if(!kept)    // LIGOU AGORA: A MEMORIA RTC TEM LIXO
			logWritten = 0;

		logMagic = LOG_MAGIC;
		flushed  = logWritten;
		const esp_partition_t* running  = esp_ota_get_running_partition();
		const bool crash = (reason == ESP_RST_PANIC) || (reason == ESP_RST_INT_WDT) || (reason == ESP_RST_TASK_WDT) || (reason == ESP_RST_WDT) || (reason == ESP_RST_BROWNOUT);
		log(crash ? 'E' : 'I', "boot %s, reset %s, particao %s", device->firmware, getReset(), running ? running->label : "?");
	}

	// thread0: A TRAVADA NA HORA E O RESTO UMA VEZ POR SEGUNDO
	void handle(){
		const int64_t now = esp_timer_get_time();
		const int gap     = (lastLoop == 0) ? 0 : (now - lastLoop)/1000;
		lastLoop          = now;
		stall             = max(stall, gap);

		if(gap >= STALL)
			log('W', "thread0 travou %d ms", gap);

		if(timer.ready())
			update();
	}

	void update(){
		const KernelSensor& kernel = device->sensors.kernel;
		const int32_t sum = kernel.ax ^ kernel.ay ^ kernel.az ^ kernel.wx ^ kernel.wy ^ kernel.wz ^ kernel.pitch ^ kernel.roll ^ kernel.yaw ^ kernel.q0 ^ kernel.q1;
		const float temperature = kernel.temperature*KernelSensor::SCALE[kernel.mode].temperature;
		const float values[4]   = {device->processing.pitch, device->processing.roll, device->processing.yaw, device->processing.h};
		bool broken = false;

		for(const float value : values)
			broken = broken || !isfinite(value);

		rate = kernel.packets - lastPackets;
		same = (sum == lastSum) ? same + 1 : 0;
		setAlarm(silent, !kernel.alive(), 'E', "kernel mudo: nenhum pacote valido", "kernel voltou a transmitir");
		setAlarm(frozen, kernel.alive() && (same >= FROZEN), 'E', "kernel congelado: valores identicos por 3 s", "kernel voltou a variar");
		setAlarm(invalid, broken, 'E', "processamento gerou NaN na saida", "processamento voltou a numeros validos");
		setAlarm(hot, kernel.alive() && (temperature < TEMPERATURE[0] || temperature > TEMPERATURE[1]), 'W', "temperatura do kernel fora da faixa", "temperatura do kernel normal");
		invalids += broken;

		if(kernel.errors != lastErrors)
			log('W', "%lu pacotes do kernel com checksum invalido em 1 s", (unsigned long) (kernel.errors - lastErrors));

		if(device->telemetry.streamer.skipped != lastSkipped)
			log('W', "%lu pacotes nao enviados em 1 s: porta saturada", (unsigned long) (device->telemetry.streamer.skipped - lastSkipped));

		lastPackets = kernel.packets;
		lastErrors  = kernel.errors;
		lastSkipped = device->telemetry.streamer.skipped;
		lastSum     = sum;
	}

	void reset(){
		lastLoop = 0;
	}

	void setAlarm(bool& state, const bool now, const char level, const char* raised, const char* cleared){
		if(state == now)
			return;

		state = now;
		now ? log(level, "%s", raised) : log('I', "%s", cleared);
	}

	// QUALQUER THREAD: O USB NAO BLOQUEIA (setTxTimeoutMs) E A PORTA ATIVA SO RECEBE NO flush() DA thread1, ENTRE DUAS LINHAS DO STREAM
	void log(const char level, const char* format, ...){
		char text[LOG_TEXT];
		va_list args;
		va_start(args, format);
		vsnprintf(text, sizeof(text), format, args);
		va_end(args);

		const float time = esp_timer_get_time()*1e-6f;
		portENTER_CRITICAL(&lock);
		LogEntry& entry = logEntries[logWritten % LOG_SIZE];
		entry.time  = time;
		entry.level = level;
		memcpy(entry.text, text, LOG_TEXT);
		logWritten++;
		portEXIT_CRITICAL(&lock);

		Serial.printf("#%c %.3f %s\n", level, time, text);
	}

	void flush(){
		if(!verbose || device->telemetry.serial.port == USB_PORT){    // NO USB O log() JA ESCREVEU
			flushed = logWritten;
			return;
		}

		flushed = max(flushed, logWritten - min(logWritten, (uint32_t) LOG_SIZE));

		while(flushed != logWritten){
			const LogEntry entry = get(flushed);
			char line[LOG_TEXT + 16];
			snprintf(line, sizeof(line), "#%c %.3f %s", entry.level, entry.time, entry.text);
			device->telemetry.serial.send(line);
			flushed++;
		}
	}

	LogEntry get(const uint32_t index){
		portENTER_CRITICAL(&lock);
		const LogEntry entry = logEntries[index % LOG_SIZE];
		portEXIT_CRITICAL(&lock);
		return entry;
	}

	const char* getReset() const {
		switch(esp_reset_reason()){
			case ESP_RST_POWERON:   return "poweron";
			case ESP_RST_SW:        return "sw";
			case ESP_RST_PANIC:     return "panic";
			case ESP_RST_INT_WDT:   return "int_wdt";
			case ESP_RST_TASK_WDT:  return "task_wdt";
			case ESP_RST_WDT:       return "wdt";
			case ESP_RST_DEEPSLEEP: return "deepsleep";
			case ESP_RST_BROWNOUT:  return "brownout";
			case ESP_RST_SDIO:      return "sdio";
			default:                return "unknown";
		}
	}

	// $diagnostics!: TUDO QUE EXPLICA O MRU SEM DADOS OU COM DADOS RUINS, NUMA LINHA
	String info(){
		const KernelSensor& kernel = device->sensors.kernel;
		const auto& streamer       = device->telemetry.streamer;
		const esp_partition_t* running = esp_ota_get_running_partition();
		JsonDocument doc;

		doc["uptime"]      = Time::get()/1000;
		doc["reset"]       = getReset();
		doc["heap"]        = ESP.getFreeHeap();
		doc["heap_min"]    = ESP.getMinFreeHeap();
		doc["partition"]   = running ? running->label : "?";
		doc["sketch_free"] = ESP.getFreeSketchSpace();
		doc["rolled_back"] = (esp_ota_get_last_invalid_partition() != nullptr);
		doc["stall"]       = stall;
		doc["logs"]        = logWritten;
		doc["verbose"]     = verbose;

		JsonObject sensor    = doc["kernel"].to<JsonObject>();
		sensor["found"]      = kernel.found;
		sensor["alive"]      = kernel.alive();
		sensor["frozen"]     = frozen;
		sensor["baud"]       = kernel.baud;
		sensor["rate"]       = rate;
		sensor["packets"]    = kernel.packets;
		sensor["errors"]     = kernel.errors;
		sensor["silence"]    = kernel.silence();
		sensor["temperature"] = kernel.temperature*KernelSensor::SCALE[kernel.mode].temperature;

		JsonObject stream = doc["stream"].to<JsonObject>();
		stream["active"]  = streamer.active;
		stream["port"]    = device->telemetry.serial.getName();
		stream["lines"]   = streamer.lines;
		stream["skipped"] = streamer.skipped;

		JsonObject chain   = doc["processing"].to<JsonObject>();
		chain["count"]     = device->processing.count;
		chain["invalid"]   = invalids;

		String output;
		serializeJson(doc, output);
		return output;
	}

	// $log!: OS ULTIMOS EVENTOS, DESTE BOOT E DO ANTERIOR SE ELE CAIU, PARA QUEM CONECTOU DEPOIS QUE ACONTECERAM
	String getLog(){
		JsonDocument doc;
		JsonArray list = doc["log"].to<JsonArray>();

		for(uint32_t index = logWritten - min(logWritten, (uint32_t) LOG_SIZE); index != logWritten; index++){
			const LogEntry entry = get(index);
			JsonObject item = list.add<JsonObject>();
			item["t"] = entry.time;
			item["l"] = String(entry.level);
			item["m"] = String(entry.text);    // O log() SEMPRE TERMINA O TEXTO, E A MEMORIA RTC SO VALE COM O logMagic CERTO
		}

		String output;
		serializeJson(doc, output);
		return output;
	}
};

#endif
