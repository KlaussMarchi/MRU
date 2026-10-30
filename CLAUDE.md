# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

MRU (Motion Reference Unit): um ESP32-S3 lê o IMU **Kernel-120** (Inertial Labs), processa e transmite atitude,
aceleração, giro, heave e `heave_rate` por USB, RS232 ou RS422. O computador grava ensaios contra uma mesa de
referência, calcula a calibração (notebooks de `Calibration/` ou o pipeline do app MRU Monitor) e os parâmetros vão
ao firmware compilados nos `config.h` ou gravados na flash pela serial (`CL:`).
O procedimento operacional completo (comandos seriais, bauds, montagem) está no `README.md` da raiz; os detalhes
internos, em `Hardware/Embedded/Main/README.md` e `Calibration/README.md`. Documentação, comentários e commits em
português; código em inglês.

## Comandos

Não há linter. Verificar = compilar o firmware, rodar os testes do app, executar o notebook ou o módulo do pipeline
afetado e, quando um algoritmo muda dos dois lados, comparar C++ e Python no host (ver "Espelhamento").

```bash
# Firmware principal. Sem CDCOnBoot=cdc o #error de telemetry/serial/index.h dispara (RS232 ocupa a UART0).
# Para só verificar, use --build-path fora do repo para não tocar no build/ versionado.
arduino-cli compile --fqbn esp32:esp32:esp32s3:CDCOnBoot=cdc,USBMode=hwcdc --build-path /tmp/mru-build Hardware/Embedded/Main

# Build de release (o Updater lê Main.ino.bin deste caminho) e gravação
arduino-cli compile --fqbn esp32:esp32:esp32s3:CDCOnBoot=cdc,USBMode=hwcdc --output-dir Hardware/Embedded/Main/build/esp32.esp32.esp32s3 Hardware/Embedded/Main
arduino-cli upload  --fqbn esp32:esp32:esp32s3:CDCOnBoot=cdc,USBMode=hwcdc --port /dev/ttyACM0 --input-dir Hardware/Embedded/Main/build/esp32.esp32.esp32s3 Hardware/Embedded/Main

# Mesa (ESP32 clássico); Encoder/Listener usam arduino:avr:uno
arduino-cli compile --fqbn esp32:esp32:esp32 Hardware/Table

# MRU Monitor (app Tauri): ver Monitor/README.md
(cd Monitor && npm install && npm run tauri dev)
(cd Monitor/src-tauri && cargo test --lib) && (cd Monitor && npx vite build)    # testes do backend e build do frontend

# Pipeline do app sem a interface: job.json com session, output, strategy, gravity, id e point; eventos JSON no stdout, log no stderr
(cd Monitor/Pipeline && python -u index.py /caminho/job.json)

# Updater: precisa rodar de dentro da pasta para achar o .bin
(cd Updater && python index.py)

# Um notebook: sempre com o diretório de trabalho na pasta dele (todos os caminhos são relativos)
(cd "Calibration/2 - Correction" && jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=-1 "1 - Model.ipynb")

# Datasheet: Documents/Datasheet/index.html é a fonte; gera ../datsheet.pdf e ../pipeline.png
(cd Documents/Datasheet && sh cmd)
```

Core esp32 **3.3.12**, ArduinoJson **7.4.3**, FastAccelStepper 1.4.0 (mesa). Nesta estação os notebooks rodam no
Jupyter do conda (`~/miniconda3/bin/jupyter`, kernel `base`); o Jupyter do sistema está quebrado.

**Tempo de execução:** num ensaio de ~5 min a 200 Hz o pipeline inteiro leva ~4 min com KalmanFusion (`1 - Filters`
~7 s com o espectro de Welch fora da busca e orçamento de busca de 1 dimensão; `KalmanFusion` ~4 min com o laço do
filtro compilado pelo `numba`) e ~20 s com LinearFit. Os notebooks e o app precisam do `numba` (está no
`requirements.txt`; no conda: `pip install numba`). No `test1` (10 Hz, 1800 amostras) o pipeline do app inteiro leva
~15 s.

## Arquitetura

O projeto é uma cadeia de três partes que trocam arquivos:

```text
MRU Monitor (Aquisição) ──► Monitor/Data/Sessions/<data_hora>/data.csv
  ├─► Monitor/Pipeline (Calibração) ──────────► Monitor/Data/Calibrations/<data>_<id>/ (calibration.json, firmware/*/config.h, certificate.pdf)
  │                                 └─► tela Produção: CL: pela serial, sem recompilar
  └─► Calibration/Dataset/testN/files/data.csv ──► notebooks numerados ──► Dataset/testN/results/*.csv + *.json
                                                                       └─► objects/processing/<etapa>/config.h ──► recompilar Main
```

### Espelhamento Calibration ↔ firmware

Cada etapa numerada de `Calibration/` tem uma pasta em `objects/processing/`, e o csv de cada etapa é o que o MRU
entregaria naquele ponto da cadeia:

| Notebook | Firmware | Saída no `results/` |
|---|---|---|
| `Dataset/Format.ipynb` | `scale()` em `processing/index.h` | `dataset.csv` |
| `1 - Filters` | `filters/` (Butterworth 2ª ordem, passa-baixa 4 polos, exponencial; tipo e corte por eixo) | `filtered.csv` (+ `_raw`), `filters.json` |
| `2 - Correction` | `correction/` (`x = M x + c + k (T − T0)`) e `align/` | `corrected.csv`, `correction.json` |
| `3 - Attitude/{KalmanFusion,LinearFit,MachineLearning}` | `attitude/{kalman,linear,machine}/`, escolhido por `using AttitudeModel = ...` em `attitude/config.h` | `attitude.csv`, `attitude.json` |
| `4 - Heave` | `heave/` (duas seções de 2ª ordem em cascata, `double`) | `heave.csv`, `heave.json` |
| `5 - Lever` | `lever/` (`LEVER_POINT`) | `lever.csv`, `lever.json` |

- Nas pastas de `processing/`, `index.h` é o algoritmo e `config.h` é **gerado** pela célula de exportação do
  notebook (cabeçalho `GERADO POR ...`). Editar à mão é perdido na próxima exportação: mude o notebook.
- As estratégias de atitude são alternativas: **a última exportada** é dona de `attitude.csv` e de
  `attitude/config.h`. Mudou uma etapa, refaça as seguintes.
- Etapa nova lê o csv da anterior em `results/` e grava um par csv+json. Só o `Format` lê `files/data.csv`.
- `Calibration/info.json` escolhe o ensaio (`test`) e a gravidade local (`gravity` 9,785). `*.csv` é ignorado pelo
  Git: os json de `results/` são versionados, os csv não. `test1`/`test2` são ensaios de pêndulo antigos com `axes`
  remapeando eixos; dados novos do Monitor não usam `axes`. O pêndulo balança só em roll: métricas de pitch/yaw
  ruins nele são do ensaio, não do modelo.
- `Analysis.ipynb` junta corrected + attitude + lever e grava `Certificate/results/<variável>/metrics.json`;
  `Certificate/1 - Certificate.ipynb` monta o PDF.
- Paridade no host: compilar os `index.h` de `processing/` com `g++ -std=c++17 -I processing` e um shim de
  `Arduino.h` (String, PI, radians, constrain), alimentar o csv do ensaio na taxa dele e comparar com o notebook
  (filtros/correção/heave batem a ~1e-5 relativo).
- Otimização nos notebooks: `NatureSelector('genetic', {**problem, **SEARCH}, n_gaussian=RUNS)` visível na
  célula, com `objective(params)` devolvendo um escalar. `'genetic'` é **CMA-ES**. Cada estudo tem a sua cópia da
  pasta `Nature/` (Filters e KalmanFusion): mudar uma não muda a outra.

### Espelhamento Calibration ↔ Monitor/Pipeline

- `Monitor/Pipeline/<Etapa>/index.py` é a cópia dos notebooks, etapa por etapa (mapa em `Monitor/README.md`),
  com a mesma API (`update()`, `apply()`, `getParams()`, `info()`); `Firmware/index.py` escreve os `config.h` no
  formato das células de exportação e lê de volta as chaves do `CL:`. Mudou um lado, mude o outro.
- Paridade conferida em 29/10/2026 no `test1` com as três estratégias e numa sessão de 200 Hz gravada pelo app com o
  MRU e a mesa simulados (LinearFit): csv iguais até ~1e-14, os 7 `config.h` idênticos fora a linha `GERADO`,
  métricas da análise e texto do certificado iguais. Em 30/10/2026, numa sessão simulada de 335 s a 200 Hz, também
  KalmanFusion e MachineLearning: csv até ~1e-12 (`heave_ref` do Lever ~1e-9), `config.h` idênticos fora o `GERADO`
  e métricas até ~1e-10. Para repetir: copiar
  `Calibration/` (sem o `test3`) e `objects/processing/` para fora do repo, `info.json` com `test: 1`, apagar os
  `Backup/model_*` do MachineLearning da cópia (o `3 - Compare` escolheria um modelo antigo), rodar os notebooks e o
  pipeline com o mesmo `data.csv` + `info.json` do ensaio e comparar `results/` e os `config.h`.
- Diferenças conscientes: o MachineLearning do app treina e usa um modelo por execução; o `5 - Lever` lê o pivô do
  `heave.json` com 10 dígitos (`to_json`), o que dá ~1e-11 a 1e-7 no `heave_ref`; número de série e do certificado vêm
  do pedido do app, não do `info.json`; só o app tem as guardas da referência em debug (ensaio sem trecho parado ou sem
  balanço), que não mudam nada num ensaio com a mesa. O `getRates` do Format (notebook e app) dá taxa zero a uma
  amostra isolada entre dois pacotes perdidos, onde o CubicSpline quebrava.

### Eixos e unidades

- **SCALE** mantém os eixos do Kernel: X boreste, Y proa, Z para cima. **CALIBRATED** entrega os eixos do navio:
  x proa, y boreste, z para baixo. Heave e `heave_rate` positivos para baixo. `vertical()` recebe `(ay, ax, −az)`
  do Kernel no SCALE.
- Pacote HR do Kernel: aceleração em **g**·1e6 (não m/s²), giro °/s·1e5, ângulos graus·1e3; o firmware escala com
  g = 9,8106 (constante do ICD), distinta da gravidade local exportada pela calibração.
- Euler do Kernel (ICD 1.42): heading em Z (horário) → pitch em X → roll em Y, `C = Rz(−K)·Rx(θ)·Ry(φ)`.

### Firmware (`Hardware/Embedded/Main`)

- `Main.ino` só monta `Device`; cada componente é uma pasta com `index.h`, recebe o pai por ponteiro de template
  (`template <typename Parent> class X`, sem globais) e expõe `setup()`/`handle()`.
- `device/tasks`: `thread0` roda sensores → processamento → componentes; `thread1` (FreeRTOS, núcleo 1) roda a
  telemetria. Compartilham só o estado mais recente, sem fila: a aquisição não garante gravação sem perdas.
- `Processing::handle()` só avança quando `kernel.lastAckTime` muda; `dt` vem desses instantes, e os filtros
  usam a taxa nominal `KernelSensor::RATE` (200 Hz a 460800 baud).
- UARTs: **UART0 = RS232** (pinos 10/11, só livre com USB CDC On Boot), **UART1 = Kernel** (3/4), **UART2 =
  RS422** (13/12). Nunca ponha RS232/RS422 na UART1. O encoder está desabilitado porque usa os pinos do RS232.
- No boot o `KernelSensor` procura o baud do Kernel e grava por SaveFlash só o parâmetro que difere; align e
  parâmetros do Kernel só valem depois de desligar e ligar o MRU (reiniciar o ESP não basta).
- Modos (`globals/constants.h`): `device_mode` NORMAL/ACQUISITION, `streamer_mode` CALIBRATED 0 / RAW 1 / SCALE 2,
  `kernel_mode` HR/QT/OR, `protocol` JSON/LIST/NMEA. Configurações persistem em `Preferences` via
  `CF:chave$valor!`, que reinicia o ESP32.
- v1.0.8: `CS:chave$valor!` salva sem reiniciar (um `MICRS` aplica todas), `$status!` devolve em JSON o estado
  efetivo e `CF:output$N!` escolhe a porta do stream ao ligar (1 USB, 2 RS422, 3 RS232). A calibração também pode
  vir da flash (`objects/processing/calibration/`): `CL:CHAVE@posição$v1,v2,...!` monta uma pendente com as chaves
  dos `config.h`, `$calibration_check!` dá o CRC-32 por chave, `$calibration_save!`/`$calibration_erase!` gravam ou
  apagam e reiniciam. A da flash prevalece sobre a compilada.

### MRU Monitor (`Monitor/`)

App Tauri 2 (React em `src/`, Rust em `src-tauri/src/`); o Monitor antigo em Python foi apagado. `device.rs` lê cada
porta numa thread e, gravando, escreve o diário `*.journal.csv`; `device::open` abre a serial de verdade ou, com o
prefixo `sim:`, a porta fictícia do simulador, pelo mesmo caminho (descoberta, parser, terminal e gravação são os
mesmos). `discover.rs` acha porta e baud (ouve o stream ou pergunta o ACK); `packet.rs` reconhece o aparelho pelo
layout da linha (mesa = 3 campos ou JSON `{"t","pitch","roll"}`; MRU = LIST de 10–13 campos, JSON ou NMEA);
`simulate.rs` é o banco simulado (`Rig`): MRU com o firmware v1.0.8 e um Kernel com o ruído do `test3`, cinemática do
braço, perda de pacote, jitter, banda da UART e baud errado virando lixo, e a mesa do `Table.ino`, ligados em
Ajustes → Simular MRU (portas SIM0/SIM1). O MRU simulado sai transmitindo CALIBRATED/LIST a 100 Hz em 115200 bps e a
plataforma simulada cicla sozinha, seguindo o alvo como o FastAccelStepper (até ~2,5° atrás da senoide, a mesma posição
que o `Table.ino` imprime); `record_start` manda `start` à mesa (real ou simulada), que fica 20 s parada e roda
pitch 100 s, roll 100 s e repouso 100 s em ciclo, e `record_stop` manda `stop`. Toda linha do stream vai ao terminal
(não há eco a ligar). `job.rs` roda os scripts Python, e cada linha JSON do stdout é um evento
`progress`/`result`/`error`.

`Pipeline/Session/index.py` transforma os diários em `target.csv`, `reference.csv`, `data.csv` e `info.json`: recupera
o instante de cada pacote pela contagem de passos em reta (o carimbo tem ±1 ms de jitter e o relógio deriva; sem isso
o Format derivava o jitter da referência) e interpola a mesa por spline suavizada nesses instantes. Sem a mesa, a
**referência em debug** usa os ângulos do próprio MRU filtrados (`reference: debug` na sessão, no `calibration.json` e
no certificado). `Pipeline/` é o pipeline e `Pipeline/Session/` o conversor de gravações; em desenvolvimento os dados vão para `Monitor/Data/` (fora do Git).
O Python é escolhido em Ajustes, onde "Instalar ambiente" baixa o `uv`, um Python 3.12 próprio e o
`Pipeline/requirements.txt` para a pasta local do app.

## Fora do fluxo principal

- `Analysis/`: estudos independentes; `Analysis/Calibration_OLD/` é legado (tem `GEMINI.md` próprios) e não
  alimenta nada do pipeline atual.
- `Documents/`: ICD e GUI do Kernel, normas, datasheet. `README.html` ao lado de cada `README.md` é uma cópia
  renderizada; o gerador não está no repositório.
