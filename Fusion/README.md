# FUSÃO DE FILTROS

A fusão (ou combinação) de filtros tem como objetivo principal agregar estimativas ou medições provenientes de diferentes fontes (sensores, algoritmos de filtragem, modelos, etc.) para obter uma estimativa final mais precisa e robusta. Em vez de simplesmente fazer uma média ponderada das saídas — que é uma técnica básica — emprega-se métodos mais sofisticados, que levam em conta incertezas, correlações, ruído e até mesmo não-linearidades presentes no sistema ou nos dados.

# Filtro de Kalman
O Filtro de Kalman é um algoritmo de estimação recursiva ideal para sistemas lineares afetados por ruídos gaussianos. Ele estima o estado interno de um sistema (posição, velocidade, etc.) com base em um modelo matemático e medições ruidosas. Funciona em duas etapas:

1. Previsão: projeta o estado e a incerteza para o próximo instante:

$$x_k = A\, x_{k-1} + B\, u_k \,\,\,\,\,\,\,\,\,\,\,\,\,\,\, \,\,\,\,\,\,\,\,\,\,\,\,\,\,\, P_k = A\,P_{k-1}\cdot A^T+ Q $$

2. Atualização: corrige a estimativa com base na nova medição.

### Vantagens:
- Ótima estimativa para sistemas lineares
- Simples e eficiente
- Muito utilizado e bem documentado

### Desvantagens:
- Incapaz de lidar com sistemas não lineares
- Sensível a erros de modelagem nas covariâncias $Q$ e $R$

# Filtro de Kalman Estendido (EKF)
Adaptação do KF para sistemas não lineares. O EKF lineariza as equações de estado e de observação ao redor da estimativa atual usando as Jacobianas das funções. Assim, permite aplicar o mesmo esquema de previsão e atualização do KF mesmo quando o sistema real apresenta não linearidades.

Linearização: $\,\,\,\,\,\,F = \frac{\partial f}{\partial x}\,\,\,\,\,\,\,\,\,\,\,\,H = \frac{\partial h}{\partial x}$

Demais equações seguem o esquema do KF.

### Vantagens
- Suporta sistemas não lineares moderados
- Computacionalmente eficiente
- Facilidade de adaptação a sistemas originalmente modelados com KF

### Desvantagens:
- Linearização pode degradar a qualidade da estimativa
- Erros aumentam em sistemas com forte não linearidade
- Requer cálculo de derivadas (Jacobianas)

# Filtro de Kalman Unscented (UKF)
Melhoria do EKF para sistemas não lineares, o UKF evita a linearização e utiliza a transformada unscented, propagando pontos sigma que capturam melhor as propriedades estatísticas da distribuição. Assim, fornece estimativas mais precisas para estados e covariâncias em sistemas não lineares.

### Vantagens:
- Representa melhor a não linearidade sem necessidade de Jacobianas
- Melhor precisão que o EKF em muitos cenários
- Mais robusto a distribuições não gaussiana dos erros

### Desvantagens:
- Maior carga computacional que o EKF
- Pode ser sensível à escolha dos parâmetros da transformada

# Filtro de Kalman Federado (FKF)
É uma estrutura modular que utiliza múltiplos KFs (ou EKFs, UKFs) em paralelo, cada um associado a subconjuntos de sensores ou dados. As estimativas locais são então combinadas de forma hierárquica. O FKF melhora a escalabilidade e a tolerância a falhas em sistemas grandes ou distribuídos.

### Vantagens:
- Modularidade e escalabilidade
- Tolerância a falhas parciais (sensores ou filtros)
- Facilita o desenvolvimento e manutenção de sistemas complexos

### Desvantagens:
- Exige estrutura adicional de fusão
- Pode apresentar soluções conservadoras demais

# Filtro de Partículas (PF)
Baseado em amostragem estocástica (Monte Carlo), representa a distribuição do estado por um conjunto de partículas, cada uma com peso associado. Ideal para sistemas altamente não lineares e não gaussianos. As partículas são propagadas segundo o modelo do sistema e reponderadas de acordo com a observação atual.

Equação básica (atualização dos pesos): $w_{k}^{(i)} \propto w_{k - 1}^{(i)} p(z_k | x_k^{(i)})$

###  Vantagens:
- Flexível para tratar qualquer tipo de não linearidade e distribuição
- Robusto a falhas de modelagem
- Muito utilizado em SLAM, tracking e navegação autônoma

### Desvantagens:
- Muito mais custoso computacionalmente
- Sofre com degenerescência (acúmulo de peso em poucas partículas)
- Necessita técnicas de reamostragem

# Covariance Intersection (CI)
Técnica de fusão que combina estimativas de filtros ou sensores mesmo quando as correlações entre eles são desconhecidas ou difíceis de modelar. Utiliza uma regra de fusão ponderada que sempre garante uma covariância consistente.

- Fusão de covariâncias: $P^{-1} = \omega P_1^{-1} + (1 - \omega) P_2^{-1}$

- Fusão de estados: $\hat{x} = P\,(\omega P_1^{-1}\hat{x}_1 + (1 - \omega) P_2^{-1}\hat{x}_2)$

### Vantagens:
- Consistente mesmo sem conhecer as correlações
- Robusto a dados potencialmente correlacionados

### Desvantagens:
- Pode ser conservador (subestima a fusão)
- Definir o peso $\omega$ é uma escolha sensível

# Dempster-Shafer (Teoria da Evidência)
Método que lida explicitamente com a incerteza e a ignorância. Combina evidências de múltiplas fontes sem exigir probabilidades completas, gerando graus de crença (belief) e plausibilidade.

### Vantagens:
- Capaz de trabalhar com fontes incompletas e imprecisas
- Representa a ignorância de forma explícita
- Interessante em diagnóstico, segurança e cenários onde incerteza é inevitável

### Desvantagens:
- Pode ser computacionalmente pesado
- Difícil interpretação em sistemas grandes
- Pouco utilizado na indústria comparado aos filtros bayesianos

