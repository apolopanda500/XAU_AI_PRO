# AUDITORIA TÉCNICA — V1.0 (Levantamento real)

**Data:** 31/07/2026
**Escopo:** Core MQL5, IA MQL5, Python, métricas do dataset
**Status:** 🔴 Bloqueado — falta o código-fonte do EA
**Próxima etapa:** Etapa 2 — reescrever/recriar módulos ausentes em blocos

---

## 0. ACHADO BLOQUEANTE (ler primeiro)

> **Os arquivos-fonte do EA não existem neste repositório.**

Verificação executada:

```bash
find . -path ./venv -prune -o -type f \( -name "*.mq5" -o -name "*.mqh" \) -print
# → 0 resultados
ls MQL5/        # → só contém MQL5/Files/Data (runtime)
```

Conteúdo real de `MQL5/`:

- `MQL5/Files/Data/dataset.csv` (15.656 bytes, UTF-16 LE, 71 linhas)
- `MQL5/Files/Data/prediction.json` (133 bytes)

**Implicações:**

1. Os 8 arquivos listados no `XAU_AI_PRO_CONTEXTO.md` (`Config.mqh`, `SignalCore.mqh`, `DecisionEngine.mqh`, `ValidationEngine.mqh`, `ExecutionEngine.mqh`, `RiskEngine.mqh`, `PositionManager.mqh`, `TradePipeline.mqh`, `AIEngine.mqh`, `AIConnector.mqh`, `DataLogger.mqh`) **não estão versionados**.
2. Os documentos de auditoria anteriores (`Docs/AUDITORIA_V1.0.md`, `Docs/CORRECOES_APLICADAS.md`, `AUDITORIA_CONCLUIDA.md`) descrevem um código que **não pode ser inspecionado nem compilado** a partir do estado atual do repositório.
3. A frase "EA compila" só é verificável quando o código voltar a existir.

**Decisão para o plano:** tratar a Etapa 1 como **diagnóstico do que existe** e abrir a Etapa 2 imediatamente, **reescrevendo em blocos** o Core/IA MQL5 contra os requisitos do contexto, sem tentar patchar um código que não está sob nosso controle. Auditoria real só será possível na Etapa 2, com o código restaurado.

---

## 1. Inventário do que existe

### 1.1. Estrutura

```
C:\Users\Micro\Downloads\XAU_AI_PRO\
├── AUDITORIA_CONCLUIDA.md         ← desatualizado (ref. código inexistente)
├── BEM_VINDO.md
├── Docs\                          ← docs de auditoria antigos
│   ├── ACAO_IMEDIATA.md
│   ├── AUDITORIA_V1.0.md
│   ├── CORRECOES_APLICADAS.md
│   ├── PLANO_CORRECAO.md
│   ├── REFERENCE_NOTES.md
│   ├── ROADMAP_V1.0.md
│   ├── STATUS_ATUAL.md
│   └── TROUBLESHOOTING_NEW_BROKER.md
├── Data\                          ← VAZIA
├── Logs\                          ← VAZIA
├── Models\                        ← VAZIA
├── MQL5\
│   └── Files\Data\
│       ├── dataset.csv            ← UTF-16 LE
│       └── prediction.json        ← JSON OK
├── Python\
│   ├── main.py
│   ├── train.py
│   ├── predict.py
│   ├── ai\__init__.py
│   ├── ai\export_prediction.py
│   ├── ai\feature_engineering.py  ← VAZIO
│   ├── ai\predict_engine.py
│   ├── ai\predict_model.py
│   ├── ai\train_model.py          ← NÃO usado pelo main.py (código legado)
│   ├── data\__init__.py
│   ├── data\data_engine.py        ← wrapper fino sobre data_engine_xau
│   ├── data\data_engine_xau.py
│   ├── data\data_pipeline.py      ← NÃO usado pelo main.py
│   └── oracleJdk-26\…             ← irrelevante, deve sair
├── Reports\                       ← VAZIA
├── Backups\                       ← VAZIA
├── report.20260728.*.json         ← dump OOM do Node/Copilot, NÃO é relatório de trade
├── original_main.py               ← vazio (0 bytes)
├── _tmp_check.py                  ← "Intentionally left blank"
├── requirements.txt
└── venv\
```

### 1.2. `prediction.json` (formato vigente, gerado pelo `predict.py`)

```json
{
  "symbol": "XAUUSDc",
  "signal": "SELL",
  "price": 4077.934,
  "buy": 17.0,
  "sell": 83.0,
  "score": 83.0
}
```

### 1.3. `dataset.csv` (UTF-16 LE, 71 linhas)

Cabeçalho: `Time, Symbol, Open, High, Low, Close, Volume, Spread, ATR, ADX, RSI`

Símbolos presentes:

| Símbolo    | Linhas válidas |
|------------|---------------:|
| XAUUSD     | 26             |
| BTCUSDc    | 38             |
| BTCJPYm    | 1              |
| BTCUSDm    | 2              |
| XAUUSDc    | 2              |
| EURUSD     | 2              |
| **(total)** | **71**        |

Período: **2026-07-13 01:00 → 2026-07-21 21:30** (≈ 8 dias).

Faixa de preço XAUUSD observada: **Open min 3979.24, Close min 3991.24, Close max 4084.29, High max 4103.13** (compatível com XAUUSD em julho/2026).

Linha corrompida detectada (`MQL5/Files/Data/dataset.csv` linha 3 do arquivo UTF-16): `2.46,34.18` — resíduo de uma linha EURUSD mal fatiada. Bug do logger MQL5 (não do Python).

### 1.4. `model.pkl` (gerado por `train.py`)

- Existe em `Python/model.pkl` (193.417 bytes, 30/07 22:22).
- É o único "modelo" versionado. `Models/` está vazio.

---

## 2. Auditoria do Python (único módulo auditável de fato)

### 2.1. `Python/main.py`

- CLI mínimo: `python main.py [train|predict|help]`.
- Faz `sys.path.append(BASE_DIR)` e importa `train` / `predict` por nome de módulo (não pacote), portanto **só funciona se executado de dentro de `Python/`**. Executar da raiz quebra (`ModuleNotFoundError`).
- Sem `__main__` guard em `train.py` / `predict.py` que impeça execução direta — ok.

### 2.2. `Python/train.py` (canônico, usado pelo `main.py`)

**Pontos fortes:**

- Lê `dataset.csv` cru, decodifica como **UTF-16** e descarta a primeira linha quebrada (`next(... line.startswith("2026"))`). Robusto contra o BOM e contra a linha residual de EURUSD.
- Filtra símbolo por prefixo `XAUUSD` (cobre `XAUUSD`, `XAUUSDc`, `XAUUSDm`, etc.). **Mas não cobre `XAUUSD.pro`** (note o ponto) — `startswith("XAUUSD")` aceita, ok. Falso positivo: qualquer símbolo que comece com "XAUUSD" (ex.: `XAUUSDTEST`) entraria. Aceitável.
- Cria target `Target = (Close.shift(-1) > Close).astype(int)` (direção da próxima vela).
- Split **temporal** (`shuffle=False`) — correto.
- `RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)`.
- Salva em `Python/model.pkl` via joblib.

**Problemas:**

- **Não normaliza features.** RandomForest não exige, mas ATR/Volume/Spread têm ordens de grandeza muito diferentes — desempenho e interpretabilidade ruins.
- **Não há validação temporal explícita** (TimeSeriesSplit / walk-forward). Split único 80/20 em 26 amostras vira 20/6 — **conjunto de teste tem 6 candles**. Acurácia reportada é estatisticamente insignificante.
- **Não calcula métricas de classe** (precision/recall/F1) nem matriz de confusão. Só `accuracy_score`.
- **Não há feature importance** nem persistência de metadata (lista de features, versão, timestamp). `predict.py` redeclara a lista de features — qualquer divergência futura quebra o pipeline em produção sem erro claro.
- **`shuffle=False` no split** com 26 amostras, em dados que o próprio usuário descreveu como "ruins" (drawdown alto), é um problema: o último candle (que é justamente o que vai para produção) pode estar em período degenerado.

### 2.3. `Python/predict.py` (canônico)

- Carrega modelo + última linha de XAUUSD, gera `prediction.json`.
- Filtro de símbolo por prefixo `XAUUSD` (igual a `train.py`).
- Hard-coda o nome do `OUTPUT_PATH` em `MQL5/Files/Data/prediction.json`. **Não é configurável** sem editar fonte.

**Problemas:**

- **`build_result` mapeia errado `buy`/`sell`.** Olhando `predict_engine.py`:

  ```python
  sell = float(probabilities[0])   # classe 0
  buy  = float(probabilities[1])   # classe 1
  ```

  e o target é `(Close.shift(-1) > Close).astype(int)`, ou seja, **classe 1 = sobe**. Ok, `buy=prob[1]` é coerente. Mas o JSON de exemplo que está em `MQL5/Files/Data/prediction.json` mostra `signal=SELL, buy=17, sell=83` — coerente (classe 0 dominante, classe 1 minoritária). **Não há bug aqui** — só é frágil a mudanças de versão do sklearn, que pode inverter a ordem das classes.
- **Não trata modelo ausente com fallback** — `load_model()` lança `FileNotFoundError` e mata o EA inteiro do lado Python.
- **Não há lock/concorrência** entre `train.py` rodando e o EA lendo `prediction.json`. Em prática, irrelevante em desktop; vira problema quando virar serviço.

### 2.4. `Python/ai/predict_engine.py`

- Implementa `build_result`. Pequeno, legível, sem bugs.
- `score = max(buy, sell) * 100` — **score é a confiança do modelo**, não a força do sinal. O EA não pode usar isso como se fosse score técnico. Documentar.

### 2.5. `Python/ai/predict_model.py`

- Protocol/typing bem feito, `load_model()` com `cast`. OK.
- `MODEL_PATH = BASE_DIR.parent / "model.pkl"` — coloca o modelo **fora** do pacote `ai/`, em `Python/model.pkl`. Consistente com `train.py`.

### 2.6. `Python/ai/feature_engineering.py` → **VAZIO**. Remover ou preencher.

### 2.7. `Python/ai/train_model.py` → **NÃO é usado pelo `main.py`**. É código legado de uma fase anterior. **Remover** para não confundir.

### 2.8. `Python/ai/export_prediction.py` → também **não referenciado**. Remover ou integrar.

### 2.9. `Python/data/data_engine_xau.py`

- Lê com `encoding="utf-16"` e trata BOM. OK.
- Filtra `Symbol == "XAUUSD"` **exato** — perde `XAUUSDc` (que existe no CSV e é o símbolo do `prediction.json`). **Inconsistência grave com `predict.py` / `train.py`**, que usam `startswith("XAUUSD")`.
- Filtro `Open > 1000` e `dropna`. OK para XAUUSD (preço > 1000), mas **vai derrubar qualquer ativo futuro** (EURUSD≈1.14, BTCJPYm, etc.).
- `data_engine.py` é wrapper; `data_pipeline.py` é uma DSL fluente não usada.

### 2.10. `requirements.txt` (raiz)

- Falta `joblib`? Listado. Falta `scikit-learn`? Listado. OK.
- Falta **nenhuma** dependência usada em código. OK.

### 2.11. Resumo de problemas — Python

| # | Severidade | Onde | Problema |
|---|---|---|---|
| PY-1 | 🔴 Crítico | `train.py` | Dataset com 26 amostras de XAUUSD → modelo sem significância estatística. Precisa de meses de dados. |
| PY-2 | 🔴 Crítico | `data_engine_xau.py` | Filtro `Symbol == "XAUUSD"` perde `XAUUSDc` e é divergente de `train.py`/`predict.py`. |
| PY-3 | 🟠 Grave | `train.py` | Não persiste metadata do modelo (features, versão, data). Pipeline fica frágil. |
| PY-4 | 🟠 Grave | `train.py` | Sem validação temporal (walk-forward). Métrica reportada não é confiável. |
| PY-5 | 🟠 Grave | `predict.py` | `OUTPUT_PATH` hard-coded em caminho Windows. Sem fallback se modelo/dataset sumir. |
| PY-6 | 🟡 Moderado | repo | `feature_engineering.py` vazio, `train_model.py`/`data_pipeline.py`/`export_prediction.py` órfãos. |
| PY-7 | 🟡 Moderado | `train.py` | Encoding do dataset é tratado no Python; **deve ser corrigido no logger MQL5** (linha residual `2.46,34.18` mostra que o CSV é escrito linha-a-linha com fatiamento errado). |

---

## 3. Auditoria MQL5 (Core, IA) — INVIÁVEL

Não há fontes. As referências em `Docs/AUDITORIA_V1.0.md` e `PLANO_CORRECAO.md` descrevem um código que **não pode ser lido nem compilado** a partir do estado atual. As métricas de Win Rate, Profit Factor, Drawdown, Expectancy, R:R, horários e número de trades **não podem ser extraídas** porque:

- `Reports/`, `Logs/`, `Data/` (na raiz) estão **vazios**.
- Não há backtest, `.set` files, nem export do Strategy Tester.
- O único `report.*.json` na raiz é um dump OOM do Copilot (Node.js), não do MT5.

A auditoria MQL5 real **só volta a ser possível depois que os módulos forem restaurados/reescritos** (Etapa 2).

---

## 4. Métricas que NÃO conseguimos medir hoje

| Métrica | Por que não dá |
|---|---|
| Win Rate | Sem histórico de ordens |
| Profit Factor | Sem histórico de ordens |
| Drawdown | Sem histórico de ordens |
| Expectancy | Sem histórico de ordens |
| R:R médio | Sem histórico de ordens |
| Horários de operação | Sem histórico de ordens |
| Nº de trades | Sem histórico de ordens |

O **único sinal quantitativo** disponível hoje é o `prediction.json` atual: `SELL, score=83`, com classe 1 (buy) em 17% — modelo tomado de 26 amostras, **sem valor estatístico**.

---

## 5. Conclusão da Etapa 1

**Diagnóstico honesto:**

1. O Python está funcional mas com bugs que limitam a qualidade do modelo e a cobertura multi-símbolo.
2. O **EA MQL5 simplesmente não está no repositório**. A Etapa 1 não pode auditar o que não existe.
3. Não há dados de performance para medir.

**Implicação para o plano da V1.0:**

A metodologia combinada ("não enviaremos um arquivo por vez, vamos revisar o projeto em blocos completos") é exatamente o caminho certo, mas precisa começar **reconstruindo o EA** — não há código para "padronizar". A Etapa 1 termina aqui; **a Etapa 2 (Python) e a reescrita do EA precisam acontecer em paralelo** (Python refatorado + MQL5 reescrito em blocos).

**Ordem proposta (revisão do plano):**

1. **Etapa 2A — Refatorar Python em um bloco** (consolidar `train`, `predict`, `data_engine`, remover órfãos, persistir metadata, encoding correto).
2. **Etapa 2B — Reescrever EA MQL5 em blocos** (Core inteiro → depois IA/DataLogger), com a arquitetura alvo derivada do contexto.
3. Só então **Etapa 3 (risco)**, **Etapa 4 (IA influente)**, **Etapa 5 (testes)** fazem sentido.

**Antes de prosseguir, preciso da sua decisão sobre o item 0** (código MQL5 ausente). Três caminhos:

- **(a)** Você tem o código em outro lugar (backup, MetaTrader instalado, worktree) e cola/anexa aqui para a gente auditar antes de mexer.
- **(b)** Seguimos direto para a **reescrita** do EA em blocos contra os requisitos, tratando o que está em `Docs/` apenas como referência histórica (não canônica).
- **(c)** Trabalho híbrido: eu reescrevo o **Python primeiro** (Etapa 2A), você cola o **MQL5** em paralelo, e a gente integra.

Recomendo **(c)**: minimiza retrabalho e destrava a auditoria real do MQL5 assim que o código aparecer.
