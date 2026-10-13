# Filtro de Kalman modificado para o MRU: atitude, heave e componentes inerciais

Documentação do algoritmo de `1 - Model.ipynb` (classe `KalmanFilter`) e do seu porte em C++ (`Hardware/index.h`,
classe `KalmanModel`). Todos os números deste documento saem da execução do notebook registrada em
`Backup/model_3` (08/10/2026), salvo quando marcados como **teste de desenvolvimento**.

---

## 1. Resumo

O filtro recebe os dados crus do Kernel-120 — aceleração $a_x, a_y, a_z$ e taxa angular $g_x, g_y, g_z$ — e
entrega, amostra a amostra e de forma causal:

- **atitude** (roll, pitch, yaw) por um *Multiplicative Extended Kalman Filter* (MEKF) de seis estados de erro;
- **heave** no ponto de medida, sua taxa e sua aceleração, pela cadeia de filtros do MRU-5 descrita na patente
  EP 2 092 402 B1, somando o heave do centro de rotação ao termo geométrico do braço de alavanca;
- **componentes inerciais filtradas**: taxa e aceleração angular por osciladores harmônicos de Kalman com
  frequência adaptativa (patente WO 2011/034435 A1), a aceleração transportada para o ponto de medida e o
  período dominante de cada eixo.

Resultado no ensaio de pêndulo (Seatex MRU 5/H como referência):

| grandeza | erro | observação |
|---|---|---|
| roll | 0,24° RMS (0,17° no trecho de teste) | correlação 0,9997 |
| pitch no balanço | 0,18° RMS | o pitch da Seatex em repouso está 0,9° fora da gravidade |
| roll / pitch em repouso contra a gravidade | 0,15° / 0,12° RMS | atitude que o acelerômetro da Seatex mede |
| yaw | 1,26° RMS | não observável sem magnetômetro; a própria Seatex deriva |
| heave na banda do pêndulo | 5,0 mm RMS, correlação 0,986 | sinal de ~30 mm de desvio padrão |
| C++ `double` contra Python | ≤ 3·10⁻¹³ em todas as 18 saídas | mesmo algoritmo |
| C++ `float` contra Python | ≤ 9·10⁻⁵ ° na atitude, ≤ 5 µm no heave | precisão do ESP32 |

Nos outros cinco ensaios `rolling_z` de pêndulo, independentes (parâmetros desta busca, só a montagem
recalibrada), a média foi roll 0,24°, pitch 0,19°, yaw 1,8° e heave 3,0 mm RMS contra 9,5 mm de sinal.

---

## 2. Fontes

### 2.1 As duas patentes

**[EP] Kyllingstad, Å. — *Method and apparatus for active heave compensation*, EP 2 092 402 B1
(National Oilwell Varco), concedida em 05/08/2015; WO 2008/068445.** Descreve como um MRU (o MRU-5 da
Kongsberg Seatex) mede o heave e os erros que o filtro introduz. O que este trabalho usa dela:

- [0056] cada integração da aceleração vertical é combinada com um passa-alta de segunda ordem; para a
  velocidade o filtro *General Purpose* (GP), para a posição o GP ou o *Hydrographic Survey* (HS):
  $G_{GP} = \dfrac{s^2}{s^2 + 2\varepsilon\omega_c s + \omega_c^2}$,
  $G_{HS} = \dfrac{s^2 + 4\varepsilon\omega_c s}{s^2 + 2\varepsilon\omega_c s + \omega_c^2}$, com
  $\omega_c = 2\pi/(10\,T_h)$ e $T_h$ o período de heave configurado (2 a 25 s);
- [0064]–[0065] e reivindicação 2: o avanço de fase da velocidade é corrigido por $v_G = 2\varepsilon\omega_c\,p$;
- [0033] e [0035]: o heave num ponto afastado é o do MRU mais o que a rolagem e a arfagem produzem no braço de
  alavanca (*lever arm compensation*);
- [0059] e [0076]: filtro de vibração e atraso de sinal como fontes de erro (aqui, motivo para não filtrar a
  entrada nem atrasar a saída);
- Apêndice A: exemplo de configuração de um MRU-5 (modo HS, $\varepsilon = 0{,}7$, $T_h = 25$ s).

**[WO] Rinnan, A.; Sanne, F. O.; Bogfjellmo, T.; Fjellstad, O. E.; Hukkelaas, T.; Johansen, E. — *Method and
system for modelling rotary accelerations of a vessel*, WO 2011/034435 A1 (Kongsberg Seatex AS), publicada em
24/03/2011.** Modela a aceleração angular de um navio por osciladores harmônicos independentes num filtro de
Kalman, para transportar acelerações a outros pontos. O que este trabalho usa dela:

- Eq. 1 e 2: velocidade e aceleração num ponto $m$ a partir das do instrumento,
  $a_{mp} = a_{mi} + C(\dot\omega\times r + \omega\times(\omega\times r))$;
- Eq. 2.1: a derivada numérica da taxa é ruidosa, e o ruído é multiplicado pelo braço;
- Eq. 9–12: o oscilador $\dot x_1 = x_2$, $\dot x_2 = x_3 = -D x_2 - \Omega^2 x_1$, sua forma discreta e as
  matrizes de medida para ângulo, taxa ou ambos;
- Eq. 13: covariância de processo diagonal;
- Eq. 18.1–18.4: estimativa da frequência $\Omega$ e do período $T = 2\pi/\Omega$ a partir do próprio movimento;
- reivindicação 14: verificação de integridade das medidas;
- exemplo: $\Delta t = 0{,}1$ s, amortecimento 0,05, período inicial 9 s.

A Eq. 10.3 da WO, $x_3(k+1) = -D\,x_1(k) - \Omega^2 x_2(k)$, troca $x_1$ e $x_2$ em relação à Eq. 9.2 e à matriz
da Eq. 11.2; aqui vale a forma física, $x_3 = -D x_2 - \Omega^2 x_1$.

### 2.2 Literatura de estimação

| componente | referência |
|---|---|
| MEKF, erro multiplicativo de atitude | Lefferts, Markley e Shuster (1982); Markley (2003); Solà (2017) |
| exponencial exata do vetor de rotação na integração da atitude | Savage (1998) |
| discretização do ruído de processo com o termo cruzado atitude–bias | Farrell (2008) |
| forma de Joseph da covariância | Bucy e Joseph (1968) |
| equação da força específica num ponto afastado (braço de alavanca) | Titterton e Weston (2004); WO Eq. 2 |
| consistência do filtro pelo NIS ($\chi^2$) | Bar-Shalom, Li e Kirubarajan (2001) |
| detector de repouso com janela | Skog, Händel, Nilsson e Rantakokko (2010) |
| variância de Allan e densidades ARW/VRW | IEEE Std 952-1997 |
| mínimos quadrados recursivos com esquecimento | Ljung (1999) |
| relação de amortecimento crítico $K_2 = K_1^2/(2-K_1)/\Delta t$ citada pela WO | Benedict e Bordner (1962) |
| sintonia adaptativa do filtro de heave de MRU | Godhavn (1998) |
| busca dos parâmetros (CMA-ES) | Hansen e Ostermeier (2001); Hansen (2016) |
| movimento de navio | Fossen (2011) |

As referências completas estão na seção 12.

### 2.3 Sensores

- **Kernel-120 A40A90 (Inertial Labs)**, a IMU do MRU. Datasheet: ARW 0,3 °/√h, VRW 0,06 m/s/√h (faixa de
  ±40 g), banda de 260 Hz, taxa interna de 2000 Hz. No modo HR o pacote traz aceleração em g·10⁶, taxa em
  °/s·10⁵ e ângulos em °·10³ (ICD rev. 1.42).
- **Seatex MRU 5/H (Kongsberg)**, a referência, lida pela sentença `$PSXN`: roll, pitch, yaw, taxas,
  acelerações, quaternion, *sample time* e `LA PosMonD`, o heave compensado por braço de alavanca, **positivo
  para baixo** (Installation Manual rev. 9, variável 109).

---

## 3. Dados e o que se descobriu neles

O ensaio é o `test5/rolling_z` do `Analysis/Calibration_OLD/Pendulum_Compare_MRU`: os dois sensores presos num
pêndulo que balança em roll a partir de ~28°, gravados a ~10 Hz no mesmo laço. O `Format` recortou o balanço
(0–80 s) e um repouso (180–280 s) e gravou `Calibration/Dataset/test1/files/data.csv`.

### 3.1 O `Format` espelhou o acelerômetro do alvo

`Format/Target/Analysis.ipynb` troca colunas para pôr o Kernel no referencial da Seatex:
`ay`↔`az` sem trocar sinal e `wy`↔`wz` trocando o sinal de um deles. As duas trocas diferem por uma matriz de
determinante −1: o acelerômetro e o giroscópio do alvo passaram a viver em referenciais espelhados, e nenhuma
rotação de montagem conserta isso. A prova veio do modelo de corpo rígido:

- nos eixos do `Format`, o raio do pêndulo estimado pelo termo centrípeto (eixo radial) saía 1,95 m e pelo
  termo tangencial 1,57 m — o mesmo ponto rígido não pode ter dois raios;
- nos eixos crus do Kernel os dois concordam (1,956 m e 1,933 m), o desalinhamento em x cai de −4,2° para 0,6°
  e as taxas $w_y$, $w_z$ passam a ter correlação positiva com as da Seatex;
- o filtro antigo compensava o espelhamento com `align` = (−4,8; −8,6; 0,1)° e braço = (1,87; −1,74; 0,15) m,
  sem sentido físico (o raio real é ~1,93 m).

O notebook desfaz a troca logo ao renomear as colunas e volta aos eixos crus, que são os que o firmware recebe.

### 3.2 O heave da Seatex: certo na banda, transitório do próprio filtro abaixo dela

O `la_pos_mon_d` faz excursões de −3,1 m a +2,4 m durante um ensaio em que o sensor não sobe nem desce mais
que alguns centímetros. Duas verificações explicam:

- **verdade cinemática:** num pêndulo rígido o deslocamento vertical de um ponto a $m$ do pivô é
  $z = [R\,m]_z$, sem integração nenhuma. Com a atitude e o braço da Seatex, na banda 0,25–2,5 Hz ela
  reproduz essa verdade com **1,48 mm RMS e correlação 0,9984**;
- **identificação do filtro:** a cadeia da EP aplicada à aceleração vertical da própria Seatex, na gravação
  bruta inteira, reproduz o `la_pos_mon_d` com **0,096 m RMS em 300 s** no modo GP, com
  $T_h = 23{,}6$ s, $\varepsilon = 0{,}47$ e um resto de DC de −2 mm/s²; o modo HS fica em 0,315 m.

As excursões lentas são a resposta do filtro GP (período natural $10\,T_h \approx 236$ s) ao levantar e soltar
o pêndulo e a milésimos de m/s² de erro de aceleração vertical. Por isso o heave é comparado com a Seatex só na
banda do movimento (`HEAVE_BAND` = 0,25–2,5 Hz).

### 3.3 O pitch da Seatex depois do balanço

Antes do balanço, parada, a Seatex informa pitch 0,42° e o acelerômetro dela dá 0,67°. Depois do balanço,
parada no mesmo lugar, informa 1,60° e o acelerômetro continua em 0,67°. O balanço deixou ~0,9° de erro no
pitch da referência. Consequências:

- a montagem é calibrada só no balanço;
- o pitch parado é avaliado contra a atitude que a gravidade dá no acelerômetro da Seatex
  ($\mathrm{roll} = \operatorname{atan2}(-u_y, -u_z)$, $\mathrm{pitch} = \operatorname{atan2}(u_x, \sqrt{u_y^2 + u_z^2})$, $u = f/\lVert f\rVert$);
- a busca de parâmetros não usa o pitch parado.

### 3.4 Ruído e picos do Kernel nesta aquisição

- Parado, o Kernel tem 0,23 °/s e 0,02 m/s² de desvio por amostra, contra 0,01 °/s e 0,0006 m/s² da Seatex.
  Em τ = 1 s o desvio de Allan fica ~15× acima do ARW e ~6× acima do VRW do datasheet: os pacotes do modo HR
  são instantâneos de um sinal de 260 Hz de banda lidos a 10 Hz, e o ruído de toda a banda se dobra para dentro
  de 0–5 Hz.
- O acelerômetro do Kernel tem picos isolados de 1 a 3 m/s² (por exemplo em t = 7,0 s, nos três eixos, com
  perturbação também no giro) que a Seatex, presa no mesmo pêndulo, não vê.
- Durante o balanço o resíduo do modelo de corpo rígido é ~0,13 m/s², contra 0,02 m/s² parado: ruído de
  amostragem (instante da amostra) e vibração local.

### 3.5 O firmware atual entrega aceleração em g

`Hardware/Embedded/Main/objects/sensors/Kernel/index.h` converte o modo HR como `ax = ax_raw/1e6` (g) e
`wx = wx_raw/1e5` (°/s). O `KalmanModel` que está hoje em `objects/processing/models/kalman` compara a norma
dessa aceleração com `KALMAN_GRAVITY` = 9,81 e subtrai o braço de alavanca em m/s²: no dispositivo o detector de
repouso nunca dispara, o gate infla sempre e a compensação do braço sai 9,8 vezes maior que a aceleração. Além
disso o `align` exportado foi ajustado nos eixos espelhados do `Format`, não nos eixos crus que o firmware lê.
O `Hardware/index.h` novo recebe g e °/s e converte por dentro (`KALMAN_G0`), nos eixos crus.

---

## 4. Referenciais, convenções e unidades

| item | convenção |
|---|---|
| navegação | $x$, $y$ horizontais, $z$ **para baixo**; força específica em repouso $[0, 0, -g]$ |
| corpo | eixos crus do Kernel girados pela montagem `align` (Euler `xyz`, graus): $v_{corpo} = R(\text{align})^\top v_{cru}$, aplicado como `dados @ R` nas linhas da tabela |
| quaternion | Hamilton, $q = [w, x, y, z]$, corpo → navegação, $v_{nav} = R(q)\,v_{corpo}$ |
| ângulos | Euler extrínseco `xyz` (roll em x, pitch em y, yaw em z), o mesmo da Seatex; sem salto de 360° entre amostras |
| heave, taxa e aceleração de heave | metros, m/s e m/s², **positivos para baixo**, como o `LA PosMonD` |
| braço `lever` | m, do centro de rotação (CG no navio, pivô no pêndulo) até o Kernel, no corpo |
| ponto `point` | m, do CG até o ponto onde o heave é medido, no corpo |
| entrada do Python | aceleração em m/s², taxa em °/s, tempo em s |
| entrada do C++ | aceleração em **g**, taxa em °/s, `dt` em s (o que o Kernel entrega no modo HR) |
| parâmetros de ruído | log10 no notebook e na busca; valor físico no `config.h` |

---

## 5. O algoritmo

### 5.1 Visão geral

```
 Kernel (cru)                                     saídas
 a [g], w [°/s] ─► montagem ─► integridade ─┐
                                            ├─► MEKF ─────────────► roll, pitch, yaw
              ┌── α = Δw/Δt ── braço ───────┘    │
              │                                  ├─► a_cg = (C f_c)_z + g ─► GP ─► HS ─┐
              │                                  │                                     ├─► heave, taxa
              │                                  └─► (C m)_z ─────────────► GP·HS ─────┘
              └── osciladores (WO) ─► ω̂, α̂, T ─────────────► a no ponto (Eq. 2), aceleração de heave
```

Tudo é causal e amostra a amostra, na mesma ordem no Python e no C++. A primeira amostra só guarda o giro: sem
a anterior não há aceleração angular, e o braço de alavanca entraria errado no nivelamento.

### 5.2 Pré-processamento de cada amostra

1. **Montagem:** $f = R(\text{align})^\top f_{cru}$, $\omega = R(\text{align})^\top \omega_{cru}$ (rad/s).
2. **Passo:** $\Delta t_Q = t_k - t_{k-1}$ é o tempo real; acima de `GAP_FACTOR` = 3 passos nominais é **buraco**
   e o passo integrado é limitado a $\Delta t = \min(\Delta t_Q, 3\,\Delta t_{nom})$.
3. **Aceleração angular da compensação:** $\alpha_k = (\omega_k - \omega_{k-1})/\max(\Delta t_Q, 0{,}5\,\Delta t_{nom})$;
   zero no buraco. O piso de meio passo existe porque a gravação bruta tem amostras repetidas a 2,4·10⁻⁷ s, e
   $\Delta\omega/2{,}4\cdot10^{-7}$ jogava o nivelamento inicial a 32° de pitch.
4. **Taxa integrada:** $\tilde\omega_k = \omega_k - \phi\,(\omega_k - \omega_{k-1})$ (`gyroPhase` $\phi$); com
   $\phi = 0{,}5$ é a regra do trapézio.
5. **Braço de alavanca** (WO Eq. 2 invertida): $f_c = f - \omega\times(\omega\times r) - \alpha\times r$, a força
   específica do centro de rotação. É ela que vira gravidade no MEKF e aceleração do CG no heave.

### 5.3 MEKF de atitude

**Estado.** Nominal $\{q, b\}$; erro $\delta x = [\delta\theta,\ \delta b] \in \mathbb{R}^6$ com
$q_{real} = q\otimes\delta q(\delta\theta)$ e $b_{real} = b + \delta b$. O quaternion nunca é linearizado.

**Propagação.**

$$q_{k+1} = q_k \otimes \exp\!\left(\tfrac{1}{2}(\tilde\omega - b)\,\Delta t\right), \qquad
\exp\!\left(\tfrac{1}{2}v\right) = \left[\cos\tfrac{\lVert v\rVert}{2},\ \tfrac{v}{\lVert v\rVert}\sin\tfrac{\lVert v\rVert}{2}\right]$$

A exponencial é exata: a 10 Hz o passo chega a 7° e o seno já não é linear (Savage 1998).

$$\Phi = \begin{bmatrix} R(\delta q)^\top & -\left(I\Delta t - [\omega\times]\tfrac{\Delta t^2}{2} + [\omega\times]^2\tfrac{\Delta t^3}{6}\right) \\ 0 & I \end{bmatrix},
\qquad \omega = \tilde\omega - b$$

$$Q = \begin{bmatrix} (\sigma_g^2\Delta t_Q + \sigma_b^2\Delta t_Q^3/3)\,I & -\sigma_b^2\Delta t_Q^2/2\;I \\ -\sigma_b^2\Delta t_Q^2/2\;I & \sigma_b^2\Delta t_Q\,I \end{bmatrix}
\qquad P \leftarrow \Phi P \Phi^\top + Q$$

O termo cruzado de $Q$ (Farrell 2008) é o que faz o bias convergir.

**Medida do acelerômetro.**

$$z = \frac{f_c}{\lVert f_c\rVert}, \qquad h = R(q)^\top\begin{bmatrix}0\\0\\-1\end{bmatrix}, \qquad
z - h \approx [h\times]\,\delta\theta \;\Rightarrow\; H = \big[\,[h\times]\ \ 0\,\big]$$

$$R_a = \sigma_a^2\left(1 + K\left(\frac{\lVert f_c\rVert - g}{g}\right)^2\right) I$$

O posto de $H$ é 2: a rotação em torno de $h$ (a proa) não é observável sem magnetômetro.

**ZARU.** Em repouso a taxa verdadeira é zero: $z = \omega$, $H = [\,0\ \ I\,]$, $R_z = \sigma_z^2 I$. O repouso
é declarado quando $|\lVert f\rVert - g| < 0{,}2$ m/s² e $\lVert\omega\rVert < 1$ °/s **continuamente por 1 s**
(`STILL_TIME`); o pêndulo para um instante em cada inversão, e sem a janela o ZARU entraria no meio do balanço
(Skog et al. 2010 usam janelas pelo mesmo motivo).

**Ganho sem tocar a proa.** Nenhuma das duas medidas observa a proa, e as correlações de $P$ fariam a correção
de inclinação girar o yaw. A parte de atitude do ganho perde a componente na vertical da navegação:

$$K = PH^\top(HPH^\top + R)^{-1}, \qquad K_\theta \leftarrow (I - u u^\top)K_\theta, \qquad u = R(q)^\top e_z$$

**Correção multiplicativa e Joseph.**

$$\delta x = K\,(z - h), \qquad q \leftarrow q \otimes \delta q(\delta\theta), \qquad b \leftarrow b + \delta b$$

$$P \leftarrow (I - KH)\,P\,(I - KH)^\top + K R K^\top, \qquad P \leftarrow (P + P^\top)/2$$

A forma de Joseph mantém $P$ simétrica e positiva definida e continua correta para o ganho restrito (Bucy e
Joseph 1968).

**Inicialização.** Na segunda amostra: nivelamento por $u = f_c/\lVert f_c\rVert$,
$\mathrm{roll} = \operatorname{atan2}(-u_y, -u_z)$, $\mathrm{pitch} = \operatorname{atan2}(u_x, \sqrt{u_y^2 + u_z^2})$,
proa de fora (Python: `yaw0` ou a da referência; C++: `KALMAN_HEADING` ou a do Kernel na primeira amostra).

$$P_0^{\theta\theta} = C^\top \mathrm{diag}(\sigma_{tilt}^2, \sigma_{tilt}^2, \sigma_{yaw}^2)\,C, \qquad \sigma_{tilt}^2 = 1\ \mathrm{rad}^2,\ \sigma_{yaw}^2 = 10^{-4}\ \mathrm{rad}^2,\ P_0^{bb} = 10^{-4}\,I$$

O estado de erro está no corpo e as variâncias são dadas na navegação: com o sensor deitado (roll −92°) o eixo
$y$ do corpo é a vertical, e um $P_0 = I$ deixava o yaw livre para absorver a correção de inclinação (−6° nos
primeiros 2 s, **teste de desenvolvimento**).

**Buraco.** Reabre só a inclinação na navegação, guarda a variância da proa e zera a covariância cruzada
atitude–bias; osciladores e heave recomeçam. Sem zerar a cruzada, o ZARU depois do buraco girava o yaw em −12°
(**teste de desenvolvimento**).

**Integridade** (WO, reivindicação 14). Com a atitude prevista, $a_n = C f_c + g\,e_z$ é a aceleração do CG na
navegação, suave por natureza. Se ela salta mais que `spike` = 2 m/s² em relação à última aceita, numa amostra
isolada, a amostra é pico: não corrige a atitude e o heave segura o valor anterior. Duas amostras seguidas fora
são movimento, e a segunda é aceita.

### 5.4 Osciladores harmônicos (WO 2011/034435)

Um oscilador por eixo do corpo, $x = [\theta,\ \dot\theta]$, medido pela taxa já sem bias:

$$\dot x_1 = x_2, \qquad \dot x_2 = x_3 = -D\,x_2 - \Omega^2 x_1 \qquad (\text{Eq. 9.1–9.2})$$

$$x_{k+1} = \begin{bmatrix} 1 & \Delta t \\ -\Omega^2\Delta t & 1 - D\Delta t \end{bmatrix} x_k \quad (\text{Eq. 11.2}), \qquad
z = [\,0\ \ 1\,]\,x + v \quad (H_3,\ \text{Eq. 12.5})$$

$$Q = \mathrm{diag}(0,\ q_\omega\Delta t), \qquad R = \sigma_\omega^2 \quad (\text{Eq. 13})$$

**Frequência e amortecimento** (Eq. 18 na forma de mínimos quadrados). Com $\phi_k = -[x_1,\ x_2]$ e a
aceleração medida $\alpha_k$ (Eq. 2.1), $\alpha_k = \phi_k^\top[\Omega^2,\ D]$; mínimos quadrados recursivos com
esquecimento $\lambda = e^{-\Delta t/30\,\mathrm{s}}$ e um peso $W$ nos valores iniciais da WO
($\Omega_0 = 2\pi/9$ rad/s, $D_0 = 0{,}05$ 1/s):

$$S_{xx} \leftarrow \lambda S_{xx} + \phi\phi^\top, \qquad S_{xy} \leftarrow \lambda S_{xy} + \phi\,\alpha, \qquad
\begin{bmatrix}\Omega^2 \\ D\end{bmatrix} = (S_{xx} + W I)^{-1}\left(S_{xy} + W\begin{bmatrix}\Omega_0^2 \\ D_0\end{bmatrix}\right)$$

com $\Omega \in [2\pi/30,\ 2\pi/0{,}5]$ rad/s, $D \in [0, 2]$ e $T = 2\pi/\Omega$ (Eq. 18.4). Sem o peso $W = 10^{-2}$
o primeiro passo, de posto 1, jogava $\Omega^2$ a 34 rad²/s² e o estado de ângulo não se recuperava
(**teste de desenvolvimento**: α 0,26 contra 0,08 rad/s² de erro).

**Saídas:** $\hat\omega = x_2$, $\hat\alpha = x_3 = -\Omega^2x_1 - Dx_2$, $T$ e a aceleração no ponto de medida
(Eq. 2)

$$a_m = C\left(f_c + \hat\alpha\times m + \hat\omega\times(\hat\omega\times m)\right) + g\,e_z$$

cuja componente vertical é a aceleração de heave.

**Por que os osciladores não alimentam o braço de alavanca.** A aceleração $\hat\alpha$ tem menos ruído que a
diferença finita (3 a 5 vezes nos eixos menores, seção 8.4), mas, no lugar dela, piora o roll de 0,23° para
0,37° (**teste de desenvolvimento**). A diferença para trás está centrada em $t_k - \Delta t/2$, que é o instante
efetivo da amostra do acelerômetro nesta aquisição — a fase ótima do giro, $\phi \approx 0{,}56$, aponta para o
mesmo meio de passo. Na malha fechada a sincronia vale mais que o ruído; nas saídas o ruído vale mais.

### 5.5 Heave (EP 2 092 402)

**Aceleração do CG.** $a_{cg} = (C f_c)_z + g$, positiva para baixo, retida no pico; nos primeiros
`ALIGN_TIME` = 10 s depois da partida ou de um buraco a entrada é zero: com a inclinação $\delta$ ainda
convergindo, $g(1-\cos\delta) + \delta\,a_h$ vira aceleração vertical falsa, e a dupla integração a transforma
num transitório de dezenas de segundos (no `test2/rolling_z` bruto o erro do heave chegava a ~180 mm antes dessa
espera, **teste de desenvolvimento**).

**Cadeia do MRU-5.** Velocidade pelo GP, posição pelo HS:

$$v = \frac{G_{GP}(s)}{s}\,a_{cg} = \frac{s}{s^2 + 2\varepsilon\omega_c s + \omega_c^2}\,a_{cg}, \qquad
p = \frac{G_{HS}(s)}{s}\,v = \frac{s + 4\varepsilon\omega_c}{s^2 + 2\varepsilon\omega_c s + \omega_c^2}\,v, \qquad
\omega_c = \frac{2\pi}{10\,T_h}$$

Expandindo em $\omega_c/s$, $G_{GP} \approx 1 - 2\varepsilon\omega_c/s$ (avanço) e
$G_{HS} \approx 1 + 2\varepsilon\omega_c/s$ (atraso): no produto os dois se cancelam em primeira ordem,
$G_{GP}G_{HS} = 1 + O(\omega_c^2/\omega^2)$ — fase quase nula com uma distorção de amplitude, o compromisso que a EP
descreve em [0056]. Em espaço de estados, cada filtro é uma seção

$$\ddot z = u - 2\varepsilon\omega_c\dot z - \omega_c^2 z$$

com $v = \dot z_v$ (seção da velocidade com $u = a_{cg}$) e $p = \dot z_p + 4\varepsilon\omega_c z_p$ (seção da
posição com $u = v$; no modo GP seria só $\dot z_p$).

**Discretização.** A entrada é linear dentro do passo (segurador de primeira ordem), exata para o duplo
integrador e com erro $O((\omega_c\Delta t)^2)$ nos termos lentos:

$$w_j = u_j - 2\varepsilon\omega_c\dot z_k - \omega_c^2 z_k, \qquad
z_{k+1} = z_k + \dot z_k\Delta t + \Delta t^2\frac{2w_k + w_{k+1}}{6}, \qquad
\dot z_{k+1} = \dot z_k + \Delta t\,\frac{w_k + w_{k+1}}{2}$$

**Ponto de medida.** O heave do ponto é o do CG mais o que a rolagem e a arfagem produzem no braço (EP [0033]).
O termo geométrico $(C\,m)_z$ não precisa de integração e passa pelo mesmo $G_{GP}G_{HS}$, para os dois termos
terem a mesma resposta lenta:

$$\text{heave} = p + G_{GP}G_{HS}\{(C\,m)_z\}$$

Na forma de seções: $y_1 = g - 2\varepsilon\omega_c\dot z_1 - \omega_c^2 z_1$ (GP aplicado à posição
geométrica $g$) e $y_2 = y_1 + 2\varepsilon\omega_c\dot z_2 - \omega_c^2 z_2$ (HS aplicado a $y_1$). A primeira seção
parte em regime ($z_1 = g_0/\omega_c^2$), sem transitório pelo valor inicial.

**Taxa de heave.** Derivada exata do modelo,

$$\dot p = v + 2\varepsilon\omega_c\dot z_p - \omega_c^2 z_p \approx v + 2\varepsilon\omega_c\,p$$

que é a correção $v_G = 2\varepsilon\omega_c\,p$ da reivindicação 2 da EP aplicada à velocidade do GP; mais a
derivada do termo geométrico, com $\dot g = (C(\omega\times m))_z$:

$$\dot y_1 = \dot g - 2\varepsilon\omega_c y_1 - \omega_c^2\dot z_1, \qquad
\dot y_2 = \dot y_1 + 2\varepsilon\omega_c\ddot z_2 - \omega_c^2\dot z_2$$

**Escolha de $T_h$.** A EP e o manual da Seatex mandam ajustar $T_h$ ao período dominante do heave. No pêndulo
ele é 1,35 s (o dobro da frequência do balanço), e o notebook usa $T_h$ = 1,3 s; num navio são 5 a 20 s.

---

## 6. Parâmetros

### 6.1 Ajustáveis (notebook → `Hardware/config.h`)

| parâmetro | símbolo | valor exportado | origem |
|---|---|---|---|
| `g` / `KALMAN_GRAVITY` | $g$ | 9,7852 m/s² | norma média do acelerômetro parado |
| `gyroNoise` / `KALMAN_GYRO_NOISE` | $\sigma_g^2$ | 10^−3,099 = 7,96·10⁻⁴ (rad/s)²/Hz | busca |
| `biasNoise` / `KALMAN_BIAS_NOISE` | $\sigma_b^2$ | 10^−12,82 = 1,52·10⁻¹³ (rad/s²)²/Hz | busca |
| `accelNoise` / `KALMAN_ACCEL_NOISE` | $\sigma_a^2$ | 10^−0,838 = 0,145 | busca |
| `zuptNoise` / `KALMAN_ZUPT_NOISE` | $\sigma_z^2$ | 10^−2,469 = 3,40·10⁻³ (rad/s)² | busca |
| `accelGateK` / `KALMAN_ACCEL_GATE` | $K$ | 10^2,769 = 587 | busca |
| `gyroPhase` / `KALMAN_GYRO_PHASE` | $\phi$ | 0,560 | busca |
| `rateNoise` / `KALMAN_RATE_NOISE` | $\sigma_\omega^2$ | 10^−4,790 = 1,62·10⁻⁵ (rad/s)² (0,23 °/s) | variância do giro parado |
| `spike` / `KALMAN_SPIKE` | — | 2 m/s² | salto que o movimento não faz em 0,1 s |
| `heavePeriod` / `KALMAN_HEAVE_PERIOD` | $T_h$ | 1,3 s | período dominante do heave (regra da EP) |
| `heaveDamping` / `KALMAN_HEAVE_DAMPING` | $\varepsilon$ | 0,7 | EP e manual da Seatex |
| `alignX/Y/Z` / `KALMAN_ALIGN_*` | — | (90,619; 0,414; 7,540)° | calibração da montagem |
| `leverX/Y/Z` / `KALMAN_LEVER` | $r$ | (−0,179; −1,932; 0,065) m | calibração (pivô → Kernel) |
| `pointX/Y/Z` / `KALMAN_POINT` | $m$ | (−0,021; −1,978; −0,164) m | calibração (pivô → Seatex) |
| `yaw0` / `KALMAN_HEADING` | — | da referência / `NAN` (do Kernel) | proa não observável |
| — / `KALMAN_G0` | — | 9,80665 m/s² por g | unidade do modo HR |

`align`, `lever` e `point` são da **instalação do ensaio**: mudam a cada instalação (no navio, `lever` vai do CG
ao Kernel e `point` do CG ao ponto onde se quer o heave). Os ruídos, o gate, a fase e $T_h$ são do sensor e da
aplicação.

### 6.2 Constantes da classe (iguais no Python e no C++)

| constante | valor | papel |
|---|---|---|
| `TILT_P0` | 1 rad² | inclinação inicial desconhecida |
| `YAW_P0` | 10⁻⁴ rad² | proa vem de fora |
| `BIAS_P0` | 10⁻⁴ (rad/s)² | bias de um MEMS já compensado |
| `GAP_FACTOR` | 3 | intervalo acima de 3 passos é buraco |
| `MIN_STEP` | 0,5 | piso do passo na derivada do giro |
| `STILL_ACCEL`, `STILL_GYRO`, `STILL_TIME` | 0,2 m/s², 1 °/s, 1 s | detector de repouso |
| `ALIGN_TIME` | 10 s | espera do heave do CG |
| `OSC_PERIOD`, `OSC_DAMPING` | 9 s, 0,05 1/s | valores iniciais da WO |
| `OSC_NOISE` | 1 (rad/s²)²/Hz | ruído de processo da taxa nos osciladores |
| `OSC_MEMORY`, `OSC_PRIOR` | 30 s, 10⁻² | esquecimento e peso dos valores iniciais |
| `OMEGA_RANGE`, `DAMPING_MAX` | (2π/30, 2π/0,5) rad/s, 2 1/s | faixa física |
| `HEAVE_BAND` (só Python) | 0,25–2,5 Hz | banda de comparação do heave no ensaio |

---

## 7. Procedimento

### 7.1 Notebook `1 - Model.ipynb`

1. **Importando dados e defasagem** — `Calibration/Dataset/test1/files/data.csv`; atraso entre os sensores pelo
   pico da correlação cruzada do roll (0 amostras).
2. **Renomeando colunas** — volta aos eixos crus do Kernel (desfaz a troca do `Format`) e guarda da Seatex os
   ângulos, o heave, o quaternion, o acelerômetro e o giro.
3. **Período de amostragem, salvando, visualização** — grade de 0,1 s; `Backup/target.csv`; descarte das linhas
   repetidas com que a grade preencheu o buraco de 100 s.
4. **Ruído dos sensores** — desvio de Allan parado, $g$ local e $\sigma_\omega^2$.
5. **Calibração da montagem** — mínimos quadrados do modelo de corpo rígido no balanço, com oito pontos de
   partida para a montagem (pode estar em qualquer quadrante):

   $$\min_{\text{align},\,r}\sum_k \left\lVert R(\text{align})^\top f_k - R_k^\top\begin{bmatrix}0\\0\\-g\end{bmatrix} - \omega_k\times(\omega_k\times r) - \dot\omega_k\times r\right\rVert^2$$

   com $R_k$ a atitude da Seatex e $\dot\omega$ por diferença central (só dentro de trechos contínuos).
6. **Filtro de Kalman** — teoria, classe e uma primeira rodada no ponto de partida físico
   (`gyroNoise` = $\log_{10}(\sigma_\omega^2\Delta t)$, `zuptNoise` = $\log_{10}\sigma_\omega^2$, fase 0,5).
7. **Otimização** — CMA-ES (`Nature`, população 30, 40 gerações, semente 42) nos seis parâmetros de sintonia,
   em log10 onde variam por décadas. Treino: primeira metade do balanço e do repouso; teste: a segunda metade de
   cada. Objetivo $J = \mathrm{RMSE}_{roll} + \mathrm{RMSE}_{pitch,\,balanço}$. O heave fica fora: no pêndulo o CG
   não se mexe, e a busca aprenderia a calar a cadeia de integração (aconteceu num **teste de desenvolvimento**
   com critério de prontidão por covariância: a busca escolheu ruídos que nunca deixavam o heave do CG ligar).
8. **Período do filtro de heave** — varredura de $T_h$ e escolha pelo período dominante.
9. **Validação** — seção 8.
10. **Backup, modelo, exportação e validação do C++** — `Backup/model_N/{info.json, model.csv, model.json}`,
    `Hardware/config.h` e comparação amostra a amostra com o C++.

### 7.2 C++ (`Hardware/`)

| arquivo | conteúdo |
|---|---|
| `index.h` | `KalmanModel`: contrato dos modelos do firmware, `setup(dt)`, `update(sensors, angles, dt)`, `reset()`, `toString()`; saídas `pitch`, `roll`, `yaw`, `heave`, `heaveRate`, `heaveAccel`, `rate[3]` (rad/s), `alpha[3]` (rad/s²), `accel[3]` (m/s², navegação, sem gravidade), `period[3]` (s) |
| `config.h` | gerado pelo notebook; parâmetros em unidade física |
| `Test/index.cpp` | lê uma tabela (`time, ax, ay, az [g], wx, wy, wz [°/s], pitch, roll, yaw`), roda o modelo e grava as 18 saídas |
| `Test/Arduino.h` | só o `String` que o modelo usa, para compilar no computador |

`KALMAN_REAL` escolhe o tipo: `float` (padrão, ESP32) ou `double` (teste). Para usar no firmware basta trocar
`objects/processing/models/kalman/index.h` e `config.h` por estes dois: a classe tem o mesmo nome e o mesmo
contrato, e `objects/processing/config.h` já aponta `ProcessingModel = KalmanModel`. O modelo espera exatamente
o que `KernelSensor` entrega no modo HR (g e °/s, eixos crus).

```bash
g++ -O2 -std=c++17 -Wall -Wextra -DKALMAN_REAL=double -I Hardware/Test -I Hardware Hardware/Test/index.cpp -o kalman_double
./kalman_double entrada.csv saida.csv 0.1
```

Compilado para o ESP32-S3 (`esp32:esp32:esp32s3:CDCOnBoot=cdc`, core 3.3.12, `--warnings all`) num sketch de
teste: sem avisos, 311 446 bytes de flash e 22 912 bytes de RAM no sketch inteiro.

---

## 8. Testes e resultados

### 8.1 A referência

| teste | resultado |
|---|---|
| Seatex contra $(R\,m)_z$ na banda 0,25–2,5 Hz | 1,48 mm RMS, correlação 0,9984 |
| cadeia da EP na aceleração vertical da Seatex (300 s brutos), modo GP | $T_h$ = 23,6 s, $\varepsilon$ = 0,47, DC −2,06 mm/s², **0,096 m RMS** |
| idem, modo HS | $T_h$ = 19,2 s, $\varepsilon$ = 0,36, DC −0,79 mm/s², 0,315 m RMS |
| calibração da Seatex (resíduo do corpo rígido) | 0,107 m/s², braço (−0,021; −1,978; −0,164) m |
| calibração do Kernel | 0,134 m/s², montagem (90,619; 0,414; 7,540)°, braço (−0,179; −1,932; 0,065) m |

### 8.2 Implementação

| teste | erro |
|---|---|
| $H = [h\times]$ contra diferença central de $h(q\otimes\delta q)$ | 0,0 (exato) |
| $\Phi\,\delta x$ contra o erro propagado de verdade (δθ ≈ 0,003°, δb ≈ 0,03 °/s) | 1,1·10⁻⁴ relativo (segunda ordem) |
| GP·HS discreto, 8 s a 10 Hz: ganho, fase | +4,7·10⁻³, +0,015° |
| GP·HS discreto, 8 s a 100 Hz | −2,3·10⁻³, −0,010° |
| GP·HS discreto, 12 s a 10 Hz | +8,5·10⁻³, +0,038° |
| GP·HS discreto, 12 s a 100 Hz | +9,4·10⁻⁴, +0,005° |

### 8.3 Ensaio principal (RMSE)

| janela | pitch (°) | roll (°) | yaw (°) | heave (mm) |
|---|---|---|---|---|
| treino | 0,733 | 0,295 | 1,111 | 6,61 |
| teste | 0,802 | 0,170 | 1,387 | 2,56 |
| balanço | 0,178 | 0,307 | 0,177 | 7,38 |
| repouso (contra o que a Seatex informa) | 1,018 | 0,170 | 1,678 | 1,26 |
| tudo | 0,768 | 0,241 | 1,257 | 5,01 |
| repouso, contra a gravidade | 0,122 | 0,154 | — | — |

O pitch das linhas *treino*, *teste*, *repouso* e *tudo* carrega os 0,9° de erro do pitch parado da Seatex
(seção 3.3); contra a gravidade, o pitch parado erra 0,12°.

Sobreajuste — o objetivo da busca nas duas janelas:

| parâmetros | treino | teste |
|---|---|---|
| ponto de partida físico | 0,549 | 0,542 |
| busca | 0,471 | **0,351** |

O teste melhorou mais que o treino: a busca não decorou o trecho que viu.

Varredura de $T_h$ (heave no ponto da Seatex):

| $T_h$ (s) | banda contra a Seatex (mm) | banda inteira contra a verdade cinemática pelo mesmo GP·HS (mm) |
|---|---|---|
| 1,0 | 8,40 | 34,2 |
| 1,5 | 7,11 | 67,1 |
| 2,0 | 6,82 | 95,1 |
| 3,0 | 6,65 | 140,8 |
| 5,0 | 6,55 | 336,5 |
| 10,0 | 6,49 | 938,5 |

No pêndulo o CG não se mexe: tudo o que a cadeia do CG integra é ruído do acelerômetro, e a banda inteira mede
esse passeio. Quanto menor $T_h$, menos passeio e mais distorção na banda — o compromisso de qualquer dupla
integração.

### 8.4 Componentes inerciais filtradas (RMSE no balanço)

| grandeza | x (eixo do balanço) | y | z |
|---|---|---|---|
| α dos osciladores contra a diferença central do giro da Seatex (°/s²) | 4,93 | 1,52 | 0,83 |
| α por diferença finita do Kernel (°/s²) | 4,89 | 4,71 | 3,96 |

No eixo do balanço as duas empatam (o desvio padrão da α verdadeira é ~60 °/s²); nos outros dois os osciladores
têm 3 a 5 vezes menos erro. A aceleração no ponto da Seatex (Eq. 2) contra o acelerômetro da própria Seatex erra
0,14 m/s² na vertical e 0,19 m/s² na norma horizontal.

### 8.5 Consistência

O NIS da correção do acelerômetro tem média **0,0040** (mediana 0,0020, percentil 99 em 0,034) contra 3 de uma
$\chi^2_3$; nenhuma amostra passa do limite de 95% (7,81). O filtro é muito conservador: o $R$ escolhido pela
busca ($\sigma_a \approx 0{,}38$ rad no versor) cobre erros de modelo correlacionados no tempo — braço de
alavanca, instante da amostra, vibração — e não ruído branco. A covariância $P$ **não** é a incerteza real da
atitude e não deve ser usada como tal.

### 8.6 Navio sintético com verdade conhecida

Rolagem de 5° em 10 s mais 2° em 7 s, arfagem de 2° em 6 s, guinada lenta de ±1° em 40 s, heave do CG de 1 m em
8 s mais 0,5 m em 12 s, avanço e deriva de 0,5 m e 0,3 m; IMU a (2, 1, −3) m do CG, ponto de medida em
(10, 2, −5) m; ruído do Kernel parado e bias de giro de até 0,02 °/s; 900 s a 10 Hz com $T_h$ = 10 s. Erros depois
de 300 s:

| grandeza | erro |
|---|---|
| roll / pitch | 0,22° / 0,28° |
| yaw | 11,7° (bias vertical de 0,015 °/s, não observável sem repouso: ~13° em 900 s) |
| heave, banda inteira | 0,36 m (sinal de 0,84 m de desvio) |
| heave, 0,05–0,5 Hz | 0,056 m |
| heave a 8 s: ganho, fase | 1,029, +0,82° (GP·HS analítico: 1,025, +0,24°) |
| heave a 12 s: ganho, fase | 1,072, +0,79° (GP·HS analítico: 1,055, +0,77°) |
| taxa de heave | 0,050 m/s |
| aceleração no ponto (n, e, d) | 0,24; 0,19; 0,20 m/s² |

Ganho e fase na banda são os do $G_{GP}G_{HS}$ — a distorção de amplitude do modo HS que a EP descreve. Num
**teste de desenvolvimento** com os mesmos parâmetros, o erro abaixo de 0,05 Hz se decompôs assim: sem ruído
0,009 m, só o ruído do acelerômetro (0,02 m/s² por amostra a 10 Hz) 0,21 m, só o ruído do giro 0,023 m, só o
bias 0,009 m. O piso do heave é o ruído do acelerômetro integrado duas vezes.

### 8.7 Ensaios independentes

Os 12 ensaios brutos do `Format/files` (rolagem em $x$ e em $z$, sete sessões), carregados nos eixos crus;
por ensaio só a montagem e o braço foram recalibrados no trecho dinâmico; heave comparado com a verdade
cinemática no próprio Kernel:

| ensaio | resíduo Kernel | resíduo Seatex | pitch | roll | yaw | heave (mm) | heave verdadeiro (mm) | correlação |
|---|---|---|---|---|---|---|---|---|
| test1/rolling_x | 0,253 | 0,192 | 1,931 | 0,154 | 1,52 | 7,94 | 7,48 | 0,811 |
| test1/rolling_z | 0,082 | 0,050 | 0,207 | 0,331 | 3,65 | 3,03 | 14,66 | 0,986 |
| test2/rolling_x | 0,047 | 0,005 | 1,148 | 0,141 | 9,99 | 2,71 | 1,01 | −0,789 |
| test2/rolling_z | 0,072 | 0,046 | 0,308 | 0,264 | 3,31 | 3,03 | 11,78 | 0,979 |
| test3/rolling_x | 0,176 | 0,057 | 0,754 | 0,160 | 14,45 | 3,77 | 15,95 | 0,972 |
| test3/rolling_z | 0,060 | 0,024 | 0,172 | 0,199 | 1,18 | 1,93 | 6,42 | 0,971 |
| test4/rolling_x | 0,056 | 0,021 | 2,096 | 0,112 | 25,56 | 5,78 | 2,35 | −0,886 |
| test4/rolling_z | 0,056 | 0,019 | 0,121 | 0,108 | 0,21 | 1,71 | 3,60 | 0,929 |
| test5/rolling_x | 0,097 | 0,039 | 0,467 | 0,148 | 8,04 | 3,58 | 9,89 | 0,962 |
| test5/rolling_z | 0,105 | 0,082 | 0,328 | 0,266 | 0,68 | 5,08 | 22,03 | 0,977 |
| test6/rolling_z | 0,122 | 0,041 | 0,162 | 0,283 | 0,70 | 5,20 | 11,17 | 0,937 |
| test7/rolling_x | **1,003** | 0,209 | 2,154 | 1,247 | 7,70 | 84,74 | 2,59 | −0,010 |

Médias (sem o `test7/rolling_x`, que não calibra):

| família | pitch | roll | yaw | heave (mm) | heave verdadeiro (mm) | correlação |
|---|---|---|---|---|---|---|
| rolling_z | 0,216 | 0,242 | 1,62 | 3,33 | 11,61 | 0,963 |
| rolling_x | 1,279 | 0,143 | 11,91 | 4,76 | 7,33 | 0,214 |

- `rolling_z` é a família parecida com o ensaio da busca e generaliza bem. O `test5/rolling_z` é a gravação de
  onde saiu o ensaio principal; sem ele, os outros cinco dão pitch 0,194°, roll 0,237°, yaw 1,81°, heave
  2,98 mm contra 9,53 mm de sinal e correlação 0,960.
- Em `rolling_x` o pitch é o eixo do balanço e a própria Seatex fecha pior o modelo de corpo rígido; nessas
  sessões o acelerômetro dela sai girado de 2,3° a 6,4° em torno de $z$ em relação à atitude que ela informa. A
  yaw da Seatex ali deriva até 0,14 °/s.
- Nos `test2/rolling_x` e `test4/rolling_x` o heave verdadeiro no Kernel é de 1 e 2,4 mm; com sinal no nível
  do ruído a correlação não significa nada.

### 8.8 C++ contra Python

Máximo de |Python − C++| em todas as amostras do ensaio, 18 saídas:

| saída | `double` | `float` |
|---|---|---|
| roll (°) | 7,1·10⁻¹⁴ | 9,1·10⁻⁵ |
| pitch (°) | 4,1·10⁻¹⁵ | 3,7·10⁻⁶ |
| yaw (°) | 1,7·10⁻¹⁴ | 5,6·10⁻⁵ |
| heave (m) | 5,3·10⁻¹⁵ | 4,4·10⁻⁶ |
| taxa de heave (m/s) | 2,8·10⁻¹⁵ | 3,1·10⁻⁶ |
| aceleração de heave (m/s²) | 7,2·10⁻¹⁵ | 5,4·10⁻⁶ |
| taxa filtrada x, y, z (°/s) | ≤ 2,1·10⁻¹⁴ | ≤ 1,5·10⁻⁵ |
| aceleração angular x, y, z (°/s²) | ≤ 2,8·10⁻¹³ | ≤ 1,8·10⁻⁴ |
| aceleração no ponto n, e, d (m/s²) | ≤ 1,2·10⁻¹⁴ | ≤ 1,7·10⁻⁵ |
| período x, y, z (s) | ≤ 6,1·10⁻¹⁴ | ≤ 2,1·10⁻⁵ |

Em `double` a diferença é a do arredondamento da máquina: é o mesmo algoritmo, operação por operação. Em `float`
é a precisão do ESP32, ordens de grandeza abaixo de qualquer erro de medida.

---

## 9. Decisões de projeto e as alternativas descartadas

| decisão | alternativa testada | por que não |
|---|---|---|
| eixos crus do Kernel | eixos do `Format` | espelhados (seção 3.1) |
| montagem e braço por mínimos quadrados físicos | montagem e braço dentro da busca (filtro antigo) | sem sentido físico; não transfere |
| calibração só no balanço | com o repouso | o pitch parado da Seatex puxa o `align_y` e o pitch do balanço vai a 0,58°; dois ensaios independentes deixam de calibrar |
| α por diferença finita no braço | α dos osciladores | roll 0,23° → 0,37° (seção 5.4) |
| osciladores com peso nos valores iniciais | MQ puro | Ω² salta para 34 no primeiro passo |
| ganho sem componente na proa | ganho completo | yaw 2,6° → 0,6° no ensaio, 71° → 17° no navio |
| P₀ dado na navegação | P₀ = I no corpo | −6° de yaw nos primeiros 2 s com o sensor deitado |
| detector de repouso com janela de 1 s | instantâneo | ZARU nas inversões do pêndulo |
| heave do CG depois de 10 s | prontidão pela covariância | com $R$ sintonizado $P$ não é incerteza real, e a busca aprendia a nunca ligar o heave |
| heave: CG integrado + termo geométrico | integrar a aceleração do próprio Kernel | o termo geométrico não acumula ruído nem precisa de α; no pêndulo o heave inteiro é geométrico |
| busca só de atitude | atitude + heave | o heave do pêndulo empurra os parâmetros para onde o navio perde |
| população 30 na CMA-ES | 15 | para numa bacia pior (0,49 contra 0,47) |
| integridade por salto da aceleração do CG | extrapolação linear da força específica | entra em cascata e marca 700 amostras |
| α do oscilador só no caminho do heave | — | heave 0,36 m → 1,98 m no navio simulado |

Os números desta tabela que não estão nas seções 8.x vêm de **testes de desenvolvimento**, feitos com versões
anteriores do notebook e os mesmos dados.

---

## 10. Limitações

- **Proa.** Sem magnetômetro nem GNSS o yaw é só integração do giro: o ZARU segura o bias quando há repouso, mas
  em movimento contínuo a proa deriva com o bias vertical (no navio simulado, 11,7° em 900 s com 0,015 °/s). O MRU
  precisa de proa externa para yaw de longo prazo, como a própria Seatex.
- **Piso do heave.** A cadeia do CG integra duas vezes o ruído do acelerômetro. Com os instantâneos de 10 Hz deste
  ensaio, 0,02 m/s² por amostra dão ~0,2 m de passeio abaixo de 0,05 Hz com $T_h$ = 10 s. A densidade do
  datasheet (VRW 0,06 m/s/√h) é ~6 vezes menor em desvio (~36 em potência); no dispositivo, rodar à taxa do
  Kernel ou fazer média das amostras antes do filtro aproxima o ruído da densidade do sensor.
- **Distorção do HS.** A posição pelo HS tem fase quase nula e ganho alguns por cento acima de 1 perto de
  $\omega_c$ (1,025 a 8 s e 1,055 a 12 s com $T_h$ = 10 s). É a escolha da EP para compensação; se a amplitude
  importar mais que a fase, $T_h$ maior reduz a distorção.
- **$T_h$ por aplicação.** 1,3 s serve ao pêndulo; num navio vai de 5 a 20 s. O valor exportado no `config.h` é o
  do ensaio.
- **Instalação.** `align`, `lever` e `point` saem de uma calibração com referência no próprio ensaio; a bordo vêm
  do desenho do navio ou de uma calibração equivalente.
- **Covariância.** O filtro é conservador (NIS 0,004 contra 3); $P$ não serve como estimativa de erro.
- **Dados.** Um único ensaio dinâmico de 80 s com referência confiável de roll, pitch de referência enviesado
  depois do balanço, e uma aquisição a 10 Hz com instante de amostra impreciso. A busca foi validada fora da
  amostra, mas os valores ótimos dos ruídos refletem esta aquisição.

---

## 11. Arquivos

| arquivo | papel |
|---|---|
| `1 - Model.ipynb` | dados, calibração, filtro, busca, validação, exportação e teste do C++ |
| `Backup/target.csv` | ensaio na grade de 0,1 s, eixos crus |
| `Backup/model_3/info.json` | parâmetros, busca, calibração e métricas desta execução |
| `Backup/model_3/model.csv`, `model.json` | série do filtro ao lado da referência |
| `Hardware/index.h`, `Hardware/config.h` | o filtro em C++ e os parâmetros exportados |
| `Hardware/Test/` | teste do C++ no computador (`build/` é gerado pelo notebook) |
| `Nature/` | CMA-ES e demais buscas usadas na otimização |
| `Documents/` | as duas patentes |

---

## 12. Referências

1. Kyllingstad, Å. *Method and apparatus for active heave compensation.* Patente europeia EP 2 092 402 B1,
   National Oilwell Varco, L.P., concedida em 05/08/2015 (pedido internacional PCT/GB2006/050430,
   WO 2008/068445).
2. Rinnan, A.; Sanne, F. O.; Bogfjellmo, T.; Fjellstad, O. E.; Hukkelaas, T.; Johansen, E. *Method and system for
   modelling rotary accelerations of a vessel.* Pedido internacional WO 2011/034435 A1, Kongsberg Seatex AS,
   publicado em 24/03/2011.
3. Lefferts, E. J.; Markley, F. L.; Shuster, M. D. Kalman filtering for spacecraft attitude estimation.
   *Journal of Guidance, Control, and Dynamics*, 5(5):417–429, 1982.
4. Markley, F. L. Attitude error representations for Kalman filtering. *Journal of Guidance, Control, and
   Dynamics*, 26(2):311–317, 2003.
5. Solà, J. Quaternion kinematics for the error-state Kalman filter. arXiv:1711.02508, 2017.
6. Savage, P. G. Strapdown inertial navigation integration algorithm design, part 1: attitude algorithms.
   *Journal of Guidance, Control, and Dynamics*, 21(1):19–28, 1998.
7. Farrell, J. A. *Aided Navigation: GPS with High Rate Sensors.* McGraw-Hill, 2008.
8. Bucy, R. S.; Joseph, P. D. *Filtering for Stochastic Processes with Applications to Guidance.* Interscience,
   1968.
9. Titterton, D. H.; Weston, J. L. *Strapdown Inertial Navigation Technology*, 2ª ed. IET, 2004.
10. Bar-Shalom, Y.; Li, X. R.; Kirubarajan, T. *Estimation with Applications to Tracking and Navigation.* Wiley,
    2001.
11. Skog, I.; Händel, P.; Nilsson, J.-O.; Rantakokko, J. Zero-velocity detection — an algorithm evaluation.
    *IEEE Transactions on Biomedical Engineering*, 57(11):2657–2666, 2010.
12. IEEE Std 952-1997. *IEEE Standard Specification Format Guide and Test Procedure for Single-Axis
    Interferometric Fiber Optic Gyros* (anexo C: variância de Allan).
13. Ljung, L. *System Identification: Theory for the User*, 2ª ed. Prentice Hall, 1999.
14. Benedict, T. R.; Bordner, G. W. Synthesis of an optimal set of radar track-while-scan smoothing equations.
    *IRE Transactions on Automatic Control*, AC-7(4):27–32, 1962.
15. Godhavn, J.-M. Adaptive tuning of heave filter in motion sensor. *OCEANS'98 Conference Proceedings*, IEEE,
    1998.
16. Hansen, N.; Ostermeier, A. Completely derandomized self-adaptation in evolution strategies. *Evolutionary
    Computation*, 9(2):159–195, 2001.
17. Hansen, N. The CMA evolution strategy: a tutorial. arXiv:1604.00772, 2016.
18. Fossen, T. I. *Handbook of Marine Craft Hydrodynamics and Motion Control.* Wiley, 2011.
19. Welch, G.; Bishop, G. *An Introduction to the Kalman Filter.* TR 95-041, University of North Carolina at
    Chapel Hill (citado pela WO).
20. Kongsberg Seatex. *Seatex MRU 5 & H — Installation Manual*, rev. 9.
21. Inertial Labs. *Kernel-120 datasheet* e *Kernel ICD*, rev. 1.42, maio de 2025.
