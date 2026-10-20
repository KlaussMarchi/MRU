# Calibração do MRU

O pipeline usa um ensaio com o **MRU e uma mesa de referência** para ajustar as medições e avaliar o erro. Ao final, entrega **parâmetros para o firmware** e **um certificado em PDF**.

Cada notebook (`.ipynb`) lê uma tabela de medições (`.csv`), realiza uma etapa do processamento e salva o resultado para a próxima. Cada linha do CSV representa um instante do ensaio.

**Visão geral**

```text
PREPARAR          TRATAR OS SENSORES          CALCULAR O MOVIMENTO          AVALIAR

Format ─────────► Filters ──► Correction ───► Attitude ──► Heave ──► Lever ──► Analysis ──► Certificate
organizar         reduzir     corrigir        orientação   subida/   movimento   medir       emitir
o ensaio          ruído       as leituras                  descida   no ponto    o erro      o PDF
                                                          do MRU    escolhido
```

Essa é a **ordem de execução**. Algumas etapas também leem arquivos anteriores, como mostra a tabela abaixo.

**Onde ficam os arquivos**

O campo `test` do [`info.json`](info.json) seleciona o ensaio. Para `"test": 1`, a estrutura de dados fica assim após executar o pipeline:

```text
Calibration/
├── info.json                         ← ensaio selecionado, identificação do MRU e gravidade
├── Dataset/
│   ├── Format.ipynb                  ← prepara a gravação
│   └── test1/
│       ├── info.json                 ← montagem do Kernel no ensaio e remapeamento opcional dos eixos
│       ├── files/
│       │   └── data.csv              ← gravação original do Monitor
│       └── results/
│           ├── dataset.csv           ← gravação organizada e alinhada no tempo
│           ├── filtered.csv          ← sensores filtrados
│           ├── corrected.csv         ← sensores corrigidos nos eixos do navio
│           ├── attitude.csv          ← ângulos de orientação e referência
│           ├── heave.csv             ← movimento vertical no sensor
│           ├── lever.csv             ← movimento vertical no ponto escolhido
│           └── *.json                ← registros dos ajustes usados nas etapas 1 a 5
└── Certificate/
    ├── results/<variável>/           ← métricas em JSON e gráficos dos ângulos
    └── release/certificate.pdf       ← documento final
```

**O que executar, o que muda e para onde vai**

Os caminhos dos notebooks partem desta pasta, `Calibration/`. Os CSV da tabela ficam em `Dataset/testN/results/`, exceto a gravação original, em `Dataset/testN/files/data.csv`.

| Etapa e notebook | O que lê | O que faz com os dados | O que entrega → próximo uso |
|---|---|---|---|
| **0 · Preparação**<br>`Dataset/Format.ipynb` | `files/data.csv` | Organiza os eixos e os instantes de amostragem, sem preencher falhas da gravação. Compensa o atraso entre MRU e referência para comparar o mesmo movimento no mesmo instante. Calcula também a velocidade de rotação da referência a partir de seus ângulos. | **`dataset.csv`**: ensaio preparado para os cálculos → Filters. |
| **1 · Filtragem**<br>`1 - Filters/1 - Model.ipynb` | `dataset.csv` | Escolhe um filtro por eixo do acelerômetro e giroscópio para reduzir pequenas oscilações de ruído. Considera também o atraso e a deformação que o filtro pode causar no movimento medido. | **`filtered.csv`**: sensores filtrados, com a versão sem filtro preservada em `_raw` → Correction. |
| **2 · Correção**<br>`2 - Correction/1 - Model.ipynb` | `filtered.csv` | Corrige erros persistentes de leitura: desvio de zero, escala e desalinhamento dos eixos. Ajusta o efeito da temperatura quando o ensaio permite. Calcula o ajuste sobre os sensores sem filtro e aplica às versões filtrada e sem filtro. | **`corrected.csv`**: aceleração e giro corrigidos nos eixos do navio → Attitude, Heave, Lever e Analysis. |
| **3 · Atitude**<br>`3 - Attitude/<estratégia>/` | `corrected.csv` | Calcula ou calibra a orientação: **roll** é a inclinação lateral; **pitch**, a inclinação de proa/popa; **yaw**, a direção da proa. As estratégias disponíveis estão na tabela seguinte. | **`attitude.csv`**: ângulos estimados e referência, conforme as saídas da estratégia → Heave e Analysis. |
| **4 · Heave**<br>`4 - Heave/1 - Model.ipynb` | `corrected.csv`<br>+ `attitude.csv` | Usa a orientação para encontrar a aceleração vertical e descontar a gravidade. Transforma aceleração em velocidade e depois em deslocamento, com filtros para limitar o acúmulo de erro. Ajusta o cálculo contra a referência geométrica do ensaio. | **`heave.csv`**: subida/descida no local do MRU, em metros, com referência e termos auxiliares `band_x/y/z` → Lever. |
| **5 · Braço de alavanca**<br>`5 - Lever/1 - Model.ipynb` | `heave.csv`<br>+ ângulos da referência em `corrected.csv` | Calcula o movimento vertical em outro local, como o centro do helideque, usando a distância desse ponto ao MRU. Calcula também `hr`, a velocidade vertical no ponto, em m/s. | **`lever.csv`**: heave e `hr` no ponto escolhido, com suas referências → Analysis. |
| **6 · Avaliação**<br>`Analysis.ipynb` | `corrected.csv`<br>+ `attitude.csv`<br>+ `lever.csv` | Reúne os resultados pelo tempo e mede o erro dos ângulos e do movimento vertical contra a referência, em repouso e em movimento. Para aceleração e giro, calcula métricas de ruído. | **`Certificate/results/<variável>/metrics.json`** e gráficos dos ângulos → Certificate. |
| **7 · Certificado**<br>`Certificate/1 - Certificate.ipynb` | Métricas, gráficos e identificação do ensaio | Compara os resultados com os limites definidos no notebook e monta o documento com aprovação/reprovação. Atualmente, o PDF avalia roll/pitch e ruído dos sensores. | **`Certificate/release/certificate.pdf`** → documento final. As métricas de heave e `hr` ficam nos JSON. |

**Como cada etapa funciona por dentro**

Nas explicações abaixo, **RMS/RMSE** é uma medida do tamanho do erro: calcula a raiz da média dos erros ao quadrado. Quanto menor, melhor; erros grandes pesam mais.

**0 · Format — preparar uma comparação válida**

Antes de ajustar qualquer modelo, o notebook precisa garantir que MRU e referência descrevam o mesmo instante e os eixos esperados:

1. **Eixos:** lê aceleração, giro, ângulos e temperatura do MRU. Aplica as trocas de eixo e sinal descritas em `axes`, quando existem.
2. **Tempo:** estima o intervalo entre amostras pela mediana e monta uma grade regular. Usa a leitura mais próxima de cada instante, com tolerância de meio intervalo; trechos sem amostra permanecem como lacunas.
3. **Giro da referência:** a mesa fornece ângulos. O notebook usa uma **spline cúbica**, uma curva suave por trechos, para derivá-los e calcular a velocidade angular do corpo. Faz isso separadamente em cada trecho contínuo.
4. **Atraso:** usa **correlação cruzada** entre os módulos das velocidades angulares do MRU e da referência durante o movimento. Desloca as colunas do MRU pelo atraso encontrado, sem atravessar lacunas.

Por exemplo, se o MRU registrar o pico do balanço duas amostras depois da referência, esse deslocamento precisa ser compensado antes de calcular a correção. O resultado é `dataset.csv`.

**1 · Filters — quais filtros existem e como são escolhidos**

São avaliados **três filtros para cada um dos seis sinais**: `ax`, `ay`, `az`, `wx`, `wy` e `wz`. Todos são passa-baixa: preservam variações lentas e atenuam componentes rápidas. O desafio é retirar ruído sem apagar ou atrasar o movimento.

| Filtro no código | Princípio | Parâmetro ajustado |
|---|---|---|
| `LowPassFilter` / `low_pass` | Passa-baixa de **quatro polos reais iguais**. Aplica uma resposta de quarta ordem, discretizada por Tustin para operar amostra por amostra. | Frequência dos polos `Fc`, em Hz. Ela não é diretamente o corte de −3 dB; no modelo contínuo, esse corte é aproximadamente `0,435 × Fc`. |
| `ButterworthFilter` / `butterworth` | Passa-baixa de **segunda ordem**, com resposta de amplitude plana na faixa preservada. Usa Tustin com ajuste da frequência de corte. | Corte de −3 dB, em Hz; internamente convertido para uma fração da frequência de Nyquist, metade da taxa de amostragem. |
| `ExponentialFilter` / `exponential` | **Média exponencial:** a saída combina a leitura atual com a saída anterior: `y = α·x + (1−α)·y_anterior`. `α` pequeno suaviza mais; próximo de 1 acompanha a leitura quase sem filtragem. | Uma frequência equivalente, convertida em `α = 1 − exp(−2π·fc·dt)`. |

**Papel do “genético”.** O notebook chama `NatureSelector('genetic', ...)`. No [seletor atual](<1 - Filters/Nature/index.py>), esse nome aponta para a classe **CMA-ES**, implementada em [Models/Genetic/index.py](<1 - Filters/Nature/Models/Genetic/index.py>). Trata-se de uma estratégia evolutiva: gera uma população de parâmetros candidatos, avalia os resultados e adapta a distribuição dos próximos candidatos em direção às melhores regiões. Quando a busca estagna, pode reiniciar com uma população maior.

**O otimizador escolhe os parâmetros; o filtro escolhido processa as amostras.** O ESP32 recebe o tipo de filtro e a frequência ajustada; a busca evolutiva acontece no computador durante a calibração.

A escolha segue este processo:

1. **Estimar movimento e ruído:** o método de **Welch** mede como a energia do sinal se distribui pelas frequências no trecho em movimento. O código assume que o balanço ocupa poucas frequências; usa a mediana do espectro como piso de ruído e o excedente como estimativa do movimento.
2. **Avaliar cada candidato:** calcula `ε`, o erro RMS estimado após filtrar, dividido pelo erro estimado do sinal sem filtro. A conta penaliza tanto o ruído que sobrou quanto a parte do movimento que o filtro atenuou ou atrasou. É um critério espectral baseado nessa estimativa, não uma comparação direta com a mesa.
3. **Buscar a frequência:** a CMA-ES varia `log10(fc)`, permitindo explorar frequências pequenas e grandes. A configuração atual usa população inicial de **30**, `generations = 150` — orçamento de até **4.500 avaliações por execução** — e **5 execuções**, com sementes 42 a 46, para cada combinação de filtro e eixo.
4. **Escolher por eixo:** entre os três filtros ajustados, fica o de menor `ε`. São **18 buscas**, cada uma repetida cinco vezes. `ε < 1` indica melhora estimada; próximo de 1, pouco ganho; acima de 1, piora estimada. A média exponencial pode chegar a `α ≈ 1`, praticamente deixando o sinal passar.

O vencedor de cada eixo gera `filtered.csv`. Os sinais anteriores ficam em `_raw`, e `filters.json` registra a escolha. Embora `Nature/` também ofereça PSO, DE, LSHADE e LSRTDE, o notebook atual seleciona a CMA-ES pelo nome `genetic`.

**2 · Correction — montagem, escala, viés e temperatura**

Uma leitura pode estar suave e continuar errada. Esta etapa procura corrigir esse erro persistente:

1. **Construir o valor esperado:** para o acelerômetro, usa a gravidade projetada pela orientação da referência **nos trechos parados**, quando não há aceleração do balanço. Para o giroscópio, usa a velocidade angular da referência ao longo do ensaio.
2. **Descobrir a montagem:** resolve o **problema de Wahba por SVD**, encontrando a rotação que melhor alinha os vetores medidos aos esperados.
3. **Ajustar a correção:** resolve mínimos quadrados com **regularização ridge**, usando `x_corrigido = M·x + c + k·(T−T0)`. A matriz `M` ajusta montagem, escala e mistura entre eixos; `c` é o desvio de zero; `k` descreve o efeito da temperatura.
4. **Evitar ajustes sem informação:** a regularização mantém a matriz próxima da montagem quando o ensaio movimenta pouco determinado eixo. O termo térmico só é ajustado quando as amostras usadas cobrem pelo menos **10 °C** de variação.

O ajuste usa os sinais `_raw` para que o atraso do filtro não seja absorvido pela correção. Depois aplica a mesma transformação aos sinais filtrados e sem filtro, gerando `corrected.csv`.

Também exporta o `align` do ensaio para o firmware adaptar a correção a uma mudança de montagem. Essa adaptação depende do `align` registrado e de uma montagem estimada próxima de uma troca de eixos com sinais.

**3 · Attitude — três maneiras de obter a orientação**

Escolha uma estratégia dentro de `3 - Attitude/`:

| Pasta | Como obtém a orientação | Ordem dos notebooks |
|---|---|---|
| `KalmanFusion/` | Combina o giro medido pelo giroscópio com a informação de inclinação do acelerômetro. | `1 - Model.ipynb` |
| `LinearFit/` | Ajusta os ângulos que o próprio Kernel entrega para aproximá-los da referência. | `1 - Model.ipynb` |
| `MachineLearning/` | Aprende a relação entre uma sequência recente de medições dos sensores e os ângulos da referência. | `1 - Processing.ipynb` → `2 - Model.ipynb` → `3 - Compare.ipynb` |

**KalmanFusion — combinar sensores com um modelo físico.** Usa um **Kalman de estado de erro (ESKF)** com seis componentes: três erros de orientação e três desvios do giroscópio. A orientação é representada internamente por quaternion.

- O giroscópio propaga a orientação entre amostras; o acelerômetro fornece uma referência de inclinação pela direção da gravidade.
- O filtro reduz a confiança no acelerômetro quando sua medida se afasta da gravidade e compensa a aceleração causada pela distância entre o sensor e o centro de rotação.
- Ao detectar repouso pelas próprias medições, aplica **ZARU**, uma atualização de taxa angular zero para estimar o desvio do giroscópio. Inclui ainda correção de *coning*, para mudanças do eixo de rotação entre amostras.
- A **CMA-ES**, também chamada por `genetic`, ajusta os pesos de ruído, a rejeição de acelerações, o vetor do centro de rotação até o sensor e a fase de integração do giro. Minimiza a **soma do RMSE de pitch e roll** contra a referência. A configuração atual usa população inicial 15, orçamento `15 × 200 = 3.000` avaliações e uma execução.

O acelerômetro informa inclinação, mas não determina sozinho a direção absoluta da proa. No notebook, a proa inicial vem da referência quando não é fornecida; no firmware, o parâmetro exportado como `NAN` faz usar a proa inicial do Kernel.

**LinearFit — calibrar os ângulos já calculados pelo Kernel.** Ajusta por mínimos quadrados a relação `ângulos_corrigidos = M·ângulos_Kernel + B`. O notebook atual usa **`fuse=False`**: cada ângulo recebe sua própria escala e desvio, sem misturar os outros eixos. Ajusta apenas o trecho em movimento e avalia com **cinco grupos de validação cruzada**, formados por blocos contíguos intercalados. Depois aplica a correção à série inteira, incluindo o repouso.

A classe também suporta `fuse=True`, que usa uma matriz completa para combinar os três ângulos. Apesar de o texto do notebook mencionar uma seleção automática entre as duas versões, as células atuais executam somente o ajuste por eixo.

**MachineLearning — aprender a partir de uma janela de sensores.**

| Notebook | O que acontece internamente | Resultado |
|---|---|---|
| `1 - Processing.ipynb` | Organiza as amostras no intervalo `dt` e coloca a leitura atual e as anteriores de cada sensor em uma linha, sem atravessar lacunas. A configuração atual usa **30 instantes a cada 0,1 s**, com pitch e roll da referência como respostas esperadas. | `Backup/model.csv`: entradas temporais e ângulos para treino. |
| `2 - Model.ipynb` | Instancia a família escolhida em `info.json`, busca hiperparâmetros com **RandomizedSearchCV** e avalia com blocos de validação. Mede R², R² ajustado, RMSE e MAE. Depois treina o modelo final com os dados disponíveis. | `Backup/model_N/model.pkl` e `info.json`: modelo treinado e avaliação. |
| `3 - Compare.ipynb` | Compara registros do mesmo ensaio e das mesmas saídas. Dentro da família configurada, escolhe o maior **R² ajustado**, aplica o modelo e exporta as previsões. | `attitude.csv`, registro da escolha e parâmetros do firmware. |

O seletor oferece regressão linear, Ridge, Lasso, Elastic Net, KNN, SVR, Random Forest, Gradient Boosting e árvore de decisão; a configuração atual seleciona **regressão linear**. A exportação C++ existente espera um modelo linear com padronização, coeficientes e intercepto: os demais modelos do catálogo não têm todos um exportador correspondente.

**As estratégias são alternativas: a última exportada define `attitude.csv` e o modelo do firmware.** Depois de trocar a estratégia, refaça Heave → Lever → Analysis → Certificate.

**4 · Heave — integrar sem deixar o erro crescer indefinidamente**

Esta etapa usa a aceleração de `corrected.csv` e roll/pitch de `attitude.csv`, unidos por `time`:

1. **Encontrar a vertical:** gira a força medida para o referencial de navegação e compensa a gravidade. Nesta convenção, o eixo vertical aponta para baixo e a conta soma `g`. A componente vertical depende de roll e pitch, sem depender de yaw.
2. **Integrar duas vezes:** aceleração vira velocidade e depois deslocamento. Usa **duas seções de segunda ordem em cascata**, que funcionam como integradores na faixa de interesse e rejeitam componentes constantes e muito lentas. Isso limita o crescimento de posição causado por pequenos desvios do sensor.
3. **Construir a referência geométrica:** estima por mínimos quadrados o vetor do pivô ao sensor, usando as acelerações de rotação. Com a orientação da referência, calcula quanto esse ponto sobe e desce. Retira uma média móvel de **10 s** para separar oscilação de tendência lenta.
4. **Escolher período e amortecimento:** testa uma **grade de 24 combinações**: períodos de `0,5; 1; 1,5; 2; 3; 5 s` e amortecimentos de `0,5; 0,7; 1; 1,4`. Escolhe o menor RMS no movimento, excluindo os primeiros **20 s após seu início**. Aqui o ajuste é por varredura da grade.

O período define a frequência das seções por `ωc = 2π/(10·Th)`; o amortecimento controla sua resposta. Lacunas maiores que **0,5 s** reiniciam as seções. O heave representa a oscilação vertical na faixa filtrada, não uma altitude absoluta.

`heave.csv` salva heave estimado, referência e `band_x/y/z`: as contribuições da orientação já passadas pelo filtro, preparadas para a translação da etapa seguinte.

**5 · Lever — calcular o movimento no helideque**

Você informa `POINT = [dx, dy, dz]`, em metros, **do MRU até o ponto desejado**, nos eixos do navio. Esse vetor vem da instalação; o notebook não procura a posição do helideque por otimização.

Quando o navio inclina, pontos distantes do sensor têm outro deslocamento vertical. O código soma essa contribuição ao heave do MRU, mantendo a mesma filtragem:

```text
heave_no_ponto = heave_no_MRU + dx·band_x + dy·band_y + dz·band_z
```

Para conferir a geometria, testa o pivô fixo, o próprio sensor e um ponto com o dobro do braço. Os ângulos da referência, lidos de `corrected.csv`, servem para calcular o movimento esperado desses pontos e comparar.

Por fim, calcula `hr = variação_do_heave / intervalo_de_tempo`, com zero na partida e após lacunas. `lever.csv` entrega heave em metros e velocidade vertical em m/s, ambos no ponto escolhido. Com `POINT = [0, 0, 0]`, o ponto é o próprio MRU.

**6 · Analysis — transformar diferenças em métricas**

Une `corrected.csv`, `attitude.csv` e `lever.csv` pelos instantes em comum. A coluna `static` separa repouso de movimento; para as variáveis com referência, o erro é `estimado − referência`.

| Métrica calculada | O que permite observar |
|---|---|
| `std_stat` e `std_raw` | Oscilação em repouso, depois e antes do filtro. Nos dois casos, os sensores já passaram pela correção. |
| `rms_stat` e `rms_dyn` | Tamanho do erro contra a referência, separado entre repouso e movimento. |
| `rmse` e `mae` | Erro quadrático e erro absoluto médio na série comparada. |
| `r2` | Quanto a estimativa acompanha a variação da referência. |

Aceleração e giro recebem as métricas de ruído; os ângulos, heave e `hr` também recebem as métricas de erro quando têm referência. Cada variável ganha um `metrics.json`; os ângulos ganham ainda `ref_vs_model.png` e `error.png`.

**7 · Certificate — comparar com os requisitos e montar o PDF**

Lê os JSON e gráficos gerados pelo Analysis. Para cada requisito, compara o valor medido com o limite; quando a linha cobre vários eixos, o **pior valor** determina o status. Os requisitos de ruído usam desvio padrão, enquanto os de roll/pitch usam erros RMS.

Os limites atuais no notebook são **0,20° de RMS estático e 0,50° de RMS dinâmico** para roll/pitch, **0,30°/s de ruído** para o giroscópio e **0,05 m/s² de ruído** para o acelerômetro.

Há também um requisito de `rms_scale_factor` configurado, mas a implementação atual de Analysis não exporta essa métrica; o certificado omite requisitos sem valores. Embora o texto explicativo do Analysis mencione precisão e deriva, essas métricas também não são calculadas pela classe atual. O PDF apresenta os resultados disponíveis em `Certificate/results/`.

**Como iniciar um ensaio**

1. Grave MRU e mesa com [`Monitor/index.py`](../Monitor/index.py), usando o MRU em aquisição (`CF:device_mode$1!`). Inclua repouso e movimento. O Monitor salva `Monitor/output/<data_hora>/data.csv`, com tempo, indicação de repouso (`static`), MRU (`target_*`) e referência (`ref_*`).
2. Copie `data.csv` para `Dataset/testN/files/` e selecione esse número em `Calibration/info.json`. Confira também `id`, a identificação do MRU, e `gravity`, a gravidade local em m/s².
3. Em `Dataset/testN/info.json`, registre `align`: os ângulos configurados no Kernel durante o ensaio, em graus, na ordem `[proa, pitch, roll]`. O campo opcional `axes` remapeia dados de formatos antigos.
4. Execute os notebooks na ordem da tabela, com as células de cima para baixo e o diretório de trabalho na pasta de cada notebook.

**Como o ajuste chega ao equipamento**

Os CSV guardam o resultado calculado sobre o ensaio. Os **`config.h` guardam os parâmetros que o MRU usará nas novas medições**. As células de exportação escrevem diretamente em `../Hardware/Embedded/Main/objects/processing/`:

| Gerado por | Arquivo no firmware | Conteúdo |
|---|---|---|
| Filters | `filters/config.h` | Tipo e frequência de corte do filtro por eixo. |
| Correction | `correction/config.h` e `align/config.h` | Correção das leituras e montagem do ensaio para adaptar a correção quando o align muda. |
| Attitude | `attitude/config.h` e `attitude/<kalman, linear ou machine>/config.h` | Seleção da estratégia e parâmetros do modelo escolhido. |
| Heave | `heave/config.h` | Parâmetros do cálculo de movimento vertical. |
| Lever | `lever/config.h` | Posição do ponto de interesse em relação ao MRU. |

Depois de exportar, **recompile e grave o firmware** para aplicar os ajustes. Os registros `filters.json`, `correction.json`, `attitude.json`, `heave.json` e `lever.json`, no `results/` do ensaio, identificam os ajustes usados e seus backups.

Ao alterar uma etapa, execute novamente todas as que dependem dela. O Analysis recria `Certificate/results/`, e o certificado sobrescreve o PDF anterior.

O [diagrama geral do MRU](../Documents/Pipeline.png) contextualiza o sistema. O bloco NORMAM mostrado na imagem não está presente no processamento atual; o certificado usa os requisitos definidos no próprio notebook.
