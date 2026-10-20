# Firmware do MRU · ESP32-S3

Este firmware recebe as medições do **Kernel-120**, aplica os ajustes produzidos pela calibração e transmite orientação, aceleração, giro e movimento vertical por **USB, RS232 ou RS422**. O ponto de entrada é [`Main.ino`](Main.ino), que identifica a versão atual como `v1.0.7`.

O [pipeline de calibração](../../../Calibration/README.md) escolhe filtros e ajusta modelos no computador. Aqui, o ESP32 executa esses modelos sobre as novas amostras, usando os parâmetros compilados em `config.h`.

**Visão geral**

```text
Kernel-120 → UART1 → decodificação → escala → filtros → correção → atitude → heave → braço
                                                                                     │
                                                                                     ▼
                                                                          JSON · LIST · NMEA
                                                                                     │
                                                                                     ▼
                                                                            USB · RS232 · RS422

Computador → comandos pela serial → configurações persistentes / controle do stream
Calibration → config.h → compilação do firmware → parâmetros usados no processamento
```

Esse é o caminho calibrado. Os modos RAW e SCALE permitem observar as medições anteriores à calibração.

**Estrutura de arquivos**

```text
Main/
├── Main.ino                         ← setup() e loop() do Arduino
├── device/
│   ├── index.h                     ← reúne e inicializa os módulos
│   ├── settings/index.h            ← configurações persistentes
│   └── tasks/index.h               ← laços de processamento e comunicação
├── globals/
│   ├── constants.h                 ← números que identificam modos e protocolos
│   └── functions.h                 ← função de exemplo, sem papel na cadeia de medição
├── objects/
│   ├── sensors/
│   │   ├── index.h                 ← gerencia o sensor
│   │   └── Kernel/
│   │       ├── index.h             ← conexão, configuração e recepção do Kernel
│   │       ├── HR/index.h          ← pacote de alta resolução
│   │       ├── quat/index.h        ← pacote de quaternion
│   │       └── orient/index.h      ← pacote de orientação
│   ├── processing/
│   │   ├── index.h                 ← executa a sequência de cálculo
│   │   ├── filters/                ← passa-baixa de cada eixo
│   │   ├── correction/             ← matriz, viés e temperatura
│   │   ├── align/                  ← adapta a correção ao align atual
│   │   ├── attitude/
│   │   │   ├── config.h            ← seleciona o modelo compilado
│   │   │   ├── kalman/             ← fusão de acelerômetro e giroscópio
│   │   │   ├── linear/             ← correção linear dos ângulos do Kernel
│   │   │   └── machine/            ← regressão sobre uma janela de sensores
│   │   ├── heave/                  ← movimento vertical do sensor
│   │   └── lever/                  ← movimento vertical no ponto de interesse
│   ├── telemetry/
│   │   ├── index.h                 ← coordena comandos, respostas e transmissão
│   │   ├── serial/index.h          ← portas USB, RS232 e RS422
│   │   ├── protocol/index.h        ← interpretação dos comandos
│   │   └── streamer/index.h        ← formato e cadência das amostras transmitidas
│   ├── components/                 ← LEDs e encoder
│   └── updater/index.h             ← atualização do firmware pela serial
├── utils/                          ← texto, JSON, relógios e estruturas auxiliares
└── build/                          ← artefatos de compilação, quando gerados
```

Nas pastas de processamento, **`index.h` implementa o algoritmo e `config.h` fornece seus parâmetros**. Os arquivos `.h` contêm boa parte da implementação; o `Main.ino` apenas monta e inicia o dispositivo.

**O que acontece ao ligar**

| Ordem | Arquivo e chamada | O que faz | Resultado |
|---|---|---|---|
| **1 · Entrada** | `Main.ino` → `setup()` | Desliga o encoder, habilita LEDs e multitarefa, mantém o sensor real ativo e inicia `Serial` a 115200. | Chama `device.setup()`. |
| **2 · Dispositivo** | `device/index.h` → `Device::setup()` | Gera a identificação a partir do MAC do ESP32, mostra a versão, inicia componentes e carrega as configurações. | Define modo de operação e frequência de transmissão. |
| **3 · Comunicação** | `objects/telemetry/index.h` → `setup()` | Abre RS232/RS422 e configura formato, origem dos dados e início automático do stream. | Comunicação pronta, ainda antes da aquisição do sensor. |
| **4 · Sensor** | `objects/sensors/Kernel/index.h` → `setup()` | Procura o Kernel, configura sua saída, lê o align e solicita o pacote HR, QT ou OR. | Recepção dos pacotes binários. |
| **5 · Processamento** | `objects/processing/index.h` → `setup()` | Monta os filtros, inicializa atitude, heave e braço, e prepara a adaptação de montagem. | Estados e coeficientes prontos para as amostras. |
| **6 · Execução contínua** | `Main.ino` → `loop()` → `tasks.handle()` | Inicia os laços que mantêm sensor, cálculos, LEDs e telemetria funcionando. | O MRU passa a receber, processar e transmitir. |

Com `multitask = true`, `thread0()` executa **sensores → processamento → componentes**; uma tarefa FreeRTOS criada e fixada no núcleo 1 executa `thread1()`, responsável pela telemetria. O código não fixa explicitamente o núcleo do laço original. Com multitarefa desabilitada, os dois caminhos são chamados sequencialmente.

**Como uma amostra atravessa o firmware**

Os arquivos abaixo ficam em `objects/`. As setas representam dados mantidos em memória: o firmware não cria os CSV usados na calibração.

| Etapa e arquivo | Entrada | Operação | Saída → destino |
|---|---|---|---|
| **Recepção** · `sensors/Kernel/index.h` e decodificador do modo | Bytes da UART1 | Localiza `AA 55`, reúne o pacote e verifica a soma de controle. Extrai os campos e registra o instante de início do pacote recebido pelo ESP32. | Inteiros do Kernel e `lastAckTime` → Processing. |
| **Escala** · `processing/index.h` → `scale()` | Inteiros e modo HR/QT/OR | Multiplica cada campo pelo fator de conversão correspondente. | m/s², °/s, graus, °C e quaternion quando disponível → saída SCALE ou cadeia calibrada. |
| **Pré-filtro** · `processing/filters/index.h` | Seis sinais em escala física | Aplica o filtro escolhido para cada eixo do acelerômetro e giroscópio. | Sensores filtrados → Align/Correction. |
| **Correção** · `processing/align/index.h` + `correction/index.h` | Sensores filtrados e temperatura | Adapta os eixos quando o align mudou e aplica matriz, viés e termo térmico. | Sensores corrigidos nos eixos do navio → Attitude e Heave. |
| **Atitude** · `processing/attitude/<modelo>/index.h` | Sensores corrigidos e ângulos originais do Kernel | Executa o modelo selecionado em `attitude/config.h`. | Pitch, roll e yaw → Heave, Lever e saída. |
| **Heave** · `processing/heave/index.h` | Aceleração corrigida, pitch, roll e intervalo de tempo | Encontra a aceleração vertical, compensa a gravidade e integra com rejeição de deriva. | Heave no sensor, em metros → Lever. |
| **Braço** · `processing/lever/index.h` | Heave, inclinação e vetor até o ponto desejado | Acrescenta o deslocamento vertical devido à distância entre sensor e ponto; calcula sua velocidade vertical. | Heave e `heave_rate` no ponto → Streamer. |
| **Transmissão** · `telemetry/streamer/index.h` | Estado mais recente e contador do processamento | Escolhe os campos, verifica a cadência, formata e escreve na porta ativa. | Uma mensagem JSON, LIST ou NMEA → computador ou sistema do navio. |

`Processing::handle()` verifica se `lastAckTime` mudou, evitando processar novamente a mesma amostra. O intervalo usado por atitude e heave vem da diferença entre esses instantes; os coeficientes dos pré-filtros são calculados para a taxa nominal do Kernel.

**1 · Kernel — conexão, pacote e escala**

O driver usa **UART1, TX 4 e RX 3**. No boot, procura resposta em 460800, 115200, 230400 e 921600 baud. Quando encontra o sensor, verifica os parâmetros e grava os que diferem da configuração desejada:

| Parâmetro do Kernel | Valor solicitado | Motivo |
|---|---|---|
| Baud | 460800 | Transportar os pacotes na taxa configurada. |
| Taxa de saída | 200 Hz | Fornecer uma amostra nominal a cada 5 ms. |
| Variante de saída | Média das amostras internas | Reduzir a taxa interna de 2 kHz por média. |
| Passa-baixa interno | 66 Hz | Atenuar componentes rápidas antes da saída reduzida. |

O firmware também lê os três ângulos de `Alignment_Angles`. Para aplicar mudanças persistentes do Kernel, siga o procedimento de desligar e ligar o MRU descrito no [guia geral](../../../README.md); reiniciar somente o ESP32 não corta a alimentação do sensor.

| Modo do Kernel | Decodificador | Conteúdo utilizado | Escala aplicada pelo firmware |
|---|---|---|---|
| **HR · 0** | `HR/index.h` · 60 bytes | Ângulos, aceleração, giro e temperatura. | Aceleração: `9,8106 × 10⁻⁶`; giro: `10⁻⁵`; ângulos: `10⁻³`; temperatura: `0,1`. |
| **QT · 1** | `quat/index.h` · 42 bytes | Ângulos, quaternion e temperatura. | Ângulos: `10⁻²`; quaternion: `10⁻⁴`; temperatura: `0,1`. |
| **OR · 2** | `orient/index.h` · 42 bytes | Ângulos, aceleração, giro e temperatura, com menor resolução. | Aceleração: `9,8106 / 4000`; giro: `0,02`; ângulos: `10⁻²`; temperatura: `0,1`. |

Os fatores multiplicam o inteiro recebido. A aceleração resultante fica em m/s², o giro em °/s e os ângulos em graus. O valor `9,8106` pertence à conversão da escala do Kernel; a gravidade local dos modelos vem dos arquivos exportados pela calibração.

O modo **QT não fornece aceleração e giro**, portanto desabilita a cadeia calibrada. O heave transmitido nesse caminho é zero.

**2 · Filters — aplicar os filtros escolhidos na calibração**

`filters/config.h` informa `FILTERS_TYPE[6]` e `FILTERS_FC[6]`, na ordem `ax, ay, az, wx, wy, wz`. `Filters::setup()` converte esses parâmetros em coeficientes digitais.

| Tipo | Como funciona no ESP32 | Efeito do parâmetro |
|---|---|---|
| **Butterworth de segunda ordem** | Uma seção recursiva combina a entrada atual, duas entradas anteriores e duas saídas anteriores. Usa Tustin com ajuste da frequência. | `fc` define o corte de −3 dB. |
| **Passa-baixa de quatro polos** | Quatro seções de primeira ordem em cascata, com polos iguais e transformação de Tustin. | `fc` define a frequência dos polos; o corte de −3 dB do modelo contínuo é aproximadamente `0,435 × fc`. |
| **Média exponencial** | `y = α·x + (1−α)·y_anterior`, com `α = 1−exp(−2π·fc·dt)`. | Frequência menor suaviza mais; `α` próximo de 1 deixa a leitura quase intacta. |

Os estados começam com a primeira leitura, evitando um salto artificial causado por iniciar em zero. Os seis eixos podem usar filtros e frequências diferentes.

Na calibração, a chamada `genetic` executa **CMA-ES** para escolher os parâmetros. **O firmware aplica o resultado dessa busca**: não executa otimização evolutiva. A filtragem acontece antes de o Streamer reduzir a taxa de saída.

**3 · Correction e Align — corrigir a leitura no referencial certo**

`correction/index.h` aplica, separadamente ao acelerômetro e ao giroscópio:

```text
x_corrigido = M·x + c + k·(T−T0)
```

`M` reúne montagem, escala e mistura entre eixos; `c` é o desvio de zero; `k` é o efeito térmico por grau em relação a `T0`. Esses números foram ajustados nos notebooks, por Wahba/SVD e mínimos quadrados com regularização.

`Align::apply()` envolve essa correção. Se a montagem atual difere da usada no ensaio, primeiro leva a entrada aos eixos da calibração, aplica `correct()` e gira a saída para os eixos atuais do navio. A rotação depende do align lido do Kernel e de `ALIGN_CALIBRATION`/`ALIGN_FRAME`.

Com align igual ou informação indisponível (`NAN`), a correção continua sendo aplicada, mas sem essa rotação adicional. A mensagem de boot informa `sem rotacao` ou `correcao girada`.

**4 · Attitude — o modelo escolhido em tempo de compilação**

[`objects/processing/attitude/config.h`](objects/processing/attitude/config.h) inclui um modelo e define o apelido `AttitudeModel`. Na configuração atual, ele seleciona **`KalmanModel`**. Para trocar de estratégia, exporte a desejada no pipeline de calibração e recompile.

| Modelo | Entrada efetivamente usada | Princípio e comportamento |
|---|---|---|
| **Kalman** · `kalman/index.h` | Aceleração e giro corrigidos; proa inicial configurada ou do Kernel. | Propaga a orientação com o giroscópio e corrige a inclinação pela gravidade observada no acelerômetro. Estima também o desvio do giro. |
| **Linear** · `linear/index.h` | Ângulos originais do Kernel. | Calcula `ângulos = M·ângulos_Kernel + B`. A matriz permite ajustar escala, desvio e acoplamento, conforme os coeficientes exportados. |
| **Machine** · `machine/index.h` | Janela temporal de sensores corrigidos. | Padroniza as entradas com média/desvio do treino e aplica os coeficientes de uma regressão. Atualiza a janela no período `MACHINE_PERIOD`. |

O Kalman é um **filtro multiplicativo de estado de erro com seis componentes**: três erros de orientação e três desvios do giroscópio. A orientação nominal usa quaternion. A cada atualização:

1. Converte o giro para radianos/s, estima a aceleração angular e desconta do acelerômetro a aceleração causada pelo braço `KALMAN_LEVER`.
2. Propaga o quaternion com o giro corrigido. Usa ajuste de fase e correção de *coning* para a mudança do eixo de rotação entre amostras.
3. Compara a direção medida pelo acelerômetro com a gravidade prevista. Reduz a confiança nessa medida quando seu módulo se afasta da gravidade.
4. Ao detectar repouso, aplica **ZARU**: a taxa verdadeira deve ser zero, então a leitura ajuda a corrigir o desvio do giroscópio. Os limiares são `|norma(aceleração) − g| < 0,20 m/s²` e norma do giro inferior a `1°/s`.
5. Atualiza a incerteza com a forma de Joseph e converte o quaternion para pitch, roll e yaw, preservando a continuidade dos ângulos.

O acelerômetro não determina a proa absoluta. O início usa `KALMAN_HEADING`, ou o yaw do Kernel quando esse parâmetro é `NAN`. A primeira amostra preserva os ângulos do Kernel enquanto o histórico é iniciado.

No modelo Machine, os ângulos do Kernel também são usados enquanto a janela ainda não está completa e para saídas não previstas pelo modelo. A implementação embarcada é uma regressão com coeficientes; não é um executor genérico de todos os modelos disponíveis no seletor Python.

**5 · Heave — aceleração vertical para deslocamento**

O acelerômetro mede força específica nos eixos do corpo. `vertical()` usa pitch e roll para encontrar sua componente vertical; a soma com `HEAVE_GRAVITY` retira a contribuição da gravidade, na convenção adotada.

A classe `Heave` passa essa aceleração por **duas seções de segunda ordem em cascata**: uma produz velocidade, a outra deslocamento. As seções integram na faixa de interesse e rejeitam componentes constantes e muito lentas, reduzindo a deriva que cresceria ao integrar um pequeno desvio.

`HEAVE_PERIOD` define `ωc = 2π/(10·Th)` e `HEAVE_DAMPING` define o amortecimento. O cálculo usa estados em `double`. Na primeira amostra, ou após um intervalo maior que **0,5 s**, as seções reiniciam em regime para a entrada recebida.

O resultado é **heave no sensor, em metros, positivo para baixo**. Representa movimento oscilatório na faixa filtrada, não altitude absoluta.

**6 · Lever — movimento no ponto de interesse**

`LEVER_POINT = [x, y, z]` representa o vetor **do MRU até o ponto desejado**, em metros, nos eixos do navio. Pode ser, por exemplo, o centro do helideque.

`Lever::update()` projeta esse vetor na vertical usando a inclinação atual. Passa o deslocamento pelas mesmas duas seções, agora usando suas saídas passa-alta, e soma ao heave do sensor. Assim, a contribuição geométrica tem a mesma filtragem do heave.

A velocidade `heave_rate` é a diferença entre o heave atual e o anterior, dividida pelo intervalo de tempo. Vale zero no primeiro passo e após lacunas maiores que 0,5 s. **Heave e velocidade são positivos para baixo.** Com vetor nulo, o ponto coincide com o sensor.

`KALMAN_LEVER` e `LEVER_POINT` têm funções distintas: o primeiro vai do **centro de rotação ao sensor** e corrige acelerações; o segundo vai do **sensor ao ponto de saída** e transporta o heave.

**7 · Telemetria — origem, formato e frequência**

Há três seleções independentes:

| Configuração | Valores | O que controla |
|---|---|---|
| `device_mode` | `0` NORMAL · `1` ACQUISITION | O modo de operação geral. Aquisição força SCALE, LIST e início automático; RS232/RS422 usam 460800 baud. |
| `streamer_mode` | `0` CALIBRATED · `1` RAW · `2` SCALE | A origem dos valores transmitidos. |
| `protocol` | `0` JSON · `1` LIST · `2` NMEA | A representação textual de cada mensagem. |
| `kernel_mode` | `0` HR · `1` QT · `2` OR | O pacote binário solicitado ao Kernel. |

**RAW** lê diretamente os inteiros do Kernel. **SCALE** transmite esses campos convertidos para unidades físicas. **CALIBRATED** transmite a saída da cadeia de processamento, desde que o Kernel esteja em HR ou OR.

O processamento segue as amostras recebidas. No modo normal, `frequency` controla a cadência de transmissão, com temporização em milissegundos; não muda a configuração de 200 Hz do Kernel. O Streamer só envia quando o contador de processamento mudou. Em aquisição, elimina o intervalo adicional e tenta transmitir cada novo estado processado.

**Campos transmitidos**

| Situação | Ordem dos campos em JSON/LIST |
|---|---|
| HR/OR calibrado · **13 campos** | `time, tmp, pitch, roll, yaw, ax, ay, az, wx, wy, wz, heave, heave_rate` |
| HR/OR RAW ou SCALE · **12 campos** | `time, tmp, pitch, roll, yaw, ax, ay, az, wx, wy, wz, heave` |
| QT · **10 campos** | `time, tmp, pitch, roll, yaw, q0, q1, q2, q3, heave` |

JSON usa nomes; LIST usa uma lista entre colchetes na mesma ordem. RAW imprime os campos do sensor como inteiros; os demais modos usam três casas decimais. `time` é sempre apresentado em segundos com três casas e se refere à recepção do pacote no ESP32, relativa ao início do stream. RAW/SCALE mantêm heave em zero.

O formato chamado NMEA no código contém **quatro campos**:

```text
$GPPASHR,pitch,roll,yaw,heave*checksum
```

O checksum é o XOR dos caracteres entre `$` e `*`, e a linha termina em CRLF. Use esse layout ao integrar o equipamento: o nome da sentença, sozinho, não descreve seus campos.

**Portas, comandos e configurações**

| Ligação | Interface | Pinos do ESP32 | Velocidade |
|---|---|---|---|
| Console/telemetria USB | `Serial` por USB CDC | USB nativo | Inicializado com 115200. |
| Kernel-120 | UART1 | TX 4 · RX 3 | Alvo de 460800. |
| RS232 | UART0 | TX 11 · RX 10 | `baudrate`, padrão 9600; aquisição: 460800. |
| RS422 | UART2 | TX 12 · RX 13 | Igual ao RS232. |
| LEDs | GPIO | 1 e 2 | Estado do sensor e da comunicação. |

`serial/index.h` seleciona a porta que recebe o comando; respostas e stream passam a usar essa porta. A porta inicial é RS232. O código exige **USB CDC On Boot habilitado** para a UART0 ficar disponível ao RS232.

| Comando | Efeito |
|---|---|
| `$stream_start!` / `$stream_stop!` | Inicia ou interrompe a transmissão. |
| `$settings!` | Mostra as configurações persistidas. |
| `ID:chave$` | Consulta um valor salvo; resposta no formato `$valor!`. |
| `CF:chave$valor!` | Salva uma configuração e reinicia o ESP32. |
| `$calibrate!` | Informa o processamento ativo; não executa uma nova calibração. |
| `$check_sensor!` | Informa `OK` ou `NOT WORKING`, conforme o estado do driver. |
| `$firmware!` | Informa a versão. |
| `$align:N!` | Grava no Kernel o preset de montagem `N` e reinicia os estados do processamento. |
| `MICRS` | Reinicia o ESP32. |
| `$ERASE!` | Restaura configurações padrão e reinicia. |
| `updt` | Entra no recebimento de uma atualização de firmware. |

`device/settings/index.h` guarda as opções via `utils/json/index.h`, em `Preferences`, como um JSON persistido na flash do ESP32. Os padrões efetivos são modo normal, Kernel HR, saída calibrada, protocolo JSON, `autostream` desligado, frequência de 100 Hz e baud de 9600. Frequência e baud usam valores de fallback quando ainda não estão salvos.

Para gravar um ensaio, envie `CF:device_mode$1!`. Para voltar ao uso calibrado, envie os comandos abaixo **um por vez, aguardando o reinício**:

```text
CF:device_mode$0!
CF:streamer_mode$0!
CF:protocol$1!
CF:frequency$10!
CF:baudrate$115200!
CF:autostream$1!
```

O exemplo escolhe LIST a 10 Hz. Os comandos `CF:` alteram a operação; os coeficientes de calibração continuam vindo dos `config.h`.

**Montagem e presets de align**

| Preset `N` | Proa · pitch · roll gravados no Kernel |
|---|---|
| `0` ou `3` | `0° · 0° · 0°` |
| `1` | `0° · −90° · 0°` |
| `2` | `0° · +90° · 0°` |
| `4` | `180° · 0° · 180°` |

Escolha o preset correspondente à montagem física, desligue e ligue o MRU e confira a linha `Kernel Align` no boot. O [guia de instalação](../../../README.md) descreve as posições e os sentidos dos eixos. A referência do ensaio deve estar registrada em `Calibration/Dataset/testN/info.json` antes de exportar Correction.

**Parâmetros que vêm da calibração**

| Notebook em `Calibration/` | Arquivo gerado em `objects/processing/` | O que o firmware recebe |
|---|---|---|
| `1 - Filters/1 - Model.ipynb` | `filters/config.h` | Tipo e frequência do filtro por eixo. |
| `2 - Correction/1 - Model.ipynb` | `correction/config.h` e `align/config.h` | Matrizes, vieses, coeficientes térmicos e montagem do ensaio. |
| Estratégia de `3 - Attitude/` | `attitude/config.h` e configuração do modelo | Modelo ativo e seus parâmetros. |
| `4 - Heave/1 - Model.ipynb` | `heave/config.h` | Período, amortecimento e gravidade local. |
| `5 - Lever/1 - Model.ipynb` | `lever/config.h` | Vetor até o ponto de interesse. |

Uma nova exportação substitui esses arquivos. **Recompile e grave o firmware para usar os novos parâmetros.** Na instalação, confira principalmente `HEAVE_PERIOD`, `KALMAN_LEVER` e `LEVER_POINT`: os valores ajustados na mesa descrevem aquele ensaio e sua geometria.

**Compilação e gravação**

Abra `Main.ino` no ambiente Arduino com suporte a ESP32-S3 e **ArduinoJson 7**. Use a placa **ESP32-S3 Dev Module**, **USB CDC On Boot = Enabled** e uma tabela de partições com suporte a atualização OTA se for usar o atualizador serial.

Com `arduino-cli` já configurado, execute a partir da raiz do repositório MRU, ajustando a porta do equipamento:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32s3:CDCOnBoot=cdc --export-binaries Hardware/Embedded/Main
arduino-cli upload --fqbn esp32:esp32:esp32s3:CDCOnBoot=cdc -p /dev/ttyACM0 Hardware/Embedded/Main
```

No boot, confira modo do dispositivo, baud e modo do Kernel, align, modelo de processamento e modo do Streamer. O [README geral](../../../README.md) reúne a configuração de placa e o procedimento operacional do projeto.

**Componentes, utilitários e atualização**

| Arquivo/pasta | Papel |
|---|---|
| `components/leds/index.h` | Controla os tempos ligado/desligado dos LEDs. LED 1 alterna a cada 0,5 s com Kernel funcionando; LED 2 alterna a cada 0,2 s com stream ativo. |
| `components/encoder/` | Conta pulsos por interrupção e converte para ângulo. Está desabilitado no `Main.ino`; seus pinos 10/11 são usados pelo RS232. |
| `utils/time/` e `utils/listener/` | Fornecem relógios e verificações periódicas sem usar um atraso fixo em cada iteração. |
| `utils/text/` | Buffers de texto usados na leitura e interpretação dos comandos. |
| `utils/json/` | Serialização com ArduinoJson e persistência com Preferences. |
| `utils/array/` | Vetor circular, estatísticas e persistência auxiliares. Não executa a filtragem principal. |
| `utils/notes/` | Utilitário de arquivos em LittleFS, sem integração na cadeia ativa de `Device`. |
| `objects/updater/index.h` | Recebe o binário codificado em base64 pela porta ativa e o grava com a biblioteca `Update`. |

O atualizador começa com `updt`, responde `__STARTING_UPDATE__` e espera blocos no formato `$base64!`. Cada escrita produz `__WRITTEN__`; dez segundos sem dados encerram a recepção, e uma finalização bem-sucedida reinicia o ESP32. É uma transferência serial, sem etapa de download pela rede.

**Comportamentos importantes para interpretar os resultados**

- **As tarefas compartilham o estado mais recente.** A implementação não possui uma fila de amostras entre recepção, processamento e transmissão. Se várias amostras chegarem antes do consumo, estados intermediários podem não ser processados ou enviados; aquisição não constitui garantia de gravação sem perdas.
- **As lacunas recebem tratamentos diferentes.** O Kalman limita o passo de propagação e aumenta a incerteza de inclinação quando o intervalo supera três períodos nominais; Heave e Lever reiniciam suas seções acima de 0,5 s.
- **O estado `working` não é um teste de atualização contínua.** O driver o altera ao decodificar pacotes, mas o silêncio da UART não o limpa por tempo de inatividade. `$check_sensor!` e LED 1 devem ser interpretados junto com a chegada de novas amostras.
- **O código atual não inclui a etapa de relatório NORMAM do diagrama antigo.** A cadeia entrega medições e movimento no ponto de interesse; a avaliação e o certificado descritos no pipeline ficam no computador.
