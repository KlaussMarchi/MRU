#ifndef KALMAN_MODEL_H
#define KALMAN_MODEL_H
#include <Arduino.h>
#include <cmath>
#include <cstring>
#include "config.h"

#ifndef KALMAN_REAL
#define KALMAN_REAL float
#endif


// MEKF DE ATITUDE COM OSCILADORES HARMONICOS (WO 2011/034435) E CADEIA DE HEAVE DO MRU-5 (EP 2 092 402), ESPELHO DO KalmanFilter DO 1 - Model.ipynb
class KalmanModel{
  private:
	typedef KALMAN_REAL real;

	static constexpr real PI_R        = 3.14159265358979323846;
	static constexpr real TILT_P0     = 1.0;          // (rad^2) INCLINACAO INICIAL DESCONHECIDA: DEIXA O ACCEL PUXAR
	static constexpr real YAW_P0      = 1e-4;         // (rad^2) A PROA VEM DE FORA: SEM ISSO A CORRECAO DE INCLINACAO VAZA PARA O YAW
	static constexpr real BIAS_P0     = 1e-4;         // (rad/s)^2 BIAS INICIAL TIPICO DE UM MEMS JA COMPENSADO
	static constexpr real GAP_FACTOR  = 3.0;          // ACIMA DISSO O INTERVALO E BURACO DE AQUISICAO, NAO AMOSTRA
	static constexpr real MIN_STEP    = 0.5;          // FRACAO DO PASSO NOMINAL ABAIXO DA QUAL A DIFERENCA DO GIRO NAO VIRA DERIVADA
	static constexpr real ALPHA_TIME  = 0.05;         // (s) JANELA DA DERIVADA DO GIRO: A 100 Hz UM PASSO SO MULTIPLICA O RUIDO POR 1/dt
	static const int SPAN_MAX         = 16;           // AMOSTRAS GUARDADAS PARA A JANELA: COBRE ATE 320 Hz
	static constexpr real STILL_ACCEL = 0.20;         // (m/s^2) TOLERANCIA DE |a|-g NO DETECTOR DE REPOUSO
	static constexpr real STILL_GYRO  = 0.017453292519943295;    // (rad/s) UM GRAU POR SEGUNDO
	static constexpr real STILL_TIME  = 1.0;          // (s) REPOUSO CONTINUO EXIGIDO: O PENDULO PARA UM INSTANTE EM CADA INVERSAO
	static constexpr real ALIGN_TIME  = 10.0;         // (s) O HEAVE DO CG SO INTEGRA DEPOIS QUE A INCLINACAO CONVERGIU
	static constexpr real OSC_PERIOD  = 9.0;          // (s) PERIODO INICIAL DOS OSCILADORES, O DO EXEMPLO DA WO
	static constexpr real OSC_DAMPING = 0.05;         // (1/s) AMORTECIMENTO INICIAL, O DO EXEMPLO DA WO
	static constexpr real OSC_NOISE   = 1.0;          // (rad/s^2)^2/Hz RUIDO DE PROCESSO DA TAXA NOS OSCILADORES
	static constexpr real OSC_MEMORY  = 30.0;         // (s) MEMORIA DOS MINIMOS QUADRADOS DE Omega E D (Eq. 18)
	static constexpr real OSC_PRIOR   = 1e-2;         // PESO DOS VALORES INICIAIS NOS MINIMOS QUADRADOS
	static constexpr real OMEGA_MIN   = 2*PI_R/30;
	static constexpr real OMEGA_MAX   = 2*PI_R/0.5;
	static constexpr real DAMPING_MAX = 2.0;

	real q[4], b[3], P[6][6];
	real mount[3][3], lever[3], point[3];
	real gyroPrev[3], held[3], previous[3];
	real history[SPAN_MAX][3], stamps[SPAN_MAX], clock;
	real ox[3][2], oP[3][2][2], Om2[3], D[3], Sxx[3][2][2], Sxy[3][2];
	real vel[2], pos[2], gp[2], hs[2], aPrev, gPrev, y1Prev;
	real nominal, still, settle, heading, wc;
	int span, stored, head;
	bool primed, started, hasHeld, wasSpike, chained;

	void quatMul(const real* q1, const real* q2, real* out){
		out[0] = q1[0]*q2[0] - q1[1]*q2[1] - q1[2]*q2[2] - q1[3]*q2[3];
		out[1] = q1[0]*q2[1] + q1[1]*q2[0] + q1[2]*q2[3] - q1[3]*q2[2];
		out[2] = q1[0]*q2[2] - q1[1]*q2[3] + q1[2]*q2[0] + q1[3]*q2[1];
		out[3] = q1[0]*q2[3] + q1[1]*q2[2] - q1[2]*q2[1] + q1[3]*q2[0];
	}

	// EXPONENCIAL EXATA DO VETOR DE ROTACAO: NO PASSO CHEIO O SENO JA NAO E LINEAR
	void quatFromRotVec(const real* rotVec, real* out){
		const real angle = std::sqrt(rotVec[0]*rotVec[0] + rotVec[1]*rotVec[1] + rotVec[2]*rotVec[2]);

		if(angle < 1e-12){
			out[0] = 1;
			for(int i = 0; i < 3; i++) out[i+1] = rotVec[i]/2;
			return;
		}

		const real scale = std::sin(angle/2)/angle;
		out[0] = std::cos(angle/2);
		for(int i = 0; i < 3; i++) out[i+1] = rotVec[i]*scale;
	}

	// CORPO -> NAVEGACAO NA CONVENCAO DE HAMILTON (v_nav = R * v_corpo)
	void quatToDCM(const real* quat, real R[3][3]){
		const real w = quat[0], x = quat[1], y = quat[2], z = quat[3];

		R[0][0] = 1-2*(y*y+z*z); R[0][1] = 2*(x*y-w*z);   R[0][2] = 2*(x*z+w*y);
		R[1][0] = 2*(x*y+w*z);   R[1][1] = 1-2*(x*x+z*z); R[1][2] = 2*(y*z-w*x);
		R[2][0] = 2*(x*z-w*y);   R[2][1] = 2*(y*z+w*x);   R[2][2] = 1-2*(x*x+y*y);
	}

	void skew(const real* v, real S[3][3]){
		S[0][0] = 0;     S[0][1] = -v[2]; S[0][2] = v[1];
		S[1][0] = v[2];  S[1][1] = 0;     S[1][2] = -v[0];
		S[2][0] = -v[1]; S[2][1] = v[0];  S[2][2] = 0;
	}

	void cross(const real* a, const real* v, real* out){
		out[0] = a[1]*v[2] - a[2]*v[1];
		out[1] = a[2]*v[0] - a[0]*v[2];
		out[2] = a[0]*v[1] - a[1]*v[0];
	}

	void apply(const real R[3][3], const real* v, real* out){
		for(int i = 0; i < 3; i++)
			out[i] = R[i][0]*v[0] + R[i][1]*v[1] + R[i][2]*v[2];
	}

	void normalize(real* quat){
		const real norm = std::sqrt(quat[0]*quat[0] + quat[1]*quat[1] + quat[2]*quat[2] + quat[3]*quat[3]);

		for(int i = 0; i < 4; i++)
			quat[i] /= norm;
	}

	// ROTACAO FIXA DE MONTAGEM: v * R, COMO O NOTEBOOK APLICA NAS LINHAS DA TABELA
	void rotate(real* v){
		const real in[3] = {v[0], v[1], v[2]};

		for(int i = 0; i < 3; i++)
			v[i] = in[0]*mount[0][i] + in[1]*mount[1][i] + in[2]*mount[2][i];
	}

	void setMount(){
		const real a = KALMAN_ALIGN_X*PI_R/180, c1 = std::cos(a), s1 = std::sin(a);
		const real e = KALMAN_ALIGN_Y*PI_R/180, c2 = std::cos(e), s2 = std::sin(e);
		const real c = KALMAN_ALIGN_Z*PI_R/180, c3 = std::cos(c), s3 = std::sin(c);

		mount[0][0] = c2*c3; mount[0][1] = s1*s2*c3 - c1*s3; mount[0][2] = c1*s2*c3 + s1*s3;
		mount[1][0] = c2*s3; mount[1][1] = s1*s2*s3 + c1*c3; mount[1][2] = c1*s2*s3 - s1*c3;
		mount[2][0] = -s2;   mount[2][1] = s1*c2;            mount[2][2] = c1*c2;
	}

	// NIVELAMENTO PELO ACELEROMETRO COM A PROA DE FORA; INCERTEZA SO NA INCLINACAO
	void level(const real* up){
		const real roll  = std::atan2(-up[1], -up[2]);
		const real pitch = std::atan2(up[0], std::sqrt(up[1]*up[1] + up[2]*up[2]));
		const real yaw   = heading*PI_R/180;

		const real cr = std::cos(roll/2),  sr = std::sin(roll/2);
		const real cp = std::cos(pitch/2), sp = std::sin(pitch/2);
		const real cy = std::cos(yaw/2),   sy = std::sin(yaw/2);

		q[0] = cr*cp*cy + sr*sp*sy;
		q[1] = sr*cp*cy - cr*sp*sy;
		q[2] = cr*sp*cy + sr*cp*sy;
		q[3] = cr*cp*sy - sr*sp*cy;

		const real diag[3] = {TILT_P0, TILT_P0, YAW_P0};
		tilt(diag);
	}

	// P DE ATITUDE = C^T diag C: VARIANCIAS DADAS NO REFERENCIAL DE NAVEGACAO, ESTADO DE ERRO NO DO CORPO
	void tilt(const real* diag){
		real C[3][3];
		quatToDCM(q, C);

		for(int i = 0; i < 3; i++)
			for(int j = 0; j < 3; j++){
				P[i][j] = 0;

				for(int k = 0; k < 3; k++)
					P[i][j] += C[k][i]*diag[k]*C[k][j];
			}
	}

	void predict(const real* rate, const real dt, const real dtQ){
		real w[3], dq[4], out[4], S[3][3], F[6][6] = {}, T[6][6], E[3][3];

		for(int i = 0; i < 3; i++)
			w[i] = rate[i] - b[i];

		const real step[3] = {w[0]*dt, w[1]*dt, w[2]*dt};
		quatFromRotVec(step, dq);
		quatMul(q, dq, out);

		for(int i = 0; i < 4; i++) q[i] = out[i];
		normalize(q);

		skew(w, S);
		quatToDCM(dq, E);

		for(int i = 0; i < 6; i++) F[i][i] = 1;

		for(int i = 0; i < 3; i++){
			for(int j = 0; j < 3; j++){
				real square = 0;

				for(int k = 0; k < 3; k++)
					square += S[i][k]*S[k][j];

				F[i][j]   = E[j][i];                                                   // exp(-[w x] dt) EXATO
				F[i][j+3] = -((i == j ? dt : 0) - S[i][j]*dt*dt/2 + square*dt*dt*dt/6);
			}
		}

		for(int i = 0; i < 6; i++)
			for(int j = 0; j < 6; j++){
				T[i][j] = 0;

				for(int k = 0; k < 6; k++)
					T[i][j] += F[i][k]*P[k][j];
			}

		for(int i = 0; i < 6; i++)
			for(int j = 0; j < 6; j++){
				P[i][j] = 0;

				for(int k = 0; k < 6; k++)
					P[i][j] += T[i][k]*F[j][k];
			}

		const real qq = KALMAN_GYRO_NOISE*dtQ + KALMAN_BIAS_NOISE*dtQ*dtQ*dtQ/3;
		const real qc = -KALMAN_BIAS_NOISE*dtQ*dtQ/2;
		const real qb = KALMAN_BIAS_NOISE*dtQ;

		for(int i = 0; i < 3; i++){
			P[i][i]     += qq;
			P[i][i+3]   += qc;
			P[i+3][i]   += qc;
			P[i+3][i+3] += qb;
		}
	}

	// CORRECAO MULTIPLICATIVA COM R = r*I SEM TOCAR A PROA: NENHUMA MEDIDA AQUI A OBSERVA, E JOSEPH VALE PARA O GANHO RESTRITO
	void correct(const real H[3][6], const real* innovation, const real r){
		real PH[6][3], S[3][3], inv[3][3], K[6][3], dx[6], A[6][6], T[6][6], C[3][3];

		for(int i = 0; i < 6; i++)
			for(int j = 0; j < 3; j++){
				PH[i][j] = 0;

				for(int k = 0; k < 6; k++)
					PH[i][j] += P[i][k]*H[j][k];
			}

		for(int i = 0; i < 3; i++)
			for(int j = 0; j < 3; j++){
				S[i][j] = (i == j) ? r : 0;

				for(int k = 0; k < 6; k++)
					S[i][j] += H[i][k]*PH[k][j];
			}

		const real det = S[0][0]*(S[1][1]*S[2][2] - S[1][2]*S[2][1])
					   - S[0][1]*(S[1][0]*S[2][2] - S[1][2]*S[2][0])
					   + S[0][2]*(S[1][0]*S[2][1] - S[1][1]*S[2][0]);

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

		quatToDCM(q, C);    // C[2] E A VERTICAL DA NAVEGACAO VISTA NO CORPO

		for(int j = 0; j < 3; j++){
			const real along = C[2][0]*K[0][j] + C[2][1]*K[1][j] + C[2][2]*K[2][j];

			for(int i = 0; i < 3; i++)
				K[i][j] -= C[2][i]*along;
		}

		for(int i = 0; i < 6; i++){
			dx[i] = 0;

			for(int k = 0; k < 3; k++)
				dx[i] += K[i][k]*innovation[k];
		}

		real dq[4], out[4];
		quatFromRotVec(dx, dq);
		quatMul(q, dq, out);

		for(int i = 0; i < 4; i++) q[i] = out[i];
		normalize(q);

		for(int i = 0; i < 3; i++)
			b[i] += dx[i+3];

		for(int i = 0; i < 6; i++)
			for(int j = 0; j < 6; j++){
				A[i][j] = (i == j) ? 1 : 0;

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
					P[i][j] += T[i][k]*A[j][k];

				for(int k = 0; k < 3; k++)
					P[i][j] += K[i][k]*r*K[j][k];
			}

		for(int i = 0; i < 6; i++)
			for(int j = i+1; j < 6; j++)
				P[i][j] = P[j][i] = (P[i][j] + P[j][i])/2;
	}

	// UM PASSO DOS TRES OSCILADORES x1'' = -D x1' - Omega^2 x1 MEDIDOS PELA TAXA; Omega^2 E D POR MINIMOS QUADRADOS (Eq. 18)
	void oscillate(const real* measured, const real* derivative, const real dt){
		const real lam      = std::exp(-dt/OSC_MEMORY);
		const real prior[2] = {(2*PI_R/OSC_PERIOD)*(2*PI_R/OSC_PERIOD), OSC_DAMPING};

		for(int i = 0; i < 3; i++){
			const real A[2][2] = {{1, dt}, {-Om2[i]*dt, 1 - D[i]*dt}};
			real x[2], T[2][2], M[2][2], K[2];

			for(int r = 0; r < 2; r++)
				x[r] = A[r][0]*ox[i][0] + A[r][1]*ox[i][1];

			for(int r = 0; r < 2; r++)
				for(int c = 0; c < 2; c++)
					T[r][c] = A[r][0]*oP[i][0][c] + A[r][1]*oP[i][1][c];

			for(int r = 0; r < 2; r++)
				for(int c = 0; c < 2; c++)
					M[r][c] = T[r][0]*A[c][0] + T[r][1]*A[c][1];

			M[1][1] += OSC_NOISE*dt;
			K[0] = M[0][1]/(M[1][1] + KALMAN_RATE_NOISE);
			K[1] = M[1][1]/(M[1][1] + KALMAN_RATE_NOISE);

			const real innovation = measured[i] - x[1];
			ox[i][0] = x[0] + K[0]*innovation;
			ox[i][1] = x[1] + K[1]*innovation;

			for(int r = 0; r < 2; r++)
				for(int c = 0; c < 2; c++)
					oP[i][r][c] = M[r][c] - K[r]*M[1][c];

			const real phi[2] = {-ox[i][0], -ox[i][1]};

			for(int r = 0; r < 2; r++){
				for(int c = 0; c < 2; c++)
					Sxx[i][r][c] = lam*Sxx[i][r][c] + phi[r]*phi[c];

				Sxy[i][r] = lam*Sxy[i][r] + phi[r]*derivative[i];
			}

			const real s00 = Sxx[i][0][0] + OSC_PRIOR, s01 = Sxx[i][0][1], s11 = Sxx[i][1][1] + OSC_PRIOR;
			const real y0  = Sxy[i][0] + OSC_PRIOR*prior[0], y1 = Sxy[i][1] + OSC_PRIOR*prior[1];
			const real det = s00*s11 - s01*s01;
			Om2[i] = std::fmin(std::fmax((s11*y0 - s01*y1)/det, OMEGA_MIN*OMEGA_MIN), OMEGA_MAX*OMEGA_MAX);
			D[i]   = std::fmin(std::fmax((s00*y1 - s01*y0)/det, (real) 0), DAMPING_MAX);
		}

		for(int i = 0; i < 3; i++){
			rate[i]   = ox[i][1];
			alpha[i]  = -Om2[i]*ox[i][0] - D[i]*ox[i][1];
			period[i] = 2*PI_R/std::sqrt(Om2[i]);
		}
	}

	// SECAO z'' = u - 2 eps wc z' - wc^2 z DOS FILTROS DO MRU-5, ENTRADA LINEAR DENTRO DO PASSO
	void section(real* z, const real u0, const real u1, const real dt){
		const real e  = KALMAN_HEAVE_DAMPING;
		const real w0 = u0 - 2*e*wc*z[1] - wc*wc*z[0];
		const real w1 = u1 - 2*e*wc*z[1] - wc*wc*z[0];
		const real z0 = z[0] + z[1]*dt + dt*dt*(2*w0 + w1)/6;
		const real z1 = z[1] + dt*(w0 + w1)/2;

		z[0] = z0;
		z[1] = z1;
	}

	// HEAVE NO PONTO = CG (GP NA VELOCIDADE E HS NA POSICAO) + TERMO GEOMETRICO (R m)_z PELO MESMO GP*HS
	void chain(const real aCg, const real geo, const real dGeo, real dt){
		const real e = KALMAN_HEAVE_DAMPING;

		if(!chained){
			gp[0] = geo/(wc*wc); gp[1] = 0;
			hs[0] = 0; hs[1] = 0;
			aPrev = aCg; gPrev = geo; y1Prev = 0;
			chained = true;
			dt = 0;
		}

		real v[2] = {vel[0], vel[1]};
		section(v, aPrev, aCg, dt);
		section(pos, vel[1], v[1], dt);
		vel[0] = v[0]; vel[1] = v[1];
		section(gp, gPrev, geo, dt);

		const real y1 = geo - 2*e*wc*gp[1] - wc*wc*gp[0];
		section(hs, y1Prev, y1, dt);
		aPrev = aCg; gPrev = geo; y1Prev = y1;

		const real y2  = y1 + 2*e*wc*hs[1] - wc*wc*hs[0];
		const real dy1 = dGeo - 2*e*wc*y1 - wc*wc*gp[1];
		heave     = pos[1] + 4*e*wc*pos[0] + y2;
		heaveRate = vel[1] + 2*e*wc*pos[1] - wc*wc*pos[0] + dy1 + 2*e*wc*(y1 - 2*e*wc*hs[1] - wc*wc*hs[0]) - wc*wc*hs[1];
	}

	// ANGULOS DO QUATERNION NA MESMA SEQUENCIA DO ENSAIO, SEM SALTO DE 360 ENTRE AMOSTRAS
	void euler(){
		const real w = q[0], x = q[1], y = q[2], z = q[3];
		const real sine = std::fmin(std::fmax(2*(w*y - z*x), (real) -1), (real) 1);
		real angles[3];

		angles[0] = std::atan2(2*(w*x + y*z), 1 - 2*(x*x + y*y))*180/PI_R;
		angles[1] = std::asin(sine)*180/PI_R;
		angles[2] = std::atan2(2*(w*z + x*y), 1 - 2*(y*y + z*z))*180/PI_R;

		for(int i = 0; i < 3; i++){
			angles[i] += 360*std::round((previous[i] - angles[i])/360);
			previous[i] = angles[i];
		}

		roll  = angles[0];
		pitch = angles[1];
		yaw   = angles[2];
	}

	// GIRO DA AMOSTRA NO ANEL QUE A JANELA DA DERIVADA LE
	void push(const real* w){
		for(int i = 0; i < 3; i++)
			history[head][i] = w[i];

		stamps[head] = clock;
		head   = (head + 1) % SPAN_MAX;
		stored = stored < SPAN_MAX ? stored + 1 : SPAN_MAX;
	}

	// BURACO: SO O ACCEL REANCORA A INCLINACAO, A PROA GUARDA A INCERTEZA, OSCILADORES E HEAVE RECOMECAM
	void restart(){
		real C[3][3], yawVar = 0;
		quatToDCM(q, C);

		for(int i = 0; i < 3; i++)
			for(int j = 0; j < 3; j++)
				yawVar += C[2][i]*P[i][j]*C[2][j];

		const real diag[3] = {TILT_P0, TILT_P0, yawVar};
		tilt(diag);

		for(int i = 0; i < 3; i++)
			for(int j = 3; j < 6; j++)
				P[i][j] = P[j][i] = 0;

		for(int i = 0; i < 3; i++){
			ox[i][0] = 0; ox[i][1] = 0;
			oP[i][0][0] = 1; oP[i][0][1] = 0; oP[i][1][0] = 0; oP[i][1][1] = 1;
		}

		vel[0] = vel[1] = pos[0] = pos[1] = 0;
		chained = false;
		hasHeld = false;
	}

  public:
	real pitch, roll, yaw;                   // graus, sequencia xyz do ensaio
	real heave, heaveRate, heaveAccel;       // m, m/s e m/s^2 no ponto de medida, positivos para baixo
	real rate[3], alpha[3], period[3];       // taxa (rad/s) e aceleracao angular (rad/s^2) filtradas pelos osciladores, periodo (s)
	real accel[3];                           // m/s^2 no ponto de medida, navegacao (z para baixo), sem a gravidade

	void setup(const real dt){
		nominal = dt;
		wc      = 2*PI_R/(10*KALMAN_HEAVE_PERIOD);
		span    = (int) (ALPHA_TIME/dt + (real) 0.5);
		span    = span < 1 ? 1 : (span > SPAN_MAX ? SPAN_MAX : span);
		setMount();

		for(int i = 0; i < 3; i++){
			lever[i] = KALMAN_LEVER[i];
			point[i] = KALMAN_POINT[i];
		}

		reset();
	}

	void update(const real* sensors, const real* angles, const real dt){
		real f[3] = {(real) (sensors[0]*KALMAN_G0), (real) (sensors[1]*KALMAN_G0), (real) (sensors[2]*KALMAN_G0)};    // O MODO HR DO KERNEL ENTREGA g
		real w[3] = {(real) (sensors[3]*PI_R/180), (real) (sensors[4]*PI_R/180), (real) (sensors[5]*PI_R/180)};

		rotate(f);
		rotate(w);

		if(!primed){    // A PRIMEIRA AMOSTRA SO GUARDA O GIRO: SEM ANTERIOR NAO HA ACELERACAO ANGULAR, E O BRACO DE ALAVANCA ENTRARIA TORTO NO NIVELAMENTO
			for(int i = 0; i < 3; i++)
				gyroPrev[i] = w[i];

			push(w);
			heading = std::isnan((real) KALMAN_HEADING) ? angles[2] : (real) KALMAN_HEADING;
			pitch   = angles[0];
			roll    = angles[1];
			yaw     = angles[2];
			primed  = true;
			return;
		}

		const bool first = !started;
		const bool gap   = !first && dt > GAP_FACTOR*nominal;
		const real step  = std::fmin(dt, GAP_FACTOR*nominal);
		const int back   = span < stored ? span : stored;
		const int index  = (head - back + SPAN_MAX) % SPAN_MAX;
		clock  += dt;
		settle  = gap ? 0 : settle + dt;
		stored  = gap ? 0 : stored;

		const real elapsed = std::fmax(clock - stamps[index], MIN_STEP*nominal*back);
		const real fnorm   = std::sqrt(f[0]*f[0] + f[1]*f[1] + f[2]*f[2]);
		const real wnorm   = std::sqrt(w[0]*w[0] + w[1]*w[1] + w[2]*w[2]);
		still = (std::fabs(fnorm - KALMAN_GRAVITY) < STILL_ACCEL && wnorm < STILL_GYRO) ? still + dt : 0;

		const bool rest = still >= STILL_TIME;    // PARADO NAO HA ROTACAO: O BRACO DE ALAVANCA SO TRARIA O RUIDO DO GIRO
		real dw[3], rateIn[3], centri[3], tang[3], fc[3], wl[3];

		for(int i = 0; i < 3; i++){
			dw[i]     = gap ? 0 : (w[i] - history[index][i])/elapsed;
			rateIn[i] = gap ? w[i] : w[i] - KALMAN_GYRO_PHASE*(w[i] - gyroPrev[i]);
		}

		push(w);
		cross(w, lever, wl);
		cross(w, wl, centri);
		cross(dw, lever, tang);

		for(int i = 0; i < 3; i++)
			fc[i] = rest ? f[i] : f[i] - centri[i] - tang[i];

		const real norm = std::sqrt(fc[0]*fc[0] + fc[1]*fc[1] + fc[2]*fc[2]);

		if(first){
			real up[3] = {0, 0, -1};    // SEM LEITURA UTIL, COMECA NIVELADO

			if(norm > 1e-6)
				for(int i = 0; i < 3; i++)
					up[i] = fc[i]/norm;

			level(up);
			started = true;
		}

		if(!first)
			predict(rateIn, step, dt);

		if(gap)
			restart();

		real C[3][3], nav[3];
		quatToDCM(q, C);
		apply(C, fc, nav);
		nav[2] += KALMAN_GRAVITY;

		const real jump  = std::sqrt((nav[0]-held[0])*(nav[0]-held[0]) + (nav[1]-held[1])*(nav[1]-held[1]) + (nav[2]-held[2])*(nav[2]-held[2]));
		const bool spike = hasHeld && !wasSpike && jump > KALMAN_SPIKE;
		wasSpike = spike;

		if(norm > 1e-6 && !spike){
			real H[3][6] = {}, innovation[3], h[3], hs3[3][3];

			for(int i = 0; i < 3; i++)
				h[i] = -C[2][i];                        // R^T * [0,0,-1] E MENOS A TERCEIRA LINHA

			skew(h, hs3);

			for(int i = 0; i < 3; i++){
				innovation[i] = fc[i]/norm - h[i];

				for(int j = 0; j < 3; j++)
					H[i][j] = hs3[i][j];
			}

			const real ratio = (norm - KALMAN_GRAVITY)/KALMAN_GRAVITY;
			correct(H, innovation, rest ? KALMAN_STILL_NOISE : KALMAN_ACCEL_NOISE*(1 + KALMAN_ACCEL_GATE*ratio*ratio));
		}

		if(rest){
			real H[3][6] = {}, innovation[3];

			for(int i = 0; i < 3; i++){
				H[i][i+3] = 1;
				innovation[i] = w[i] - b[i];
			}

			correct(H, innovation, KALMAN_ZUPT_NOISE);
		}

		real measured[3];

		for(int i = 0; i < 3; i++)
			measured[i] = w[i] - b[i];

		oscillate(measured, dw, step);
		quatToDCM(q, C);

		if(!spike){
			apply(C, fc, held);
			held[2] += KALMAN_GRAVITY;
			hasHeld = true;
		}

		real geoVec[3], spin[3], dGeoVec[3];
		apply(C, point, geoVec);
		cross(measured, point, spin);
		apply(C, spin, dGeoVec);
		chain(settle >= ALIGN_TIME ? held[2] : 0, geoVec[2], dGeoVec[2], first ? 0 : step);

		real ap[3], wp[3], cp[3], body[3], out[3];
		cross(alpha, point, ap);
		cross(rate, point, wp);
		cross(rate, wp, cp);

		for(int i = 0; i < 3; i++)
			body[i] = fc[i] + ap[i] + cp[i];

		apply(C, body, out);
		out[2] += KALMAN_GRAVITY;

		for(int i = 0; i < 3; i++){
			accel[i]    = out[i];
			gyroPrev[i] = w[i];
		}

		heaveAccel = out[2];
		euler();
	}

	void reset(){
		memset(P, 0, sizeof(P));
		memset(b, 0, sizeof(b));
		memset(gyroPrev, 0, sizeof(gyroPrev));
		memset(history, 0, sizeof(history));
		memset(stamps, 0, sizeof(stamps));
		memset(previous, 0, sizeof(previous));
		memset(held, 0, sizeof(held));
		memset(ox, 0, sizeof(ox));
		memset(Sxx, 0, sizeof(Sxx));
		memset(Sxy, 0, sizeof(Sxy));
		memset(vel, 0, sizeof(vel));
		memset(pos, 0, sizeof(pos));
		memset(gp, 0, sizeof(gp));
		memset(hs, 0, sizeof(hs));

		q[0] = 1; q[1] = 0; q[2] = 0; q[3] = 0;

		for(int i = 0; i < 3; i++){
			P[i][i]     = TILT_P0;
			P[i+3][i+3] = BIAS_P0;
			Om2[i]      = (2*PI_R/OSC_PERIOD)*(2*PI_R/OSC_PERIOD);
			D[i]        = OSC_DAMPING;
			oP[i][0][0] = 1; oP[i][0][1] = 0; oP[i][1][0] = 0; oP[i][1][1] = 1;
			rate[i]     = alpha[i] = accel[i] = 0;
			period[i]   = OSC_PERIOD;
		}

		pitch = roll = yaw = 0;
		heave = heaveRate = heaveAccel = 0;
		still = settle = heading = clock = 0;
		stored = head = 0;
		aPrev = gPrev = y1Prev = 0;
		primed = started = hasHeld = wasSpike = chained = false;
	}

	String toString(){
		return String(KALMAN_NAME);
	}

};

#endif
