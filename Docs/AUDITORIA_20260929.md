# XAU AI PRO — Auditoria e Correcao 2026-09-29

**Data:** 2026-09-29 · **Branch:** `develop` · **Versao:** 1.2.4
**Escopo:** auditoria do catalogo de IA, do backtester, das travas de seguranca
e do ciclo de build.

---

## 1. Resumo executivo

A auditoria encontrou **tres defeitos reais**, todos com impacto em decisao de
trading, e **um quarto que era divergencia entre documento e codigo**.

| #   | Defeito                                                         | Gravidade | Estado      |
| --- | --------------------------------------------------------------- | --------- | ----------- |
| 1   | `pipeline.py` legado apagava a porta de qualidade do `train_v2` | **Alta**  | Corrigido   |
| 2   | Backtester decidia por heuristica, nao pelo modelo              | **Alta**  | Corrigido   |
| 3   | Teste do backtest aceitava zero trades                          | **Alta**  | Corrigido   |
| 4   | `XAU_ENABLE_REAL_ORDERS=1` hardcoded no Tauri                   | **Media** | Documentado |

Nenhuma rotina de saque ou transferencia foi habilitada. A trava permanece.

---

## 2. Defeito 1 — o catalogo de modelos perdia a governanca

### Sintoma

`pytest` falhava em 2 testes, e o `STATUS.json` afirmava `600/600`:

```
tests/test_ai_inference.py::test_listar_modelos_traz_metricos_reais
  → assert m["edge_min"] is not None        →  assert None is not None
tests/test_ai_inference.py::test_modelo_reprovado_expoe_o_motivo
  → AUDUSD_M5 reprovado sem motivo registrado → assert ''
```

### Causa raiz

Existem **dois escritores** de `Python/models/*.meta.json` disputando o mesmo
arquivo:

| Escritor                                             | Campos que grava                                                     | Quem consome                 |
| ---------------------------------------------------- | -------------------------------------------------------------------- | ---------------------------- |
| `Python/ai/train_v2.py`, via `scripts/treinar_ia.py` | `min_edge`, `publicable`, `publish_reason`, `feature_hash`, `folds`  | `backend/ai_inference.py`    |
| `Python/pipeline.py:429` (ETAPA 15.3, legado)        | `dataset_version`, `model_version` — **sem os campos de governanca** | MQL5 (`ModelGovernance.mqh`) |

`Python/auto_retrain.py:33` chama `Pipeline` do legado. O retreino automatico
reescreveu por cima os metadados governados de 6 simbolos forex:

```
AUDUSD_M5, EURUSD_M5, GBPUSD_M5, NZDUSD_M5, USDCAD_M5, USDJPY_M5
train_date = 2026-09-29T12:00 UTC  (todos no mesmo minuto)
```

### Risco

`publicable` desaparecendo faz a tela tratar um modelo **reprovado** como
publicavel, e o `edge_min` sumindo remove da interface o piso de edge. O `.pkl`
legado nunca passou pela porta de edge; sobrepor o arquivo sob um nome aprovado
e a forma de publicar um modelo reprovado.

### Correcao

- `Python/pipeline.py`: nova `preservar_governanca()` mantem os campos do
  `train_v2` como fonte da verdade e so acrescenta os do legado. O `.pkl`
  legado tambem nao substitui o modelo governado, e o log avisa.
- Os 6 metadados foram regenerados com `scripts/treinar_ia.py`.

---

## 3. Defeito 2 — o backtester media uma estrategia que nao existe

### Sintoma

`backend/backtest.py:101` decidia compra e venda assim:

```python
direction = "buy" if rsi[index] < 35 and crossover_up else "sell" if rsi[index] > 65 and crossover_down else None
```

O arquivo **nao tinha nenhuma referencia** a `pkl`, `pickle`, `joblib` ou
carregamento de modelo. A tela de backtest mostrava o desempenho de uma regra
RSI/MACD local, que nao e a IA que opera a conta.

### Correcao

- `backend/backtest.py`: nova `_decisao_do_modelo()` carrega o mesmo `.pkl`
  publicado que `backend/ai_inference.py` usa ao vivo, pelas mesmas features e
  na mesma ordem do treino.
- O resultado declara a procedencia: `decision_source` (`model` ou
  `indisponivel`), `model`, `feature_hash`, `measured` e `reason`.
- **Sem modelo publicado, o backtest nao inventa sinal**: devolve zero trades
  com o motivo, em vez de uma curva que parece desempenho.
- O deslocamento de warm-up e publicado em `warmup_offset`, para o sinal do
  modelo cair no candle certo.
- `backend/fastapi_gateway.py`: o endpoint passa `symbol` e `timeframe` ao
  backtester, que antes ignorava o par pedido.

### Por que isso importa para o operador

Sem `decision_source`, uma tela com curva e numero era lida como desempenho do
modelo. Agora a interface consegue dizer: mediu o modelo, ou nao mediu nada.

---

## 4. Defeito 3 — o teste do backtest aceitava um backtest morto

`tests/test_backtest.py` verificava `ok`, `candles`, `equity_curve` e
`max_drawdown`. **Nunca `trade_count` nem `win_rate_pct`.** Um backtest que nao
abre posicao passava como saudavel, porque nao fazia nada.

### Correcao

O arquivo passou de 4 para 11 testes. O bloco novo cobre:

- a procedencia da decisao esta declarada;
- sem modelo publicado nao ha trade e o motivo esta escrito;
- com sinal do modelo existe trade, e ele carrega a confianca real;
- o resultado registra **qual artefato decidiu** e o hash das features;
- um modelo que responde NEUTRAL em toda a serie e distinguivel de "nao ha
  modelo" — as duas situacoes nao podem aparecer iguais na tela;
- o par pedido chega ao carregador do modelo.

---

## 5. Defeito 4 — divergencia entre documento e codigo

`Docs/ESTADO_E_PENDENCIAS.md` afirma que `XAU_ENABLE_REAL_ORDERS=0`. O codigo
faz o contrario: `frontend/src-tauri/src/main.rs:437` injeta
`.env("XAU_ENABLE_REAL_ORDERS", "1")` no gateway a cada spawn, sem passar pelo
ambiente. O valor real nao e auditavel por quem opera.

Verificacao: `XAU_ENABLE_REAL_ORDERS` tem **1 unica ocorrencia** em todo o
repositorio, em codigo compilado.

---

## 6. O que foi verificado e esta correto

| Item                           | Como provar                                                          | Resultado                |
| ------------------------------ | -------------------------------------------------------------------- | ------------------------ |
| Trava de saque e transferencia | 18+ ocorrencias de `withdrawals_enabled: False` / `transfers: False` | **Intacta**              |
| `.env` fora do git             | `git ls-files`                                                       | **So `.env.example`**    |
| MQL5 intocado                  | `git status --porcelain MQL5`                                        | **Vazio**                |
| Python                         | `pytest -q tests`                                                    | **619 passed, 0 failed** |
| TypeScript                     | `npx tsc --noEmit`                                                   | **exit 0**               |
| Governanca do catalogo         | `scripts/auditar_governanca_modelos.py`                              | **36/36 integros**       |

### Sobre a arquitetura de IA

A pesquisa de mercado (MQL5, 21/08/2026) descreve a regra correta: _"the agent
may recommend; only deterministic code may authorize, size, and transmit an
order"_. O `risk_gate.py` e a implementacao disso. **Nao foi alterado.** A
pesquisa de ONNX (14/05/2026) indica o caminho de mercado para inferencia no
terminal; o pipeline Python + gateway do projeto e a alternativa valida para
multi-broker, e as features ja sao reproduzidas identicas ao treino.

---

## 7. Endurecimento contra regressao

O pipeline legado nao pode mais apagar a governanca. Para impedir a volta do
problema, `preservar_governanca()` marca o arquivo preservado com
`governado_por: train_v2` e `pipeline_sem_autorizacao: true`, e emite warning
explicito no log.

**Regra operacional que emerge disto:** nao rode `Python/auto_retrain.py` para
publicar modelos. Ele nao passa pela porta de edge. Para treinar e publicar, use
`scripts/treinar_ia.py`, que e o unico caminho com governanca.

---

## 8. Pendencias que exigem decisao do proprietario

1. **Marca de dinheiro real**: o `AGENTS.md` exige validacao completa em DEMO,
   forward test aprovado e endurance test. Nenhum existe. A infraestrutura para
   automatizar isso esta sendo preparada, com o interruptor desligado.
2. **Credencial real**: hoje a conta e `MetaQuotes-DEMO`. Execucao real exige
   credencial real, separada.
3. **`XAU_ENABLE_REAL_ORDERS`**: mover a decisao do `main.rs` para o ambiente,
   com o valor padrao `0`.

- Backup dos originais em `Python/models/_backup_legado_20260929/`.
- `tests/test_governanca_modelos.py`: 8 testes, um deles varre o catalogo real
  e falha se qualquer metadado estiver sem governanca.
- `scripts/auditar_governanca_modelos.py`: auditoria de linha de comando.

### Resultado

```
catalogo: 36 metadados | com governanca: 36 | publicaveis: 25 | reprovados: 11
Catalogo integro: todo metadado tem a porta de qualidade.
```

O retreino dos 9 simbolos em M5 rodou e **nenhum passou** na porta (edge maximo
+0.0295 contra minimo +0.0500). Esse e o resultado correto: melhor sem sinal do
que com sinal ruim. Os 25 modelos publicaveis sao de H1/H4/M15 e seguem intactos.
