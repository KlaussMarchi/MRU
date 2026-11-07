# MRU Monitor

Aplicativo desktop (Tauri 2 + React + Rust) que monitora, adquire, calibra e prepara o MRU para produção, com um
painel HMS simulado e um MRU simulado para trabalhar sem hardware. É **autossuficiente**: só escreve dentro de
`Monitor/` (as calibrações e os `config.h` gerados ficam só no pacote de cada calibração), e de fora só lê o `Main.ino.bin`
que oferece para atualizar o MRU, que também vai dentro do instalador.

```text
Monitor/
├── src/                 interface React: telas em src/pages, componentes em src/components, contextos e utils
├── src-tauri/           backend em Rust: serial, descoberta de porta e baud, simulador, gravação, tarefas Python
├── Pipeline/            pipeline de calibração (os algoritmos de Calibration/): Format → Certificado
│   └── Session/         transforma a gravação em target.csv, reference.csv, data.csv e info.json
├── Data/                sessões e calibrações em desenvolvimento (Sessions/, Calibrations/; fora do Git)
└── public/, index.html  favicon e a página que o Vite monta
```

## 1. Instalar as ferramentas (uma vez por máquina)

| Ferramenta | Linux (Ubuntu/Debian) | Windows 10/11 |
|---|---|---|
| Node.js 20+ | `sudo apt install nodejs npm` ou [nodejs.org](https://nodejs.org) | instalador LTS de [nodejs.org](https://nodejs.org) |
| Rust ≥ 1.89 | `curl https://sh.rustup.rs -sSf \| sh` | [rustup-init.exe](https://rustup.rs) (aceite o *Visual Studio C++ Build Tools*) |
| Bibliotecas do Tauri | `sudo apt install libwebkit2gtk-4.1-dev libgtk-3-dev librsvg2-dev libudev-dev build-essential pkg-config libssl-dev` | WebView2 já vem no Windows 11 (no 10, instale o *Evergreen Runtime*) |
| Permissão da serial | `sudo usermod -aG dialout "$USER"` e sair/entrar da sessão | driver do conversor (CH340/FTDI/CP210x) |
| Python 3.10+ (pipeline) | `sudo apt install python3 python3-venv` ou Miniconda | [python.org](https://www.python.org) (marque *Add to PATH*) ou Miniconda |

O `src-tauri/.cargo/config.toml` faz o Cargo escolher versões compatíveis com o Rust instalado
(`incompatible-rust-versions = "fallback"`); não é preciso atualizar o Rust só por causa do Tauri.

## 2. Ambiente Python do pipeline

O app chama `Pipeline/Session/index.py` (salvar sessão) e `Pipeline/index.py` (calibrar) com o Python escolhido em **Ajustes**.
O caminho mais simples é o botão **Ajustes → Instalar ambiente**: o app baixa o [uv](https://docs.astral.sh/uv/),
um Python 3.12 próprio e os módulos de `Pipeline/requirements.txt` para a pasta local dele e passa a usá-lo. Não mexe
no Python da máquina nem no `PATH`, precisa de internet e pode ser repetido para refazer o ambiente.

| Sistema | Pasta do ambiente |
|---|---|
| Linux | `~/.local/share/com.measure.mru/` (`uv/`, `pythons/`, `python/`) |
| Windows | `%LOCALAPPDATA%\com.measure.mru\` (mesmas pastas) |

Também dá para usar um Python já instalado, criando um ambiente dedicado e apontando para ele em **Ajustes**:

```bash
# Linux
cd Monitor
python3 -m venv .venv
.venv/bin/python -m pip install -r Pipeline/requirements.txt

# Windows (PowerShell)
cd Monitor
py -m venv .venv
.venv\Scripts\python -m pip install -r Pipeline\requirements.txt
```

O cartão mostra a versão e os módulos que faltarem. Nesta máquina de desenvolvimento o conda
(`~/miniconda3/bin/python`) já tem tudo.

## 3. Rodar em desenvolvimento

```bash
cd Monitor
npm install
npm run tauri dev
```

O `tauri dev` sobe o Vite na porta 1420 e abre a janela. Mudanças no React recarregam sozinhas; mudanças no Rust
recompilam o backend.

## 4. Gerar o executável

```bash
cd Monitor
npm install
npm run tauri build
```

| Sistema | Saída |
|---|---|
| Linux | `src-tauri/target/release/bundle/deb/*.deb`, `appimage/*.AppImage` e o binário `src-tauri/target/release/mru-monitor` |
| Windows | `src-tauri\target\release\bundle\msi\*.msi` e `nsis\*-setup.exe` |

O instalador oficial de Windows deve sair **no Windows**. Do Linux também dá para gerar um, sem instalar o NSIS no sistema: com o
`x86_64-pc-windows-gnu` e o mingw, extraia os pacotes `nsis` e `nsis-common` e rode `npx tauri build --target x86_64-pc-windows-gnu
--bundles nsis` com o `makensis` no `PATH` e os stubs em `/usr/share/nsis`. A pasta `Pipeline/` vai dentro do instalador como recurso. Instalado, o app grava sessões e calibrações em
`Documentos/MRU Monitor/`; o Python sai do botão **Instalar ambiente** (seção 2).

## 5. Testes

```bash
cd Monitor/src-tauri && cargo test --lib     # parser das linhas, simulador (cinemática e protocolo) e o poll do backend
cd Monitor && npx vite build                 # o frontend compila
```

## 6. MRU simulado

Em **Ajustes → Simulação**, a chave **Simular MRU** liga um MRU e uma plataforma de referência fictícios nas portas
**SIM0** e **SIM1**. Elas aparecem em todas as listas de porta e na busca automática, e o backend as abre pelo mesmo
caminho de uma serial de verdade (`device::open`): parser, terminal, estatísticas, gravação e descoberta são os mesmos.

- **Como o MRU que temos:** sai de fábrica já transmitindo em modo normal, CALIBRATED, LIST, 100 Hz e 115200 bps; a
  porta se comporta como o conversor RS232 (aberta no baud errado só entrega lixo e não entende comandos). `CS:` só grava, o
  reinício aplica; o modo aquisição sobe a UART para 460800. Emula o firmware v1.0.9 inteiro: ACK, `$status!`, `$diagnostics!`, `$log!`, eventos, atualização com rollback,
  `$settings!`, `CF:`/`CS:`/`ID:`, `MICRS`, align, `CL:` com CRC, `$calibration_save!/erase!`, porta do stream ao ligar.
- **Kernel realista:** ruído por eixo do ensaio real (`test3`, parado a 200 Hz: aceleração 0,0072/0,0084/0,0062 m/s²,
  giro 0,068/0,044/0,037 °/s, pitch/roll/yaw 0,0058/0,0035/0,0038°), carimbo em ms que sai 1 ms atrasado em 10,8% dos
  pacotes (81% dos passos de 5 ms e 9,6% de 4 e de 6 ms, como no real), viés, fator de escala, deriva térmica (34,5 a 36,8 °C), desalinhamento da caixa, align que gira os eixos,
  AHRS com atraso, pacotes perdidos na taxa do ensaio (4e-4) e a banda da UART (JSON a 100 Hz não
  cabe em 9600 bps). A força específica sai da segunda derivada da posição do sensor no braço, então o heave e o pivô
  da calibração existem de verdade; o heave sai pelo mesmo filtro do firmware.
- **Movimento:** *sobre a plataforma* repete o ciclo do `Table.ino` sem parar (100 s de pitch, 100 s de roll, 100 s de
  repouso a 15° e 0,3 Hz, envelope em cosseno de 2 s, 40 passos/grau, `{"t","pitch","roll"}` com duas casas a 100 Hz),
  para o Monitor e a Aquisição nunca ficarem parados. A mesa simulada segue o alvo como o motor de passo: o
  FastAccelStepper só acelera enquanto a distância até o alvo passa a de frenagem, então fica até v²/2a ≈ 2,5° atrás
  da senoide nos cruzamentos e reverte perto do limite de 150°/s² nos picos (média de 20 ms pela inércia da mesa).
  Conferido contra o próprio `Table.ino` compilado no PC: 98% das linhas iguais e o resto a um passo (0,025°); *navio em ondas* e *parado* completam. Ao gravar para calibração
  o app manda `start` à plataforma (ou, sem ela, ao MRU simulado): o movimento vai a zero numa rampa de 2 s, fica 20 s
  parado e recomeça o ciclo no mesmo instante da gravação; o `stop` do fim da gravação devolve o ciclo livre. A
  plataforma de verdade fica parada esperando o `start`.
- **Restaurar o MRU simulado** volta configurações, calibração gravada e align ao padrão de fábrica.

Com isso dá para fazer o fluxo inteiro sem hardware: Aquisição → sessão → Calibração → relatório → Produção (envio da
calibração ao MRU simulado e conferência pelo CRC).

**Falha simulada:** em Ajustes, escolhe um defeito para ver o diagnóstico e a atualização reagirem, sem hardware: Kernel que não responde no boot, que para, com checksum errado ou congelado, MRU reiniciando sozinho, processamento travando; e, na atualização, linha ruidosa (blocos repetidos), erro de gravação (o firmware atual continua) e firmware novo que cai (o MRU volta sozinho ao anterior). A escolha não volta na próxima abertura.

## 7. Diagnóstico

Em qualquer tela, uma faixa diz o problema mais grave com o motivo e o botão que resolve, e "detalhes" mostra os outros e os eventos do MRU. Vale para quando **não há dados**: porta inexistente, sem permissão ou ocupada, baud errado (chegam bytes ilegíveis), MRU mudo, stream chegando sem ACK (fio TX), Kernel que não respondeu no boot ou parou, stream desligado. E para **dados ruins**: congelados, NaN, aceleração impossível, checksum, taxa abaixo do configurado (e se a banda comporta), perdas, linhas corrompidas, travadas, porta saturada, reinício por panic, watchdog ou queda de alimentação, MRU reiniciando sozinho.

O app pergunta ao firmware (`$diagnostics!`, `$log!`) só fora da gravação, sem ocupar o terminal; os eventos em tempo real (`#E 12.340 kernel mudo`) chegam pela porta e aparecem no terminal, no chip *Eventos*. Firmware anterior à v1.0.9 não responde a isso: o que dá para ver é o que chega pela porta, e a faixa sugere atualizar. Os comandos estão no [README do firmware](../Hardware/Embedded/Main/README.md).

## 8. Atualizar o firmware

Em **Dispositivo → Atualizar firmware**: o caminho já vem em `Hardware/Embedded/Main/build/esp32.esp32.esp32s3/Main.ino.bin` (instalado, o `.bin` que veio junto) e **Escolher…** aceita outro. O app mostra versão, tamanho, data e tempo estimado, e recusa na hora o que não serve: merged, bootloader, partitions, firmware da mesa, arquivo cortado ou corrompido. Avisa se o arquivo é mais antigo que o MRU ou que o código, e se a linha é lenta (a 9600 bps leva ~10 min; pelo USB, ~20 s).

**Enviar ao MRU** conecta, se preciso, e passa por Sincronizar → Preparar → Enviar → Verificar → Reiniciar → Confirmar, com a barra e o que está acontecendo. Bloco ruim ou confirmação perdida se repetem sozinhos; o MRU só troca de firmware depois de conferir a imagem inteira, e qualquer falha deixa o atual rodando. O firmware novo fica 10 s em prova: se cair, o bootloader volta ao anterior, e o app diz isso em vez de "atualizado". Cancelar vale até o fim do envio. Gravando, a atualização é recusada.

A porta fica reservada durante o envio, então outra tela não consegue mandar comando no meio. Um MRU até a v1.0.8 é atualizado pelo protocolo dele, sem CRC por bloco nem prova.

## 9. Referência em debug (sem a plataforma)

Na Aquisição, em modo de calibração e sem a plataforma conectada, a caixa **Sem plataforma · referência em debug**
deixa gravar e calibrar só com o MRU. O `Session` usa como referência os ângulos do próprio MRU (pitch, roll e proa)
filtrados sem atraso (Butterworth de 2ª ordem a 2 Hz, ida e volta) e marca a sessão com `reference: debug`. O pipeline
roda inteiro, mesmo sem trecho parado ou sem balanço, e o pacote sai com `reference: debug` no `calibration.json`; o
certificado ganha a faixa e a marca d'água **REFERÊNCIA EM DEBUG** e um rodapé avisando que não atesta a calibração.
Com a plataforma conectada, a referência é sempre a dela.

## 10. Telas

As telas rodam a 60 fps com o gráfico e o terminal a 200 Hz. Sombra em volta de um card com canvas custa caro: o WebKitGTK refaz o borrão a cada quadro, e só isso derrubava o gráfico para 24 fps.

Nenhuma tela rola: cada uma ocupa a janela, e só listas, terminal e painéis longos rolam por dentro. A janela abre em
modo janela, centrada, com 1600 × 900 (pixels lógicos) ou 92% da área útil da tela, o que for menor; maximizar ou F11
(tela cheia) ficam com o usuário. A letra escala com o tamanho da janela, então as proporções são as mesmas de 1280 × 720
a 1920 × 1080; abaixo de 1180 px de largura a barra lateral vira só ícones. O gráfico é um só
por tela, com a grandeza escolhida (atitude, heave, aceleração, giro…) e as variáveis dela ligadas ou não, cada uma com
uma cor fixa; a plataforma aparece tracejada na cor da variável do MRU.

| Tela | Para quê |
|---|---|
| Início | Horizonte artificial e leituras ao vivo, conexão automática, estado do ambiente, o fluxo Aquisição → Calibração → Produção com o último resultado de cada passo, ferramentas e guias. |
| Monitor | Gráfico ao vivo, todas as leituras, saúde do stream, resumo de 20 min (Arf, VArf, SHR) e o terminal, aberto ao entrar e recolhível, com o stream na taxa em que chega (o chip *Stream* esconde). |
| Aquisição | Três passos com o estado de cada um: modo (calibração, SCALE, CALIBRATED, RAW ou como está) com o que o MRU transmite agora, referência (plataforma ou debug) e gravar, com o que vai acontecer e o que ainda falta; gravação com cronômetro e a linha do tempo do programa da plataforma (parado → pitch → roll → repouso), e a sessão salva, com o gráfico do MRU contra a plataforma. |
| Calibração | Sessões, prévia, pipeline e a biblioteca de pacotes com o resultado de cada um. Durante o pipeline, uma janela mostra as etapas, a barra, o tempo decorrido e o restante. |
| Produção | Envia a calibração pela serial (`CL:`, CRC por chave, flash, reinício, conferência) e configura a saída de operação com autostream. |
| Dispositivo | Identificação do MRU, reiniciar, ver a configuração em JSON, **diagnóstico** com a lista do que está bem e os eventos do MRU desde o boot, e em abas a configuração com um reinício só, a **atualização do firmware** e o align do Kernel, com o terminal largo na mesma tela. |
| Ajustes | Simulação com a falha simulada, Python do pipeline (escolher um ou instalar o do app), pastas e *Apagar sessões e calibrações*, que esvazia as duas pastas depois de confirmar (recusa durante uma gravação). |
| HMS | Painel de helideque simulado sobre o stream (limites da NORMAM-223, máximos de 20 min, SHR com histerese do guia Bristow). |

## 11. Pipeline × notebooks

`Pipeline/<Etapa>/index.py` é a cópia dos notebooks de `Calibration/`, etapa por etapa, com a mesma API
(`update()`, `apply()`, `getParams()`, `info()`). Mudou um lado, mude o outro.

| Notebook em `Calibration/` | Módulo em `Pipeline/` |
|---|---|
| `Dataset/Format.ipynb` | `Format/index.py` |
| `1 - Filters/1 - Model.ipynb` (+ `Nature/`) | `Filters/index.py` (+ `Nature/`, cópia idêntica) |
| `2 - Correction/1 - Model.ipynb` | `Correction/index.py` |
| `3 - Attitude/KalmanFusion/1 - Model.ipynb` | `Attitude/KalmanFusion/index.py` |
| `3 - Attitude/LinearFit/1 - Model.ipynb` | `Attitude/LinearFit/index.py` |
| `3 - Attitude/MachineLearning/{1,2,3}.ipynb` | `Attitude/MachineLearning/index.py` (+ `Selector/`, `RandomSearch/`) e `Metrics/CrossValidation/` |
| `4 - Heave/1 - Model.ipynb` | `Heave/index.py` |
| `5 - Lever/1 - Model.ipynb` | `Lever/index.py` (o ponto vem da tela de Calibração) |
| `Analysis.ipynb` | `Analysis/index.py` |
| `Certificate/1 - Certificate.ipynb` | `Certificate/index.py` (+ `images/`) |
| células de exportação dos `config.h` | `Firmware/index.py` (escreve os `config.h` e lê de volta as chaves do `CL:`) |

**Tempo.** Num ensaio de ~5 min a 200 Hz o pipeline leva ~4 min com KalmanFusion e ~20 s com LinearFit (antes, mais de
1 h): os filtros calculam o espectro de Welch de cada eixo uma vez e buscam o corte com um orçamento de uma dimensão
(população 8, até 40 gerações com paciência de 10, 2 corridas), e o laço do Kalman é compilado pelo `numba`. As mesmas
mudanças estão nos notebooks; depois delas os `config.h` de filtros, correção, align e Kalman do `test1` saíram idênticos
entre notebook e app, e a atitude difere ~1e-13°.

Conferido em 05/11/2026 contra os notebooks no `test1` (10 Hz) e numa sessão de 335 s a 200 Hz gravada pelo app com o
MRU e a plataforma simulados, nas três estratégias: `config.h` idênticos e csv iguais até ~1e-13. Diferenças conscientes: o
MachineLearning do app treina e usa um modelo por execução; o `5 - Lever` lê o pivô do `heave.json` com 10 dígitos,
o que dá ~1e-7 no `heave_ref`; e só o app tem as guardas da referência em debug (sem trecho parado ou sem balanço), que
não mudam nada num ensaio com a plataforma.

## 12. O que falta

- **Hardware:** o fluxo inteiro foi exercitado com o MRU e a plataforma simulados, pela interface real contra o backend
  real, e o firmware real no PC (`Hardware/Embedded/Host`, com um Kernel falso) contra a interface real; falta repetir com o
  MRU e a mesa de verdade (o MRU de bancada não estava disponível). Em especial: a atualização no USB nativo, em que a porta
  some e volta no reinício, a escrita real na flash e o rollback no bootloader de verdade.
- **Mesa:** o atraso do motor e a aceleração tangencial da mesa simulada são previsão a partir do código do
  FastAccelStepper, ainda não medida na mesa real.
- **Windows:** o executável e o instalador NSIS saem do Linux para `x86_64-pc-windows-gnu`, com o firmware e o pipeline
  dentro, mas nunca rodaram: abrir o app, a instalação do Python pelo app (`install.ps1`), os workers do Nature por *spawn* e a
  ausência de janelas de console só se conferem numa máquina Windows.
- **Picos de ~70° na saída calibrada do MRU real:** a simulação com o espelho do Kalman aponta uma travada da
  `thread0` seguida de um pacote com `dt` de microssegundos (o `KernelSensor` carimba o pacote na leitura): o buraco
  zera a covariância de inclinação e o `alpha = Δω/dt` explode no braço de 3,6 m do pêndulo do test1 (4–13° nivelado,
  60–160° em roll perto de pitch 85°; com braço zero, < 1°). Opções, a decidir: calibrar o braço para a instalação;
  calcular `alpha` com `max(dt, nominal)` no firmware e no notebook/pipeline; carimbar o pacote pela chegada; achar a
  causa das travadas.
- **README.html** de `Hardware/Embedded/Main` e `Calibration` não foram regenerados (o gerador não está no repositório).
