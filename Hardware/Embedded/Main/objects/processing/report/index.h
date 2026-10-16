#ifndef REPORT_H
#define REPORT_H
#include <Arduino.h>


// UM SEGUNDO DA JANELA: MAXIMOS DOS ANGULOS, SOMA DE hr^2 E A MAIOR MEIA OSCILACAO QUE TERMINOU NELE
struct Bucket{
	float roll, pitch, inclination;
	float square, swing, speed;
	uint32_t count;
};


// O QUE A NORMAM-27 PEDE AO HMS NO PONTO DE INTERESSE: MAXIMOS DOS ULTIMOS 20 MINUTOS, MAIS A SVArf DA NORMAM-223
class Report{
  public:
	static const int SPAN        = 1200;     // s DA JANELA MOVEL, UM BALDE POR SEGUNDO
	static constexpr float NOISE = 0.02f;    // m DE RETORNO QUE CONFIRMA UM EXTREMO DA ARFAGEM: MENOS QUE ISSO E RUIDO

	Bucket buckets[SPAN];
	float inclination = 0;                 // graus, INSTANTANEA: O MAIOR ANGULO DO PISO COM O HORIZONTE
	float B = 0, C = 0, Inc = 0;           // graus, MAXIMOS DE |roll|, |pitch| E DA INCLINACAO
	float Arf = 0, VArf = 0, SVArf = 0;    // m E m/s: A MAIOR MEIA OSCILACAO, A VELOCIDADE MEDIA DELA E 2 x RMS DE hr

	double clock = 0, extremeTime = 0, lastTime = 0;
	float extreme = 0, last = 0;
	long elapsed = 0;
	bool rising = true, anchored = false, started = false;

	void update(const float roll, const float pitch, const float heave, const float rate, const float dt){
		inclination = degrees(acosf(cosf(radians(roll))*cosf(radians(pitch))));    // (R)zz = cos(roll) cos(pitch)

		if(!started)
			start(heave);

		clock += dt;
		shift();

		Bucket& bucket = buckets[elapsed % SPAN];
		bucket.roll        = max(bucket.roll, fabsf(roll));
		bucket.pitch       = max(bucket.pitch, fabsf(pitch));
		bucket.inclination = max(bucket.inclination, inclination);
		bucket.square     += rate*rate;
		bucket.count++;

		peak(heave);
	}

	// SEGUNDO NOVO: ZERA OS BALDES QUE SAIRAM DA JANELA (MAIS DE UM SE HOUVE BURACO) E REFAZ OS MAXIMOS
	void shift(){
		const long second = (long) clock;

		if(second == elapsed)
			return;

		for(long s = elapsed + 1; s <= second && s <= elapsed + SPAN; s++)
			buckets[s % SPAN] = Bucket();

		elapsed = second;
		compute();
	}

	// MEIA OSCILACAO ENTRE DOIS EXTREMOS CONFIRMADOS POR NOISE DE RETORNO: AMPLITUDE E VELOCIDADE MEDIA ENTRE ELES
	void peak(const float heave){
		if(rising ? heave >= extreme : heave <= extreme){
			extreme     = heave;
			extremeTime = clock;
			return;
		}

		if(fabsf(heave - extreme) < NOISE)
			return;

		Bucket& bucket    = buckets[elapsed % SPAN];
		const float swing = fabsf(extreme - last);

		if(anchored && swing > bucket.swing && extremeTime > lastTime){    // A PRIMEIRA SAI DE UM PONTO QUALQUER, NAO DE UM EXTREMO
			bucket.swing = swing;
			bucket.speed = swing / (extremeTime - lastTime);
		}

		last        = extreme;
		lastTime    = extremeTime;
		extreme     = heave;
		extremeTime = clock;
		rising      = !rising;
		anchored    = true;
	}

	// AS GRANDEZAS DA NORMAM SOBRE A JANELA INTEIRA
	void compute(){
		float roll = 0, pitch = 0, incline = 0, square = 0, swing = 0, speed = 0;
		uint32_t count = 0;

		for(const Bucket& bucket : buckets){
			roll    = max(roll, bucket.roll);
			pitch   = max(pitch, bucket.pitch);
			incline = max(incline, bucket.inclination);
			square += bucket.square;
			count  += bucket.count;

			if(bucket.swing > swing){
				swing = bucket.swing;
				speed = bucket.speed;
			}
		}

		B = roll; C = pitch; Inc = incline;
		Arf = swing; VArf = speed;
		SVArf = (count > 0) ? 2*sqrtf(square/count) : 0;
	}

	void start(const float heave){
		extreme  = heave; last = heave;
		rising   = true;
		anchored = false;
		started  = true;
	}

	void reset(){
		for(Bucket& bucket : buckets)
			bucket = Bucket();

		clock = 0; extremeTime = 0; lastTime = 0;
		elapsed = 0;
		B = C = Inc = Arf = VArf = SVArf = 0;
		started = false;
	}
};

#endif
