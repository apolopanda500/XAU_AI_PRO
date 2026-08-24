# Pesquisa MQL5 Codebase — Recomendações para XAU_AI_PRO

> **Data da pesquisa:** 15/08/2026  
> **Projeto:** XAU_AI_PRO (trading automatizado de XAU/USD)  
> **Objetivo:** Curadoria de indicadores, bibliotecas, EAs e scripts recentes do MQL5 Codebase que sejam compatíveis e úteis para o projeto.

---

## Índice

1. [Indicadores Recomendados](#indicadores-recomendados)
2. [Bibliotecas Recomendadas](#bibliotecas-recomendadas)
3. [Expert Advisors (EAs) Recomendados](#expert-advisors-eas-recomendados)
4. [Scripts Recomendados](#scripts-recomendados)
5. [Ranking Geral por Prioridade](#ranking-geral-por-prioridade)
6. [Próximos Passos](#próximos-passos)

---

## Indicadores Recomendados

### 🥇 KCI Volatility Distance — ID 74838
- **Autor:** RitzFalih (Syamsurizal Dimjati)
- **Publicado:** 10/08/2026
- **Avaliação:** ⭐ 4.6 (25)
- **Visualizações:** 82
- **Tamanho:** 5,94 KB
- **Descrição:** Algoritmo proprietário baseado em matriz multidimensional que mede a força direcional do movimento de preço. Possui filtro dinâmico de ruído que se recalibra em tempo real.
- **Utilidade:** Projetado explicitamente para integração com EAs e módulos de Machine Learning. Saída numérica clara para uso como feature no dataset.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐⭐
- **Sugestão de uso:** Criar wrapper `.mqh` que exponha `GetKCIVolatilityDistance(symbol, tf)` e adicionar ao `DataLogger.mqh`.

### 🥈 KCI Directional Matrix — ID 74839
- **Autor:** RitzFalih
- **Publicado:** 09/08/2026
- **Avaliação:** ⭐ 4.6
- **Visualizações:** 83
- **Tamanho:** 7,93 KB
- **Descrição:** Indicador quantitativo de análise direcional. Saídas normalizadas entre 0-100: KCI Principal, +KDI (alta), -KDI (baixa).
- **Utilidade:** Excelente para ML. Pode substituir ou complementar o RSI no `SignalCore.mqh`.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐⭐
- **Sugestão de uso:** Adicionar como features no `dataset.csv`: `kci_principal,kdi_plus,kdi_minus`.

### 🥉 CKS Position Risk Dashboard — ID 74913
- **Autor:** ksbaba055ks (Cheng Kah Seng)
- **Publicado:** 12/08/2026
- **Avaliação:** ⭐ (1)
- **Visualizações:** 47
- **Tamanho:** 7,5 KB
- **Descrição:** Dashboard somente leitura de gestão de risco. Calcula lote sugerido, saldo, margem, spread, posições abertas e risco protegido.
- **Utilidade:** Validação visual dos cálculos do `RiskEngine.mqh` e `PositionManager.mqh`.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐
- **Sugestão de uso:** Usar como indicador auxiliar no gráfico. Não integrar no EA.


### Trend Flasher -AKM — ID 74932
- **Autor:** amarfx
- **Publicado:** 13/08/2026
- **Avaliação:** ⭐ (2)
- **Visualizações:** 56
- **Tamanho:** 13,55 KB
- **Descrição:** Dashboard multi-símbolo / multi-timeframe baseado em SuperTrend (ATR + mediana high/low). Mostra Trend, Signal, Entry, Pips, SL, TP.
- **Utilidade:** Confirmação visual multi-TF. Já está no diretório do projeto.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐
- **Sugestão de uso:** Indicador visual no gráfico. Replicar lógica SuperTrend em `.mqh` própria se quiser usá-la no sinal.

### Alpha Beta Trend + Dashboard -AKM — ID 74958
- **Autor:** amarfx
- **Publicado:** 13/08/2026
- **Avaliação:** ⭐ (1)
- **Visualizações:** 39
- **Tamanho:** 9,21 KB
- **Descrição:** Filtro Alpha-Beta (simplificação do Kalman) com dashboard matricial multi-símbolo / multi-timeframe.
- **Utilidade:** Pode ser usado como filtro de tendência no `TrendFilter.mqh`.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐
- **Sugestão de uso:** Substituir ou complementar a EMA 200 do `TrendFilter.mqh`.

### MA Gauge Pro -AKM — ID 75000
- **Autor:** amarfx
- **Publicado:** 14/08/2026
- **Avaliação:** ⭐ (1)
- **Visualizações:** 31
- **Tamanho:** 27,18 KB
- **Descrição:** Escaneia múltiplos períodos de MA (10 a 100) e seleciona o MA com melhor expectativa matemática (taxa de acerto + recompensa média).
- **Utilidade:** Pode substituir as EMAs fixas (50/200) do `SignalCore.mqh`.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐
- **Sugestão de uso:** Integrar como módulo adaptativo de tendência.

### Elder Force Index — ID 75863
- **Autor:** JotaYglesias
- **Publicado:** 08/08/2026 (atualizado 10/08)
- **Avaliação:** ⭐ 5 (1)
- **Visualizações:** 79
- **Tamanho:** 10,04 KB
- **Descrição:** Implementação fiel ao livro de Alexander Elder. Fórmula: `Volume × (Close[t] - Close[t-1])`, suavizado por EMA 2 e 13.
- **Utilidade:** Feature de volume/força para ML. Funciona bem em XAUUSD por ter volume real em bolsas.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐
- **Sugestão de uso:** Adicionar como feature no `dataset.csv`.

### Double Envelopes (Historical Gauged) — ID 74860
- **Autor:** amarfx
- **Publicado:** 10/08/2026
- **Avaliação:** ⭐ (1)
- **Visualizações:** 53
- **Tamanho:** 5,7 KB
- **Descrição:** Estratégia de rompimento de volatilidade com dois envelopes (interno como filtro, externo como alvo).
- **Utilidade:** Pode fornecer feature de largura de envelope.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐
- **Sugestão de uso:** Avaliar com cuidado. Não usar como estratégia principal.

---

## Bibliotecas Recomendadas

### 🥇 Result — Type-safe error handling — ID 74427
- **Autor:** MasksymLibovych (Maksym Libovych)
- **Publicado:** 29/07/2026
- **Avaliação:** ⭐ (1)
- **Visualizações:** 55
- **Tamanho:** 15,87 KB (3 arquivos)
- **Descrição:** Biblioteca que traz o tipo `Result<T>` no estilo Rust para MQL5. Substitui o uso de `GetLastError()` global por retornos explícitos de valor ou erro.
- **Utilidade:** Aumenta a robustez do código, elimina erros silenciosos e facilita o tratamento de falhas em funções de trading.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐⭐
- **Sugestão de uso:** Refatorar funções críticas do `RiskEngine.mqh`, `ExecutionEngine.mqh` e `OrderManager.mqh` para usar `ResultValue<double>`.

### 🥈 Channel Proximity Engine — ID 73055
- **Autor:** phade (Conor Mcnamara)
- **Publicado:** 07/08/2026
- **Avaliação:** ⭐ 5 (4)
- **Visualizações:** 35
- **Tamanho:** 9,49 KB
- **Descrição:** Biblioteca que gera sinais quando o preço atinge as linhas de um canal (Donchian) e começa a reverter. Usa máquina de estados.
- **Utilidade:** Pode complementar entradas do EA em níveis estruturais.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐
- **Sugestão de uso:** Integrar ao `EntryFilter` para confirmar reversão em suporte/resistência.

### 🥉 MQTTFive — MQTT 5.0 Client — ID 73373
- **Autor:** chekh74 (Sergey Chekh)
- **Publicado:** 01/07/2026
- **Avaliação:** ⭐ (1)
- **Visualizações:** 104
- **Tamanho:** 54,14 KB (5 arquivos + exemplo)
- **Descrição:** Cliente MQTT 5.0 completo em MQL5 puro. Permite publicar preços, sinais, receber comandos e monitorar status.
- **Utilidade:** Útil para integrar o EA com sistemas externos (Python, dashboard web, alertas) sem depender de arquivos JSON.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐
- **Sugestão de uso:** Substituir/Complementar a comunicação JSON por MQTT para envio de sinais em tempo real.

### ASQ PropFirm Shield — ID 71480
- **Autor:** Robin2.0 / Algosphere Quant
- **Publicado:** 05/05/2026 (atualizado 05/06)
- **Avaliação:** ⭐ 4.2 (28)
- **Visualizações:** 235
- **Tamanho:** 48,96 KB
- **Descrição:** Biblioteca de proteção para contas de prop firm. Monitora drawdown diário, drawdown máximo, metas de lucro, consistência e dias mínimos.
- **Utilidade:** Pode substituir/aprimorar o `DailyRisk.mqh` e `EquityProtection.mqh`.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐⭐
- **Sugestão de uso:** Integrar ao `SafetyManager.mqh` para proteção de conta/prop firm.

### Institutional Kelly-VAPS Risk Engine — ID 71390
- **Autor:** KayruYuta (Amanda Vitoria)
- **Publicado:** 03/05/2026 (atualizado 02/06)
- **Avaliação:** ⭐ 4.6 (13)
- **Visualizações:** 269
- **Tamanho:** 5,4 KB
- **Descrição:** Biblioteca OOP que combina Critério de Kelly com Volatility-Adjusted Position Sizing (VAPS) usando ATR.
- **Utilidade:** Substituir modelos estáticos de risco por dimensionamento dinâmico baseado em estatística.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐⭐
- **Sugestão de uso:** Usar no `RiskEngine.mqh` para calcular lote ótimo adaptado à volatilidade.

---

## Expert Advisors (EAs) Recomendados

> **Nota:** Esses EAs não devem substituir o XAU_AI_PRO, mas sim servir como referência de estratégia, gestão de risco e execução.

### 🥇 Aegis Quantum Lite — ID 75002
- **Autor:** ksbaba055ks
- **Publicado:** 14/08/2026
- **Avaliação:** ⭐ (1)
- **Visualizações:** 25
- **Tamanho:** 9,35 KB
- **Descrição:** EA educacional com EMA 9/21, RSI 14, velas fechadas, lote fixo, painel compacto.
- **Utilidade:** Código simples e bem comentado. Útil como referência para validação de execução.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐
- **Sugestão de uso:** Estudar padrão de execução e painel. Não integrar diretamente.

### 🥈 SuperTrend_Amarnath_Kondiyan_Mohan — ID 74894
- **Autor:** amarfx
- **Publicado:** 12/08/2026
- **Avaliação:** ⭐ (1)
- **Visualizações:** 52
- **Tamanho:** 14,9 KB
- **Descrição:** EA baseado em SuperTrend com gestão de TP e SL em cesta.
- **Utilidade:** Demonstra como transformar o indicador SuperTrend em EA lucrativo.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐
- **Sugestão de uso:** Estudar lógica de saída e gestão de cesta.

### 🥉 MA + Envelope Breakouts — ID 74815
- **Autor:** amarfx
- **Publicado:** 11/08/2026
- **Avaliação:** ⭐ (1)
- **Visualizações:** 52
- **Tamanho:** 21,09 KB
- **Descrição:** EA multi-ciclo com MA + envelopes. Gerencia risco baseado em patrimônio líquido.
- **Utilidade:** Referência para estratégia de breakout e gestão de portfólio.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐
- **Sugestão de uso:** Estudar. Cuidado com possíveis bugs (divisão por 1000 vs 100 no ciclo 1).

### Market Miner — ID 74818
- **Autor:** amarfx
- **Publicado:** 11/08/2026
- **Avaliação:** ⭐ (2)
- **Visualizações:** 58
- **Tamanho:** 29,88 KB
- **Descrição:** EA multiestratégia com 4 subsistemas independentes (MA, RSI, WPR, gerenciamento por ciclo).
- **Utilidade:** Excelente referência de arquitetura modular multiestratégia.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐
- **Sugestão de uso:** Estudar organização por ciclos/magic numbers.

### EA KCI N-Matrix engine — ID 74840
- **Autor:** RitzFalih
- **Publicado:** 09/08/2026
- **Avaliação:** ⭐ (2)
- **Visualizações:** 80
- **Tamanho:** 107,04 KB
- **Descrição:** EA HFT baseado em energia cinética, grade geométrica dinâmica e recuperação unificada de lucros.
- **Utilidade:** Referência avançada de matemática aplicada ao trading.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐
- **Sugestão de uso:** Estudar com cautela. Não usar em conta real sem extensos testes.


---

## Scripts Recomendados

### 🥇 Execution Cost Sensitivity Analyzer — ID 74663
- **Autor:** Thiabot (Cristian Castillo)
- **Publicado:** 04/08/2026
- **Avaliação:** ⭐ (2)
- **Visualizações:** 69
- **Tamanho:** 23,21 KB
- **Descrição:** Analisa robustez da estratégia em relação aos custos de execução. Lê CSV com Date, Profit, Volume e gera relatório completo.
- **Utilidade:** Fundamental para validar se a vantagem do EA sobrevive a spreads/comissões reais.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐⭐
- **Sugestão de uso:** Usar após backtests para validar resiliência a custos.

### 🥈 Trade Journal Exporter — ID 74572
- **Autor:** dmck (Dror Munk)
- **Publicado:** 02/08/2026
- **Avaliação:** ⭐ (1)
- **Visualizações:** 65
- **Tamanho:** 8,87 KB
- **Descrição:** Exporta posições fechadas para CSV com preços ponderados por volume, comissão, swap, lucro, duração.
- **Utilidade:** Excelente para análise de performance e alimentação do Python.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐⭐
- **Sugestão de uso:** Substituir/Complementar o `TradeLogger.mqh` para exportar trades.

### 🥉 Position Size Calculator — ID 74571
- **Autor:** dmck
- **Publicado:** 03/08/2026
- **Avaliação:** ⭐ (1)
- **Visualizações:** 69
- **Tamanho:** 6,26 KB
- **Descrição:** Calcula lote baseado em risco (% ou valor fixo) e distância do SL. Respeita especificações do contrato.
- **Utilidade:** Validação cruzada com o cálculo de lote do EA.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐
- **Sugestão de uso:** Usar como script auxiliar para confirmar cálculos.

### Drawdown DNA Analyzer — ID 74240
- **Autor:** Thiabot
- **Publicado:** 23/07/2026
- **Avaliação:** ⭐ (2)
- **Visualizações:** 78
- **Tamanho:** 15,73 KB
- **Descrição:** Analisa curva de patrimônio diária e decompõe a estrutura das quedas (drawdowns).
- **Utilidade:** Métricas avançadas de risco: Índice de Úlcera, Índice de Dor, Fator de Recuperação.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐⭐
- **Sugestão de uso:** Usar no `PerformanceAnalyzer.mqh` ou para relatórios de backtest.

### Profit Concentration Analyzer — ID 74245
- **Autor:** Thiabot
- **Publicado:** 22/07/2026
- **Avaliação:** ⭐ (2)
- **Visualizações:** 70
- **Tamanho:** 23,42 KB
- **Descrição:** Mede concentração de lucro (coeficiente de Gini), teste de sobrevivência sem outliers, consistência diária.
- **Utilidade:** Evitar conclusões enganosas baseadas em poucas operações de sorte.
- **Compatibilidade com XAU_AI_PRO:** ⭐⭐⭐⭐⭐
- **Sugestão de uso:** Usar para validar se a vantagem é robusta ou depende de outliers.


---

## Ranking Geral por Prioridade

| Prioridade | Item | Categoria | Uso Principal | Esforço |
|---|---|---|---|---|
| 1 | KCI Volatility Distance (74838) | Indicador | Feature ML + confirmação de sinal | Médio |
| 2 | KCI Directional Matrix (74839) | Indicador | Feature ML + substituição do RSI | Médio |
| 3 | Result — Error Handling (74427) | Biblioteca | Robustez do código | Médio |
| 4 | ASQ PropFirm Shield (71480) | Biblioteca | Proteção de conta/prop firm | Médio |
| 5 | Institutional Kelly-VAPS (71390) | Biblioteca | Cálculo dinâmico de lote | Médio |
| 6 | Trade Journal Exporter (74572) | Script | Exportação de trades | Baixo |
| 7 | Execution Cost Sensitivity (74663) | Script | Validação de custos | Baixo |
| 8 | Drawdown DNA Analyzer (74240) | Script | Análise de risco | Baixo |
| 9 | Profit Concentration Analyzer (74245) | Script | Robustez estatística | Baixo |
| 10 | CKS Position Risk Dashboard (74913) | Indicador | Validação visual de risco | Baixo |
| 11 | Trend Flasher -AKM (74932) | Indicador | Dashboard visual SuperTrend | Baixo |
| 12 | MQTTFive (73373) | Biblioteca | Integração externa via MQTT | Alto |
| 13 | Channel Proximity Engine (73055) | Biblioteca | Sinais de canal | Médio |
| 14 | MA Gauge Pro -AKM (75000) | Indicador | MA adaptativa | Alto |
| 15 | Alpha Beta Trend + Dashboard (74958) | Indicador | Filtro de tendência | Médio |
| 16 | Elder Force Index (75863) | Indicador | Feature de volume | Médio |
| 17 | SuperTrend EA (74894) | EA | Referência de saída | Estudo |
| 18 | Market Miner (74818) | EA | Referência multiestratégia | Estudo |
| 19 | Aegis Quantum Lite (75002) | EA | Referência simples | Estudo |

---

## Próximos Passos

1. **Validar indicadores visualmente** no gráfico de XAUUSD antes de qualquer integração.
2. **Criar wrappers `.mqh`** para KCI Volatility Distance e KCI Directional Matrix.
3. **Adicionar features ao `DataLogger.mqh`** para enriquecer o `dataset.csv` enviado ao Python.
4. **Atualizar o `pipeline.py`** para usar as novas colunas no treinamento.
5. **Testar bibliotecas de risco** (ASQ PropFirm Shield, Kelly-VAPS) em conta demo.
6. **Usar scripts de análise** após cada rodada de backtest para validar robustez.

---

*Documento gerado automaticamente a partir de pesquisa no MQL5 Codebase.*

