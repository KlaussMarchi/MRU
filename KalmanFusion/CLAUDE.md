# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## O que é esta pasta

Estudo do filtro do MRU, derivado de `Calibration/Model/KalmanFusion` e agora independente dele: MEKF de atitude,
osciladores harmônicos da patente WO 2011/034435 (taxa e aceleração angular filtradas, aceleração no ponto de
medida) e cadeia de heave do MRU-5 da patente EP 2 092 402 (filtros GP/HS). As patentes estão em `Documents/`;
`Documentation.md` traz a teoria, as fórmulas, os parâmetros, os testes e os resultados com referências.

- `1 - Model.ipynb` — todo o fluxo: dados, ruído (Allan), calibração da montagem, filtro, busca CMA-ES,
  validação, `Backup/model_N`, exportação de `Hardware/config.h` e comparação com o C++
- `Hardware/index.h` — o mesmo filtro em C++ (`KalmanModel`, contrato dos modelos do firmware: `setup(dt)`,
  `update(sensors, angles, dt)`, `reset()`, `toString()`); `Hardware/config.h` é gerado pelo notebook
- `Hardware/Test/` — `index.cpp` roda o modelo sobre uma tabela; `Arduino.h` é só o `String`; `build/` é gerado

## Rodar

O Python do sistema não tem Jupyter funcionando; o kernel `base` é o conda:

```bash
~/miniconda3/bin/jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.timeout=1800 --ExecutePreprocessor.kernel_name=base "1 - Model.ipynb"
```

~3 min (a busca usa 8 processos). Cria um `Backup/model_N` novo (N = quantidade de `model_*` + 1), reescreve
`Hardware/config.h` e `Hardware/Test/build/`. Não roda nada fora desta pasta além de ler `../Calibration/info.json`,
`../Calibration/Dataset/test{TEST}/files/data.csv` e os ensaios brutos de
`../Analysis/Calibration_OLD/Pendulum_Compare_MRU/Format/files`.

Paridade C++ × Python fora do notebook:

```bash
g++ -O2 -std=c++17 -Wall -Wextra -DKALMAN_REAL=double -I Hardware/Test -I Hardware Hardware/Test/index.cpp -o kalman_double
./kalman_double entrada.csv saida.csv 0.1    # time, ax, ay, az [g], wx, wy, wz [graus/s], pitch, roll, yaw
```

`double` dá ~1e-13 contra o Python; `float` (o padrão, ESP32) ~1e-4 graus. Para o ESP32-S3 o FQBN é
`esp32:esp32:esp32s3:CDCOnBoot=cdc`.

## Armadilhas

- **Eixos.** O `data.csv` do `Calibration` vem do `Format`, que trocou `ay`↔`az` sem sinal e `wy`↔`wz` com sinal:
  acelerômetro e giro do alvo ficam espelhados. O notebook volta aos eixos crus do Kernel ao renomear; qualquer
  outro estudo sobre esse arquivo precisa da mesma correção.
- **Unidades.** O Python recebe m/s² e graus/s; o C++ recebe **g** e graus/s, como o `KernelSensor` entrega no
  modo HR, e multiplica por `KALMAN_G0`.
- **Paridade.** Python e C++ são o mesmo laço, na mesma ordem: a primeira amostra só guarda o giro, o repouso
  sai do detector (a coluna `static` só serve para métricas), tempos acumulados por soma de `dt`. Mudar um exige
  mudar o outro e rodar a célula de validação do C++.
- **Referência.** O `la_pos_mon_d` da Seatex só vale na banda do movimento (`HEAVE_BAND`); abaixo dela é
  transitório do filtro GP da própria Seatex. O pitch da Seatex parada depois do balanço está ~0,9° fora do
  acelerômetro dela, por isso a calibração usa só o balanço e o repouso é avaliado contra a gravidade.
- **Instalação.** `align`, `lever` e `point` são do ensaio (pivô do pêndulo); `heavePeriod` 1,3 s é do pêndulo,
  num navio vai de 5 a 20 s.
