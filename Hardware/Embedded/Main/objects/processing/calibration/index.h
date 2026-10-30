#ifndef CALIBRATION_H
#define CALIBRATION_H
#include <Arduino.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <stddef.h>
#include <type_traits>
#include "../filters/index.h"
#include "../correction/index.h"
#include "../align/index.h"
#include "../attitude/index.h"
#include "../heave/index.h"
#include "../lever/index.h"


// TODOS OS PARAMETROS DA CADEIA CALIBRADA, SO float E SEM PREENCHIMENTO: CADA CHAVE E UM TRECHO CONTIGUO DE BYTES
struct CalibrationData{
	float model;
	FiltersParams filters;
	CorrectionParams correction;
	AlignParams align;
	KalmanParams kalman;
	LinearParams linear;
	MachineParams machine;
	HeaveParams heave;
	LeverParams lever;
};


// CHAVE DO COMANDO CL: O NOME DA CONSTANTE NO config.h, ONDE ELA FICA NA CalibrationData E QUANTOS float TEM
struct CalibrationKey{
	const char* name;
	size_t offset;
	int size;
};


// CALIBRACAO DO MRU: A DOS config.h COMPILADOS OU A GRAVADA PELA SERIAL NA FLASH, QUE PREVALECE
class Calibration{
  public:
	static constexpr const char* NAMESPACE = "calibration";
	static constexpr int MAX_VALUES = 128;    // UM COMANDO CABE EM CMD_MAX_SIZE = 256: NO MAXIMO "1,1,..."

	static constexpr CalibrationKey KEYS[] = {
		{"ATTITUDE_MODEL",     offsetof(CalibrationData, model),              1},
		{"FILTERS_TYPE",       offsetof(CalibrationData, filters.type),       6},
		{"FILTERS_FC",         offsetof(CalibrationData, filters.fc),         6},
		{"CORRECTION_T0",      offsetof(CalibrationData, correction.T0),      1},
		{"CORRECTION_M",       offsetof(CalibrationData, correction.M),       18},
		{"CORRECTION_C",       offsetof(CalibrationData, correction.C),       6},
		{"CORRECTION_K",       offsetof(CalibrationData, correction.K),       6},
		{"ALIGN_CALIBRATION",  offsetof(CalibrationData, align.calibration),  3},
		{"ALIGN_FRAME",        offsetof(CalibrationData, align.frame),        9},
		{"KALMAN_GRAVITY",     offsetof(CalibrationData, kalman.gravity),     1},
		{"KALMAN_GYRO_NOISE",  offsetof(CalibrationData, kalman.gyroNoise),   1},
		{"KALMAN_BIAS_NOISE",  offsetof(CalibrationData, kalman.biasNoise),   1},
		{"KALMAN_ACCEL_NOISE", offsetof(CalibrationData, kalman.accelNoise),  1},
		{"KALMAN_ZUPT_NOISE",  offsetof(CalibrationData, kalman.zuptNoise),   1},
		{"KALMAN_ACCEL_GATE",  offsetof(CalibrationData, kalman.accelGate),   1},
		{"KALMAN_GYRO_PHASE",  offsetof(CalibrationData, kalman.gyroPhase),   1},
		{"KALMAN_HEADING",     offsetof(CalibrationData, kalman.heading),     1},
		{"KALMAN_LEVER",       offsetof(CalibrationData, kalman.lever),       3},
		{"LINEAR_M",           offsetof(CalibrationData, linear.M),           9},
		{"LINEAR_B",           offsetof(CalibrationData, linear.B),           3},
		{"MACHINE_PERIOD",     offsetof(CalibrationData, machine.period),     1},
		{"MACHINE_SENSOR",     offsetof(CalibrationData, machine.sensor),     MACHINE_INPUTS},
		{"MACHINE_TARGET",     offsetof(CalibrationData, machine.target),     3},
		{"MACHINE_MEAN",       offsetof(CalibrationData, machine.mean),       MACHINE_FEATURES},
		{"MACHINE_SCALE",      offsetof(CalibrationData, machine.scale),      MACHINE_FEATURES},
		{"MACHINE_COEF",       offsetof(CalibrationData, machine.coef),       MACHINE_OUTPUTS*MACHINE_FEATURES},
		{"MACHINE_BIAS",       offsetof(CalibrationData, machine.bias),       MACHINE_OUTPUTS},
		{"HEAVE_PERIOD",       offsetof(CalibrationData, heave.period),       1},
		{"HEAVE_DAMPING",      offsetof(CalibrationData, heave.damping),      1},
		{"HEAVE_GRAVITY",      offsetof(CalibrationData, heave.gravity),      1},
		{"LEVER_POINT",        offsetof(CalibrationData, lever.point),        3}
	};

	CalibrationData data;       // A QUE A CADEIA USA DESDE O BOOT
	CalibrationData pending;    // A QUE OS CL: PREENCHEM ATE O $calibration_save!
	bool stored  = false;
	bool staging = false;

	void setup(){
		reset(data);
		Preferences prefs;
		prefs.begin(NAMESPACE, false);
		stored = (prefs.getBytesLength("data") == sizeof(CalibrationData)) && (prefs.getBytes("data", &pending, sizeof(CalibrationData)) == sizeof(CalibrationData));
		stored = stored && (prefs.getUInt("crc", 0) == getCRC(&pending, sizeof(CalibrationData)));    // GRAVACAO INTERROMPIDA: FICA A COMPILADA
		prefs.end();

		if(stored)
			data = pending;

		Serial.println(String("Calibration: ") + (stored ? "flash" : "firmware"));
	}

	// GRAVA NA PENDENTE OS VALORES "v1,v2,..." A PARTIR DA POSICAO offset, TODOS OU NENHUM; DEVOLVE QUANTOS, OU -1 SE A CHAVE OU UM VALOR NAO SERVE
	int set(const char* name, const int offset, const char* values){
		const CalibrationKey* key = find(name);
		float parsed[MAX_VALUES];
		const char* cursor = values;
		int count = 0;

		if(key == nullptr || offset < 0)
			return -1;

		while(*cursor){
			char* end;
			const float value = strtof(cursor, &end);

			if(end == cursor || count >= MAX_VALUES || offset + count >= key->size || (*end != ',' && *end != '\0'))
				return -1;

			parsed[count++] = value;
			cursor = (*end == ',') ? end + 1 : end;
		}

		if(count == 0)
			return -1;

		if(!staging){
			pending = data;
			staging = true;
		}

		memcpy(locate(pending, *key) + offset, parsed, count*sizeof(float));
		return count;
	}

	const CalibrationKey* find(const char* name) const {
		for(const CalibrationKey& key : KEYS)
			if(strcmp(key.name, name) == 0)
				return &key;

		return nullptr;
	}

	static float* locate(CalibrationData& source, const CalibrationKey& key){
		return (float*) ((uint8_t*) &source + key.offset);
	}

	static const float* locate(const CalibrationData& source, const CalibrationKey& key){
		return (const float*) ((const uint8_t*) &source + key.offset);
	}

	// CRC-32 IEEE DOS BYTES little-endian DE CADA float: O APP CALCULA O MESMO PARA CONFERIR O QUE ENVIOU
	static uint32_t getCRC(const void* bytes, const size_t size){
		const uint8_t* cursor = (const uint8_t*) bytes;
		uint32_t crc = 0xFFFFFFFF;

		for(size_t i = 0; i < size; i++){
			crc ^= cursor[i];

			for(int k = 0; k < 8; k++)
				crc = (crc >> 1) ^ (0xEDB88320 & (0 - (crc & 1)));
		}

		return ~crc;
	}

	String getSource() const {
		return stored ? "flash" : "firmware";
	}

	// ORIGEM, MODELO E O TAMANHO E O CRC DE CADA CHAVE: DA PENDENTE ENQUANTO HOUVER CL: SEM SALVAR
	String toJson() const {
		const CalibrationData& source = staging ? pending : data;
		JsonDocument doc;
		doc["source"]  = getSource();
		doc["staging"] = staging;
		doc["model"]   = (int) source.model;
		JsonObject keys = doc["keys"].to<JsonObject>();

		for(const CalibrationKey& key : KEYS){
			JsonArray entry = keys[key.name].to<JsonArray>();
			entry.add(key.size);
			entry.add(String(getCRC(locate(source, key), key.size*sizeof(float)), HEX));
		}

		String output;
		serializeJson(doc, output);
		return output;
	}

	template<typename T> static void copy(float* target, const T* source, const int size){
		for(int i = 0; i < size; i++)
			target[i] = (float) source[i];
	}

	// OS config.h COMPILADOS: O QUE VALE ENQUANTO NAO HA CALIBRACAO NA FLASH
	static void reset(CalibrationData& target){
		target.model = std::is_same<AttitudeModel, LinearModel>::value  ? LINEAR_MODEL  :
		               std::is_same<AttitudeModel, MachineModel>::value ? MACHINE_MODEL : KALMAN_MODEL;

		copy(target.filters.type, FILTERS_TYPE, 6);
		copy(target.filters.fc, FILTERS_FC, 6);

		target.correction.T0 = CORRECTION_T0;
		copy(&target.correction.M[0][0][0], &CORRECTION_M[0][0][0], 18);
		copy(&target.correction.C[0][0], &CORRECTION_C[0][0], 6);
		copy(&target.correction.K[0][0], &CORRECTION_K[0][0], 6);

		copy(target.align.calibration, ALIGN_CALIBRATION, 3);
		copy(&target.align.frame[0][0], &ALIGN_FRAME[0][0], 9);

		target.kalman = {KALMAN_GRAVITY, KALMAN_GYRO_NOISE, KALMAN_BIAS_NOISE, KALMAN_ACCEL_NOISE, KALMAN_ZUPT_NOISE, KALMAN_ACCEL_GATE, KALMAN_GYRO_PHASE, KALMAN_HEADING, {KALMAN_LEVER[0], KALMAN_LEVER[1], KALMAN_LEVER[2]}};
		copy(&target.linear.M[0][0], &LINEAR_M[0][0], 9);
		copy(target.linear.B, LINEAR_B, 3);

		target.machine.period = MACHINE_PERIOD;
		copy(target.machine.sensor, MACHINE_SENSOR, MACHINE_INPUTS);
		copy(target.machine.target, MACHINE_TARGET, 3);
		copy(target.machine.mean, MACHINE_MEAN, MACHINE_FEATURES);
		copy(target.machine.scale, MACHINE_SCALE, MACHINE_FEATURES);
		copy(&target.machine.coef[0][0], &MACHINE_COEF[0][0], MACHINE_OUTPUTS*MACHINE_FEATURES);
		copy(target.machine.bias, MACHINE_BIAS, MACHINE_OUTPUTS);

		target.heave = {HEAVE_PERIOD, HEAVE_DAMPING, HEAVE_GRAVITY};
		copy(target.lever.point, LEVER_POINT, 3);
	}

	bool save(){
		if(!staging)
			pending = data;

		Preferences prefs;
		prefs.begin(NAMESPACE, false);
		const bool saved = (prefs.putBytes("data", &pending, sizeof(CalibrationData)) == sizeof(CalibrationData)) && (prefs.putUInt("crc", getCRC(&pending, sizeof(CalibrationData))) > 0);
		prefs.end();
		return saved;
	}

	void erase(){
		Preferences prefs;
		prefs.begin(NAMESPACE, false);
		prefs.clear();
		prefs.end();
	}
};


// AS CHAVES COBREM A CalibrationData SEM BURACO NEM SOBREPOSICAO, NA ORDEM DA STRUCT
constexpr bool isContiguous(){
	size_t offset = 0;

	for(const CalibrationKey& key : Calibration::KEYS){
		if(key.offset != offset)
			return false;

		offset += key.size*sizeof(float);
	}

	return offset == sizeof(CalibrationData);
}

static_assert(isContiguous(), "Calibration::KEYS precisa cobrir a CalibrationData inteira, na ordem dos campos");

#endif
