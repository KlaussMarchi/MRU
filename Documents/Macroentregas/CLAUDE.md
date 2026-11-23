# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Relatórios de macroentrega do projeto do DRMM (Dispositivo de Referência de Monitoramento dos Movimentos, o "Measure
MRU" deste repositório), escritos em LaTeX e em português para o Polo de Inovação Campos dos Goytacazes (IFF). O
trabalho atual é a **Macroentrega I do Ciclo II**. Este arquivo explica como os relatórios são feitos e onde está, no
repositório `~/Projects/MRU`, cada informação de hardware, software e documentação que eles usam. Todo o repositório
pode ser lido daqui. Salvo indicação, os caminhos fora de `Macroentregas/` são relativos à raiz `~/Projects/MRU`.
O `CLAUDE.md` da raiz descreve o firmware, a calibração e o app em detalhe; não repito aqui o que está lá.

**`Documents/Macroentregas` está no `.gitignore` da raiz:** não há histórico nem como desfazer pelo Git. Antes de
reescrever um trecho grande, guarde uma cópia do `main.tex`.

## O relatório em andamento: Ciclo II, Macroentrega I

`Ciclo2/MRU Ciclo II - Macroentrega I/`, projeto PIFF-2609.0073, de 04/09/2026 a 03/12/2026. A fase prepara o DRMM
para atmosferas explosivas (Ex db para Zona 1, Ex ec para Zona 2) e para o lote piloto. Os itens do Plano de Trabalho
estão na tabela de `A - TABELA.tex`. Cada um é uma `\subsection` de "Entregas do Projeto", na mesma ordem:

| Item | Produto e critério | Onde está no repositório | O que **não** está no repositório |
|---|---|---|---|
| 2.1 *Gap analysis* frente à IEC 60079 e à Portaria 115:2022 | Planilha de requisitos com conformidade e não conformidade | Estado atual do protótipo: Final do Ciclo I (hardware, PCB, invólucro, temperatura), Macroentrega II do Ciclo I (componentes, consumo, circuitos), README da raiz (portas, pinos, alimentação das UARTs), firmware | Textos das normas ABNT NBR IEC 60079-0/-1/-7 e 60529 e da Portaria 115, BOM v2, manual técnico do DRMM (`manualdrmm` no `.bib`), planilhas de avaliação da equipe |
| 2.2 CAD 3D do invólucro Ex d | Arquivos .STEP/.IGES e desenhos em PDF | Só o "antes": figuras do invólucro de alumínio do Ciclo I (`Ciclo1/Macroentrega Final - MRU/imagens/V/embalagem_metal_*.png`, `metal*.png`, `desenho_tecnico.png`; seção "Desenhos Técnicos das Embalagens" da Macroentrega V) | Os modelos CAD dos três protótipos e os desenhos |
| 2.3 Simulação de estresse mecânico e térmico | Relatório com as premissas de cálculo | Faixa de temperatura do Kernel no datasheet (`Documents/KernelSensor/Documentation/kernel_datasheet.pdf`); compensação de temperatura `k (T − T0)` da correção (`Calibration/2 - Correction`, `Monitor/Pipeline/Correction/index.py`); ensaio de 12 h na Final do Ciclo I ("Validação de Temperatura") | Arquivos de simulação e o registro bruto do ensaio térmico |
| 2.4 Esquemáticos e PCB com isolamento galvânico | Documentação do circuito e relatório do isolamento | O "antes": Macroentregas II, III e V e a Final do Ciclo I (gerações de PCB); figuras `images/ciclo1_*` já copiadas; pinos das UARTs (RS-422 na UART2, pinos 13/12) no README da raiz e em `Hardware/Embedded/Main/objects/telemetry/serial/index.h` | Projetos Altium, esquemáticos e *layout* revisados |

Atividades complementares do relatório e onde estão as fontes:

- **NORMAM-27 × NORMAM-223:** `Documents/Compare/Norma/NORMAM-27_DPC - Rev2-Mod4_0_0.pdf` e `normam-223.pdf`. Os
  limites da NORMAM-223 (Tabela 1) estão implementados em `Monitor/src/pages/HMS/limits.js` e usados em `index.jsx`
  (janela de 20 min, inclinação, SHR/SVArf, VArf, Arf).
- **MRU 5 × KERNEL-120:** `Documents/Compare/Kongsberg/388116e_datasheet_mru5_sept25.pdf` (rev. E) e
  `Documents/KernelSensor/Documentation/kernel_datasheet.pdf`. Os outros concorrentes estão em `Documents/Compare/`.
- **Cadeia de processamento e calibração:** seção "Pipeline técnico de calibração" do `README.md` da raiz,
  `Calibration/README.md`, `Documents/Datasheet/index.html` e as figuras `Documents/pipeline.png` e
  `images/pipeline_esquematico.jpg`.
- **Montagem, comunicação e comandos:** seções "Montagem e alinhamento", "Modos do Main", "Portas, pinos e baud rate"
  e "Comandos e configurações" do `README.md` da raiz, mais o datasheet e `Documents/positions.png`.

O que ainda falta no `main.tex` está marcado; liste com
`grep -nE '\\(pendente|reservado|lacuna)\b' main.tex`. Em 17/11/2026: figuras dos três CAD, tabela de arquivos do CAD,
fixação do rosqueado, texto, esquemático e *layout* das placas revisadas, e `\urldatasheet`, que aponta para o site e
não para o arquivo.

### Cuidados com o conteúdo

- Tudo o que o relatório afirma do equipamento precisa ter fonte no repositório ou vir da equipe. O que não está aqui
  (lista da tabela acima) vai como `\pendente{...}` ou `\reservado{...}{...}`, e pergunte ao usuário. Nunca invente
  medida, componente, valor de norma ou nome de arquivo.
- As sessões e calibrações de `Monitor/Data` são todas do **simulador** (`"id": "SIMULADOR01"` no `info.json`). Não
  servem de resultado de ensaio. Ensaios reais com o Kernel: `Calibration/Dataset/test1` e `test2` (pêndulo, ciclo I)
  e `test3` (parado, 200 Hz).
- O ensaio térmico do Ciclo II (`images/temperatura_kernel.jpg`, cerca de 12 h, estabiliza em torno de 64 °C) dá o
  mesmo número e a mesma duração da "Validação de Temperatura" da Final do Ciclo I (`imagens/V/temperatura.png`).
  Confirme com o usuário se é um ensaio novo antes de escrever como tal.
- A tabela de comandos do relatório segue o datasheet (o conjunto voltado ao cliente). O firmware tem mais comandos,
  como `$status!`, `CS:`, `CL:` e `$calibration_*` (tabela completa no `README.md` da raiz).
- Firmware atual: **v1.0.9** (`MRU_FIRMWARE=` em `Hardware/Embedded/Main/Main.ino`). O README do firmware ainda diz
  v1.0.8. A atitude exportada é o Kalman (`using AttitudeModel = KalmanModel` em
  `objects/processing/attitude/config.h`, gerado em 15/10/2026).

## Mapa do repositório `~/Projects/MRU`

```text
MRU/
├── CLAUDE.md, README.md        README (801 linhas): estrutura, instalação, modos, portas e baud, comandos, montagem,
│                               calibração passo a passo, formatos de saída, atualização, diagnóstico e o pipeline
│                               técnico etapa por etapa. É a fonte mais completa para o texto técnico.
├── Documents/
│   ├── Macroentregas/          ESTA PASTA (fora do Git)
│   ├── Datasheet/              index.html = datasheet "Measure MRU" (fonte); `sh cmd` gera ../datsheet.pdf e
│   │                           ../pipeline.png com o Chrome headless; assets/ tem logos (IFF, Embrapii, LAMCE) e a foto
│   ├── datsheet.pdf            datasheet gerado (7 p.)
│   ├── pipeline.png            figura da cadeia de processamento (saída do datasheet)
│   ├── positions.png           posições de montagem
│   ├── Protocol/nmea.pdf       NMEA 0183 (7 p.)
│   ├── KernelSensor/           material do Kernel-120: Documentation/ (ICD rev. 1.42, 61 p.; datasheet; manual da
│   │                           IMU GUI rev. 2.35, 58 p.), ATC/ (certificados de teste de aceitação de duas unidades,
│   │                           K2490552 e K2490568), GUI/ (IMU GUI Windows e Linux), Driver/
│   ├── Inertial Labs/          cópia da mídia do fabricante: o mesmo conteúdo do KernelSensor, com os zip da GUI
│   └── Compare/                pesquisa de mercado e normas:
│       ├── Norma/              NORMAM-27 Rev2 Mod4 (169 p.), NORMAM-223 (213 p.) e Normas_e_Requisitos_MRU.pdf, que
│       │                       na verdade é o "Standard Measuring Equipment for HMS" da HCA/UK CAA, Rev 9c 2023 (39 p.)
│       ├── Kongsberg/          MRU 5 (datasheet rev. E set/2025 e dois manuais: 130-0002035a, 226 p., e o de
│       │                       instalação "mru and h install manual", 148 p.), MRU E, recalibração
│       ├── Kernel/             datasheets Kernel 110/120 (rev. 1.13 e atual) e 210/220, ICD 1.42
│       ├── InertialLabs/       MRU e IMU-P da Inertial Labs
│       ├── AdvancedNavigation/ Motus (datasheet e manual de 191 p.)
│       ├── NorwegianSubsea/, CHCNAV/ (CI-710), Gladiator/ (LMRK005)
│       └── Macroentrega_Final___MRU.pdf   PDF compilado da Final do Ciclo I (44 p.)
├── Hardware/                   só firmware: não há projetos de PCB, esquemáticos nem CAD no repositório
│   ├── Embedded/Main/          firmware do MRU (ESP32-S3), v1.0.9. README.md: visão geral e estrutura
│   │   ├── Main.ino, device/   montagem do Device, configurações persistentes, tarefas (thread0/thread1)
│   │   ├── globals/constants.h códigos dos modos (device, streamer, kernel, protocol)
│   │   ├── objects/sensors/Kernel/        leitura do Kernel: pacotes HR, orient e quat
│   │   ├── objects/processing/            uma pasta por etapa (filters, correction, align, attitude/{kalman,
│   │   │                                  linear,machine}, heave, lever) com index.h (algoritmo) e config.h (gerado
│   │   │                                  pela calibração); calibration/ = calibração gravada na flash pelo CL:
│   │   ├── objects/telemetry/  serial (UARTs e portas), protocol (comandos), streamer (JSON/LIST/NMEA)
│   │   ├── objects/health/     diário de eventos na RTC e $diagnostics!
│   │   ├── objects/updater/    atualização pela serial com CRC e rollback
│   │   ├── objects/components/ LEDs e encoder (desabilitado)
│   │   └── build/esp32.esp32.esp32s3/   binários de release (Main.ino.bin etc.)
│   ├── Embedded/Host/          o firmware real no PC com shim do Arduino e Kernel falso (scenarios.py)
│   ├── Table/Table.ino         mesa de referência motorizada (ESP32 clássico, motor de passo, FastAccelStepper, fins de
│   │                           curso); ciclo: 20 s parada, 100 s pitch, 100 s roll, 100 s repouso
│   ├── Encoder/, Listener/     teste isolado do encoder e ponte serial auxiliar a 9600 (Arduino Uno)
├── Calibration/                calibração em notebooks (README.md de 218 linhas)
│   ├── info.json               ensaio escolhido, gravidade local 9,785 e id
│   ├── Dataset/                Format.ipynb; test1 e test2 = pêndulo (ciclo I), test3 = parado a 200 Hz
│   ├── 1 - Filters/ … 5 - Lever/      uma etapa por pasta; results/*.json são versionados, *.csv não
│   ├── Analysis.ipynb          métricas por variável
│   └── Certificate/            1 - Certificate.ipynb monta o certificado; release/certificate.pdf é um exemplo pronto
├── Monitor/                    app MRU Monitor (Tauri: React + Rust + Python); README.md de 221 linhas, com "O que
│   │                           falta" (ensaio com hardware real pendente, Windows não testado, picos de ~70°)
│   ├── src/pages/              Monitor, Acquisition, Calibration, Production, Device, HMS (NORMAM-223), Settings
│   ├── src-tauri/src/          serial, descoberta, pacotes, firmware, simulador (simulate.rs), jobs
│   ├── Pipeline/               cópia dos notebooks em módulos (Format, Filters, Correction, Attitude, Heave, Lever,
│   │                           Analysis, Certificate, Firmware) e Session/ (gravação → sessão)
│   └── Data/                   Sessions/ (3, todas do simulador) e Calibrations/ (4, do simulador; cada uma com
│                               calibration.json, certificate.pdf, figures/, results/ e firmware/*/config.h)
├── Analysis/                   estudos fora do fluxo principal
│   ├── Calibration_OLD/        calibração antiga (pêndulo com encoder, Kongsberg, mesa); Documents/ tem o PDF da
│   │                           Macroentrega V do Ciclo I e calibrações antigas
│   ├── Pendulum/               modelo do pêndulo; docs/ tem o PDF da Macroentrega IV do Ciclo I
│   ├── Optimizer/              otimização de heave e fusão (tem GEMINI.md)
│   ├── Embedded/, Filters/, MathFusion/, Math/, PitchRollYaw/, Sensors/, TestKernel/   estudos de filtros,
│   │                           fusão, Kalman e MPU6050 do ciclo I; MathFusion/README.md compara métodos de fusão
│   ├── Board/                  DataBase.csv de uma placa e análise de amostragem e filtros
│   └── Static/                 análise de ensaio parado
└── Katia/                      APAGADA na árvore de trabalho (mudança não commitada), mas ainda no último commit:
                                `git show HEAD:Katia/Katia.md` é um guia que compara a instalação do MRU 5 (manuais
                                Kongsberg) e a NORMAM-223 com o nosso MRU
```

## Relatórios do Ciclo I (fonte do "antes")

PIFF-2411.0049, de 10/2024 a 07/2026. Já entregues: não altere, só consulte. Para achar um assunto:
`grep -rn 'termo' Ciclo1/*/main.tex`.

| Relatório | Período | Conteúdo |
|---|---|---|
| Macroentrega I | 12/2024 a 03/2025 | Pesquisa de sensores, módulos e atuadores |
| Macroentrega II | 03/2025 a 07/2025 | Modelagem e filtros, componentes e consumo, circuitos, PCB, embalagem |
| Macroentrega III | 07/2025 a 11/2025 | Sensores, prototipação e montagem das PCB, compartimento, placa do primeiro protótipo, firmware, protocolo, software de monitoramento |
| Macroentrega IV | 11/2025 a 03/2026 | Pêndulo, encoder, calibração, testes de bancada, estáticos e dinâmicos |
| Macroentrega V | 03/2026 a 07/2026 | Manuais, desenhos dos circuitos e das embalagens, registros de software, sistema embarcado, HMS, protocolo, testes de campo, calibração, validação de mercado |
| Final | 10/2024 a 07/2026 | Resumo da fase inteira: componentes, filtros e fusão, gerações de PCB, firmware, NMEA, RS-232, HMS, invólucro, calibração no pêndulo e no LAMCE, comparação com MRUs comerciais, temperatura, PI, próximos passos (mesa motorizada) |

A Final guarda as figuras de todas as macroentregas em `imagens/I` … `imagens/V`. Também há PDFs compilados: Final em
`Documents/Compare/`, V em `Analysis/Calibration_OLD/Documents/`, IV em `Analysis/Pendulum/docs/`.

## Como consultar cada tipo de arquivo

- **PDF:** use `pdfinfo arquivo.pdf` para ver o número de páginas e `pdftotext -layout -f 10 -l 15 arquivo.pdf -` para
  extrair o texto de um trecho. Para ver uma página como imagem, `pdftoppm -png -r 110 -f N -l N arquivo.pdf /tmp/p` e
  depois Read no PNG. A Read também lê PDF direto, com `pages`, até 20 páginas por vez. Nos manuais longos, procure
  primeiro com `pdftotext ... - | grep -n`.
- **Imagens:** Read mostra PNG e JPG. Antes de citar uma figura do Ciclo I, olhe a figura.
- **Notebooks:** a Read lê `.ipynb` com as saídas. Para varrer só o código e o markdown, use `python3` com `json`.
- **Código e README:** `grep -rn` na raiz, excluindo `Monitor/node_modules` e `Monitor/src-tauri/target`, que juntos
  pesam ~12 GB.
- **Histórico:** `git -C ~/Projects/MRU log --format='%h %ad %s' --date=short -- caminho` dá as datas, por exemplo de
  quando uma função do firmware mudou. `git show HEAD:caminho` lê o que foi apagado.
- **Python:** não há `python` no PATH. `python3` serve para scripts simples; pandas, numpy e o pipeline usam
  `~/miniconda3/bin/python`.

## Compilar

Cada relatório é um projeto independente; compile de dentro da pasta dele, com a saída fora dela:

```bash
cd "Ciclo2/MRU Ciclo II - Macroentrega I"
latexmk -pdf -shell-escape -interaction=nonstopmode -outdir=/tmp/macro main.tex
```

- pdfLaTeX + BibTeX (o `latexmk` roda o `bibtex` sozinho). `-shell-escape` é obrigatório: o `settings.tex` carrega
  o `minted` (usa o `pygmentize`).
- O `minted` cria `_minted-main/` na pasta do relatório mesmo com `-outdir`; apague se não havia antes.
- Os avisos `Font shape OT1/bch/n/n undefined` são esperados (fonte matemática do `settings.tex`). Conferir o
  resultado: `grep -E '^!|undefined (reference|citation)|Citation' /tmp/macro/main.log`.

## Estrutura de cada relatório

- `main.tex`: preâmbulo extra e **todo o texto**. Os demais arquivos entram por `\input`.
- `settings.tex` (pacotes, margens, fonte), `utils.tex` (macros) e `B - CABEÇALHO.tex` (estilo `modeloTexto`, com
  `imagensCapa/head.png` no topo) são copiados de relatório em relatório e já divergem um pouco: mudar um não muda os
  outros.
- Capa: `A - CAPA.tex` no Ciclo I; no Ciclo II, `A - TABELA.tex`, com a tabela de itens do Plano de Trabalho
  (item, produto, critérios de aceitação) e a equipe.
- Referências: Macroentregas I a III do Ciclo I escrevem à mão em `C - REFERÊNCIAS.tex`; da IV em diante,
  `abntex2cite` (`[alf]`, autor-data ABNT) com `references.bib` e `\bibliography{references}` no fim do `main.tex`.
  Nesses, cite com `\cite{chave}` e acrescente a entrada no `.bib`.
- Figuras em `images/` (Macroentrega V do Ciclo I e Ciclo II) ou `imagens/` (as anteriores). No Ciclo II,
  `Lab Desk with MRU Monitoring Setup.png` e `Pipeline.jpeg` estão na pasta mas não são usadas.

## Convenções do texto (Ciclo II)

- Ordem: Resumo, Introdução, Metodologia, Entregas do Projeto, Atividades Complementares, Considerações Finais,
  referências.
- Figura e tabela com `[H]`, `\caption` e `\label` antes do conteúdo e `\fonte{Autoria Própria}` (ou a origem)
  depois. Em `longtable`, a fonte vai fora: `{\vspace{-0.5\baselineskip}\fonte{...}\par}`. Figura reaproveitada do
  Ciclo I: `\fonte{Autoria Própria (Macroentrega V do ciclo I)}`.
- Tabelas em `tabularx` com bordas `|...|` e `\renewcommand{\arraystretch}{1.3}`; coluna `Y` = `X` centralizada na
  vertical.
- Rótulos `fig:`, `tab:`, `sec:`, citados como `Figura~\ref{}`, `Tabela~\ref{}`, `Seção~\ref{}`.
- Termos em inglês em `\textit{}` (*roll*, *heave*, *firmware*, *layout*); vírgula decimal e `~` entre número e
  unidade (`3,6~W`, `100~Hz`); normas por extenso como "ABNT NBR IEC 60079-1" e "Portaria Inmetro nº 115/2022".
  O equipamento é "DRMM" no texto e "Measure MRU" quando se fala do produto e do datasheet.
- Marcas do que falta, definidas no `main.tex` e no `utils.tex`: `\pendente{texto}` (vermelho),
  `\reservado{altura}{descrição}` (caixa no lugar de uma figura ainda não feita) e `\lacuna[altura]`. Ao completar
  um trecho, remova a marca.
- Planilha de *gap analysis*: células `\avA` (Atende), `\avJ` (com ajuste), `\avN` (não atende), `\avV` (a verificar),
  `\avNA` (não se aplica), `\avF` (falta).
