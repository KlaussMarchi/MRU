#ifndef KALMAN_MODEL_H
#define KALMAN_MODEL_H
#include <Arduino.h>
#include "config.h"


// MEKF DE SEIS ESTADOS (ATITUDE E BIAS DO GIRO), ESPELHO DO KalmanFilter DO Calibration/Model/KalmanFusion
class KalmanModel{
  private:
	static constexpr float TILT_P0     = 1.0f;         // (rad^2) ATITUDE INICIAL DESCONHECIDA: DEIXA O ACCEL PUXAR
	static constexpr float BIAS_P0     = 1e-4f;        // (rad/s)^2 BIAS TIPICO DE UM MEMS JA COMPENSADO
	static constexpr float GAP_FACTOR  = 3.0f;         // ACIMA DISSO O INTERVALO E BURACO DE AQUISICAO, NAO AMOSTRA
	static constexpr float STILL_ACCEL = 0.20f;        // (m/s^2) TOLERANCIA DE |a|-g NO DETECTOR DE REPOUSO
	static constexpr float STILL_GYRO  = 0.01745329f;  // (rad/s) UM GRAU POR SEGUNDO

	float q[4], b[3], P[6][6];
	float mount[3][3];
	float previous[3];
	float gyroPrev[3];
	float nominal;
	bool  started, primed;

	void quatMul(const float* q1, const float* q2, float* out){
		out[0] = q1[0]*q2[0] - q1[1]*q2[1] - q1[2]*q2[2] - q1[3]*q2[3];
		out[1] = q1[0]*q2[1] + q1[1]*q2[0] + q1[2]*q2[3] - q1[3]*q2[2];
		out[2] = q1[0]*q2[2] - q1[1]*q2[3] + q1[2]*q2[0] + q1[3]*q2[1];
		out[3] = q1[0]*q2[3] + q1[1]*q2[2] - q1[2]*q2[1] + q1[3]*q2[0];
	}

	// EXPONENCIAL EXATA DO VETOR DE ROTACAO: NO PASSO CHEIO O SENO JA NAO E LINEAR
	void quatFromRotVec(const float* rotVec, float* out){
		const float angle = sqrtf(rotVec[0]*rotVec[0] + rotVec[1]*rotVec[1] + rotVec[2]*rotVec[2]);

		if(angle < 1e-12f){
			out[0] = 1.0f;
			for(int i = 0; i < 3; i++) out[i+1] = rotVec[i] / 2.0f;
			return;
		}

		const float scale = sinf(angle/2.0f) / angle;
		out[0] = cosf(angle/2.0f);
		for(int i = 0; i < 3; i++) out[i+1] = rotVec[i] * scale;
	}

	// CORPO -> NAVEGACAO NA CONVENCAO DE HAMILTON (v_nav = R * v_corpo)
	void quatToDCM(const float* quat, float R[3][3]){
		const float w = quat[0], x = quat[1], y = quat[2], z = quat[3];

		R[0][0] = 1-2*(y*y+z*z); R[0][1] = 2*(x*y-w*z);   R[0][2] = 2*(x*z+w*y);
		R[1][0] = 2*(x*y+w*z);   R[1][1] = 1-2*(x*x+z*z); R[1][2] = 2*(y*z-w*x);
		R[2][0] = 2*(x*z-w*y);   R[2][1] = 2*(y*z+w*x);   R[2][2] = 1-2*(x*x+y*y);
	}

	void skew(const float* v, float S[3][3]){
		S[0][0] = 0;     S[0][1] = -v[2]; S[0][2] = v[1];
		S[1][0] = v[2];  S[1][1] = 0;     S[1][2] = -v[0];
		S[2][0] = -v[1]; S[2][1] = v[0];  S[2][2] = 0;
	}

	void normalize(float* quat){
		const float norm = sqrtf(quat[0]*quat[0] + quat[1]*quat[1] + quat[2]*quat[2] + quat[3]*quat[3]);

		if(norm < 1e-12f)
			return;

		for(int i = 0; i < 4; i++) quat[i] /= norm;
	}

	// ROTACAO FIXA DE MONTAGEM: v * R, COMO O ENSAIO APLICOU NAS LINHAS DA TABELA
	void rotate(float* v){
		const float in[3] = {v[0], v[1], v[2]};

		for(int i = 0; i < 3; i++)
			v[i] = in[0]*mount[0][i] + in[1]*mount[1][i] + in[2]*mount[2][i];
	}

	void setMount(){
		const float a = radians(KALMAN_ALIGN_X), c1 = cosf(a), s1 = sinf(a);
		const float bb = radians(KALMAN_ALIGN_Y), c2 = cosf(bb), s2 = sinf(bb);
		const float cc = radians(KALMAN_ALIGN_Z), c3 = cosf(cc), s3 = sinf(cc);

		mount[0][0] = c2*c3; mount[0][1] = s1*s2*c3 - c1*s3; mount[0][2] = c1*s2*c3 + s1*s3;
		mount[1][0] = c2*s3; mount[1][1] = s1*s2*s3 + c1*c3; mount[1][2] = c1*s2*s3 - s1*c3;
		mount[2][0] = -s2;   mount[2][1] = s1*c2;            mount[2][2] = c1*c2;
	}

	// NIVELAMENTO PELO ACELEROMETRO: A PROA VEM DE FORA
	void level(const float* up, const float heading){
		const float roll  = atan2f(-up[1], -up[2]);
		const float pitch = atan2f(up[0], sqrtf(up[1]*up[1] + up[2]*up[2]));
		const float yaw   = radians(heading);

		const float cr = cosf(roll/2),  sr = sinf(roll/2);
		const float cp = cosf(pitch/2), sp = sinf(pitch/2);
		const float cy = cosf(yaw/2),   sy = sinf(yaw/2);

		q[0] = cr*cp*cy + sr*sp*sy;
		q[1] = sr*cp*cy - cr*sp*sy;
		q[2] = cr*sp*cy + sr*cp*sy;
		q[3] = cr*cp*sy - sr*sp*cy;
	}

	void predict(const float* rate, const float dt, const float dtQ){
		float w[3], dq[4], out[4], S[3][3], F[6][6] = {}, T[6][6], D[3][3];

		for(int i = 0; i < 3; i++)
			w[i] = rate[i] - b[i];

		float step[3] = {w[0]*dt, w[1]*dt, w[2]*dt};
		quatFromRotVec(step, dq);
		quatMul(q, dq, out);

		for(int i = 0; i < 4; i++) q[i] = out[i];
		normalize(q);

		skew(w, S);
		quatToDCM(dq, D);

		for(int i = 0; i < 6; i++) F[i][i] = 1.0f;

		for(int i = 0; i < 3; i++){
			for(int j = 0; j < 3; j++){
				float square = 0;

				for(int k = 0; k < 3; k++)
					square += S[i][k]*S[k][j];

				F[i][j]   = D[j][i];                                                      // exp(-[w x] dt) EXATO
				F[i][j+3] = -((i == j ? dt : 0.0f) - S[i][j]*dt*dt/2 + square*dt*dt*dt/6);
			}
		}

		for(int i = 0; i < 6; i++)
			for(int j = 0; j < 6; j++){
				T[i][j] = 0;

				for(int k = 0; k < 6; k++)
					T[i][j] += F[i][k]*P[k][j];
			}

		const float qq = KALMAN_GYRO_NOISE*dtQ + KALMAN_BIAS_NOISE*dtQ*dtQ*dtQ/3;
		const float qc = -KALMAN_BIAS_NOISE*dtQ*dtQ/2;
		const float qb = KALMAN_BIAS_NOISE*dtQ;

		for(int i = 0; i < 6; i++)
			for(int j = 0; j < 6; j++){
				P[i][j] = 0;

				for(int k = 0; k < 6; k++)
					P[i][j] += T[i][k]*F[j][k];
			}

		for(int i = 0; i < 3; i++){
			P[i][i]     += qq;
			P[i][i+3]   += qc;
			P[i+3][i]   += qc;
			P[i+3][i+3] += qb;
		}
	}

	// CORRECAO MULTIPLICATIVA COM R = r*I; H ENTRA CHEIA PORQUE SAO SO TRES LINHAS
	void correct(const float H[3][6], const float* innovation, const float r){
		float PH[6][3], S[3][3], inv[3][3], K[6][3], dx[6], A[6][6], T[6][6];

		for(int i = 0; i < 6; i++)
			for(int j = 0; j < 3; j++){
				PH[i][j] = 0;

				for(int k = 0; k < 6; k++)
					PH[i][j] += P[i][k]*H[j][k];
			}

		for(int i = 0; i < 3; i++)
			for(int j = 0; j < 3; j++){
				S[i][j] = (i == j) ? r : 0.0f;

				for(int k = 0; k < 6; k++)
					S[i][j] += H[i][k]*PH[k][j];
			}

		const float det = S[0][0]*(S[1][1]*S[2][2] - S[1][2]*S[2][1])
						- S[0][1]*(S[1][0]*S[2][2] - S[1][2]*S[2][0])
						+ S[0][2]*(S[1][0]*S[2][1] - S[1][1]*S[2][0]);

		if(fabsf(det) < 1e-20f)    // INOVACAO SEM INFORMACAO: MELHOR NAO CORRIGIR QUE DIVIDIR POR ZERO
			return;

		inv[0][0] =  (S[1][1]*S[2][2] - S[1][2]*S[2][1])/det;
		inv[0][1] = -(S[0][1]*S[2][2] - S[0][2]*S[2][1])/det;
		inv[0][2] =  (S[0][1]*S[1][2] - S[0][2]*S[1][1])/det;
		inv[1][0] = -(S[1][0]*S[2][2] - S[1][2]*S[2][0])/det;
		inv[1][1] =  (S[0][0]*S[2][2] - S[0][2]*S[2][0])/det;
		inv[1][2] = -(S[0][0]*S[1][2] - S[0][2]*S[1][0])/det;
		inv[2][0] =  (S[1][0]*S[2][1] - S[1][1]*S[2][0])/det;
		inv[2][1] = -(S[0][0]*S[2][1] - S[0][1]*S[2][0])/det;
		inv[2][2] =  (S[0][0]*S[1][1] - S[0][1]*S[1][0])/det;

		for(int i = 0; i < 6; i++)
			for(int j = 0; j < 3; j++){
				K[i][j] = 0;

				for(int k = 0; k < 3; k++)
					K[i][j] += PH[i][k]*inv[k][j];
			}

		for(int i = 0; i < 6; i++){
			dx[i] = 0;

			for(int k = 0; k < 3; k++)
				dx[i] += K[i][k]*innovation[k];
		}

		float dq[4], out[4];
		quatFromRotVec(dx, dq);
		quatMul(q, dq, out);

		for(int i = 0; i < 4; i++) q[i] = out[i];
		normalize(q);

		for(int i = 0; i < 3; i++)
			b[i] += dx[i+3];

		for(int i = 0; i < 6; i++)
			for(int j = 0; j < 6; j++){
				A[i][j] = (i == j) ? 1.0f : 0.0f;

				for(int k = 0; k < 3; k++)
					A[i][j] -= K[i][k]*H[k][j];
			}

		for(int i = 0; i < 6; i++)
			for(int j = 0; j < 6; j++){
				T[i][j] = 0;

				for(int k = 0; k < 6; k++)
					T[i][j] += A[i][k]*P[k][j];
			}

		for(int i = 0; i < 6; i++)
			for(int j = 0; j < 6; j++){
				P[i][j] = 0;

				for(int k = 0; k < 6; k++)
					P[i][j] += T[i][k]*A[j][k];                  // FORMA DE JOSEPH, ROBUSTA A ERRO NUMERICO

				for(int k = 0; k < 3; k++)
					P[i][j] += K[i][k]*r*K[j][k];
			}

		for(int i = 0; i < 6; i++)
			for(int j = i+1; j < 6; j++)
				P[i][j] = P[j][i] = (P[i][j] + P[j][i])/2;
	}

	// ANGULOS DO QUATERNION NA MESMA SEQUENCIA DO ENSAIO, SEM SALTO DE 360 ENTRE AMOSTRAS
	void euler(){
		const float w = q[0], x = q[1], y = q[2], z = q[3];
		float angles[3];

		angles[0] = degrees(atan2f(2*(w*x + y*z), 1 - 2*(x*x + y*y)));
		angles[1] = degrees(asinf(constrain(2*(w*y - z*x), -1.0f, 1.0f)));
		angles[2] = degrees(atan2f(2*(w*z + x*y), 1 - 2*(y*y + z*z)));

		for(int i = 0; i < 3; i++){
			angles[i] += 360.0f * roundf((previous[i] - angles[i]) / 360.0f);
			previous[i] = angles[i];
		}

		roll  = angles[0];
		pitch = angles[1];
		yaw   = angles[2];
	}

  public:
	float pitch, roll, yaw;

	void setup(const float dt){
		nominal = dt;
		setMount();
		reset();
	}

	void update(const float* sensors, const float* angles, const float dt){
		float accel[3] = {sensors[0], sensors[1], sensors[2]};
		float gyro[3]  = {(float) radians(sensors[3]), (float) radians(sensors[4]), (float) radians(sensors[5])};

		rotate(accel);
		rotate(gyro);

		if(!primed){    // A PRIMEIRA AMOSTRA SO GUARDA O GIRO: SEM ANTERIOR NAO HA ACELERACAO ANGULAR, E O BRACO DE ALAVANCA ENTRARIA TORTO NO NIVELAMENTO
			for(int i = 0; i < 3; i++)
				gyroPrev[i] = gyro[i];

			primed = true;
			pitch  = angles[0];
			roll   = angles[1];
			yaw    = angles[2];
			return;
		}

		float lever[3], alpha[3], rate[3], S[3][3], A[3][3];
		const bool  gap  = started && (dt > GAP_FACTOR*nominal);
		const float dtQ  = started ? dt : 0.0f;
		const float step = (dtQ > GAP_FACTOR*nominal) ? GAP_FACTOR*nominal : dtQ;

		for(int i = 0; i < 3; i++){
			alpha[i] = (!gap && dt > 0) ? (gyro[i] - gyroPrev[i])/dt : 0.0f;
			rate[i]  = (!gap) ? gyro[i] - KALMAN_GYRO_PHASE*(gyro[i] - gyroPrev[i]) : gyro[i];
		}

		skew(gyro, S);
		skew(alpha, A);

		for(int i = 0; i < 3; i++){                     // ACELERACAO DO BRACO DE ALAVANCA, QUE NAO E GRAVIDADE
			lever[i] = 0;

			for(int j = 0; j < 3; j++){
				float square = 0;

				for(int k = 0; k < 3; k++)
					square += S[i][k]*S[k][j];

				lever[i] += (square + A[i][j]) * KALMAN_LEVER[j];
			}

			accel[i] -= lever[i];
			gyroPrev[i] = gyro[i];
		}

		const float norm = sqrtf(accel[0]*accel[0] + accel[1]*accel[1] + accel[2]*accel[2]);
		const float span = sqrtf(gyro[0]*gyro[0] + gyro[1]*gyro[1] + gyro[2]*gyro[2]);

		if(!started){
			float up[3] = {0.0f, 0.0f, -1.0f};    // SEM LEITURA UTIL, COMECA NIVELADO

			if(norm > 1e-6f)
				for(int i = 0; i < 3; i++)
					up[i] = accel[i]/norm;

			level(up, isnan(KALMAN_HEADING) ? angles[2] : KALMAN_HEADING);
			started = true;
		}

		predict(rate, step, dtQ);

		if(gap)                                        // BURACO: SO O ACCEL REANCORA A ATITUDE
			for(int i = 0; i < 3; i++)
				for(int j = 0; j < 3; j++)
					P[i][j] = (i == j) ? TILT_P0 : 0.0f;

		if(norm > 1e-6f){
			float R[3][3], H[3][6] = {}, innovation[3], h[3];
			quatToDCM(q, R);

			for(int i = 0; i < 3; i++){
				h[i] = -R[2][i];                       // R^T * [0,0,-1] E MENOS A TERCEIRA LINHA
				innovation[i] = accel[i]/norm - h[i];
			}

			float hs[3][3];
			skew(h, hs);

			for(int i = 0; i < 3; i++)
				for(int j = 0; j < 3; j++)
					H[i][j] = hs[i][j];

			const float ratio = (norm - KALMAN_GRAVITY)/KALMAN_GRAVITY;
			correct(H, innovation, KALMAN_ACCEL_NOISE * (1 + KALMAN_ACCEL_GATE*ratio*ratio));
		}

		if(fabsf(norm - KALMAN_GRAVITY) < STILL_ACCEL && span < STILL_GYRO){
			float H[3][6] = {}, innovation[3];

			for(int i = 0; i < 3; i++){
				H[i][i+3] = 1.0f;
				innovation[i] = gyro[i] - b[i];
			}

			correct(H, innovation, KALMAN_ZUPT_NOISE);
		}

		euler();
	}

	void reset(){
		memset(P, 0, sizeof(P));
		memset(b, 0, sizeof(b));
		memset(gyroPrev, 0, sizeof(gyroPrev));
		memset(previous, 0, sizeof(previous));

		q[0] = 1; q[1] = 0; q[2] = 0; q[3] = 0;

		for(int i = 0; i < 3; i++){
			P[i][i]     = TILT_P0;
			P[i+3][i+3] = BIAS_P0;
		}

		pitch = 0; roll = 0; yaw = 0;
		started = false;
		primed  = false;
	}

	String toString(){
		return String(KALMAN_NAME);
	}
};

#endif
