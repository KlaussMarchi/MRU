#ifndef CONSTANTS_H
#define CONSTANTS_H

// CF:device_mode$x! (como o dispositivo inicia: define o baudrate da telemetria e se o streamer segue as configurações ou é forçado)
#define NORMAL_MODE      0         // envia os dados para operação normal do MRU, com base no baudrate das configurações (padrão 9600)
#define ACQUISITION_MODE 1         // só para extrair dados para calibração: baudrate fixo em ACQUISITION_BAUD e streamer forçado em SCALE_MODE + LIST_PROTOCOL

// CF:streamer_mode$x! (quais dados o streamer lê e envia: do processing calibrado, do kernel cru ou do kernel em escala)
#define CALIBRATED_MODE 0          // a gente calcula tudo e envia: filtros, correção, atitude, heave e taxa do heave
#define RAW_MODE        1          // só envia o que é enviado kernel (sem nenhum processamento) no tipo original (inteiros, temperatura em C*10)
#define SCALE_MODE      2          // campos do kernel convertidos para unidades físicas (m/s², graus/s, graus, °C), sem calibração

// CF:protocol$x! (formato de cada amostra que o streamer imprime na serial)
#define JSON_PROTOCOL 0            // envia os dados do MRU no formato JSON {"time": 1.2, "ax": 2.1, "wy": 3.3, ....}
#define LIST_PROTOCOL 1            // uma linha por amostra em lista numérica [time,tmp,pitch,roll,yaw,ax,...], sem nomes, na ordem das chaves do JSON
#define NMEA_PROTOCOL 2            // sentença NMEA $GPPASHR,pitch,roll,yaw,heave*checksum, só com esses 4 campos

// CF:kernel_mode$x! (modo que o kernel envia os dados)
#define HR_MODE 0                  // pacote HR de 60 bytes, inteiros de 32 bits: ângulos, giro e aceleração em alta resolução, mais temperatura
#define QT_MODE 1                  // quaternion q0..q3 mais ângulos e temperatura, sem aceleração e giro; o processing não calibra e o streamer envia só 9 campos
#define OR_MODE 2                  // pacote de orientação de 42 bytes, inteiros de 16 bits: ângulos, giro e aceleração em resolução menor, mais temperatura

// CF:align$x! (como o kernel está montado no equipamento: ângulos de alinhamento proa/pitch/roll que align() grava na flash do kernel)
#define ALIGN_FORWARD     0        // sem rotação: eixos do kernel iguais aos do equipamento (proa/pitch/roll 0/0/0)
#define ALIGN_DOWN        1        // cabeça pra cima (measure em pé) - com barriguinha (pitch -90)
#define ALIGN_UP          2        // cabeça pra baixo (cabo pra baixo) (pitch +90)
#define ALIGN_RESET       3        // alinhamento zerado 0/0/0, igual ao FORWARD, para limpar uma montagem anterior
#define ALIGN_UPSIDE_DOWN 4        // kernel de cabeça pra baixo: proa e roll girados 180 graus


#define ACQUISITION_BAUD 460800    // RS232 e RS422 na aquisição: 200 linhas/s de ~90 bytes ocupam 40%
#endif
