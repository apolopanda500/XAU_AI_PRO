# Sessão 02/10/2026 — Modelos MULTI, segurança e o bundle do instalador

> **Por que este documento existe.** O ciclo foi longo e cheio de achados que
> só apareceram na medicao. Este arquivo e o mapa para nao repetir o caminho:
> o que foi pedido, o que foi medido, o que era defeito e o que era erro meu.

---

## 1. O que foi pedido (na ordem em que chegou)

| # | Pedido | Onde ficou |
|---|---|---|
| 1 | VIP com metas: operou volume **ou** comprou US$ 100 | `backend/metas_vip.py` + `backend/acesso.py` |
| 2 | Free **nunca** usa multi; PRO usa | `_PLAN_CATALOG["free"]` + `acesso.pode_usar_multi_modelo()` |
| 3 | Nenhum ativo/corretora fixo em código | `backend/exchange_symbols.py`, `asset_classes.py` |
| 4 | Um modelo MULTI por classe, **todos os timeframes** | `Python/ai/train_multi.py` |
| 5 | Nomes de modelo limpos, sem `_H1` na tela | `ai_inference.rotulo_modelo()` |
| 6 | Corretoras com pares normalizados (USDT/USDC/USD) | `backend/exchange_symbols.py` |
| 7 | Credenciais limpas, projeto seguro | `.gitignore` + 3 workflows com gitleaks |
| 8 | Testes + validação final + commit/push | `829 passed`, `8c5f197` |

---

## 2. Os 4 defeitos que a medicao revelou

Nenhum destes era visivel lendo o codigo. Todos apareceram por medir.

### 2.1 O instalador sairia SEM os 3 modelos MULTI

O `mt5-gateway.spec` empacotava apenas `Docs/version.json`. Os `.pkl` sao
carregados por `ai_inference` com `joblib.load` em tempo de execucao — e o
PyInstaller so enxerga **modulo importado**. Um arquivo aberto por caminho ele
nao inclui.

**Sintoma no app instalado:** "modelos nao carregam". **Sem excecao em lugar
nenhum** — o build passava limpo.

A correcao tem dois caminhos e **o segundo e o que quebrava**:

| Caminho | Existe? | Contem MULTI? |
|---|---|---|
| `Python/models` (raiz) | sim, 72 arquivos | **nao** |
| `frontend/src-tauri/Python/models` | sim | **sim, os 3** |

`train_multi.MODELOS_DIR` (linha 79) publica na **segunda**. Apontar o `.spec`
para a primeira compilaria sem erro e entregaria um instalador vazio de
modelos — exatamente o defeito que se queria corrigir.

**Travado por 3 testes** em `tests/test_spec_gateway.py`: a pasta precisa estar
em `datas`, a origem precisa existir e ter `.pkl`, e o destino precisa bater com
o que `ai_inference._resolver_modelos()` resolve.

### 2.2 O dataset estava sendo lido errado (UTF-16 LE)

`dataset_legacy` e **UTF-16 LE**. Lido como UTF-8, cada caractere vinha com
`\x00`: `AUDUSD` virava `" A U D U S D "`. A auditoria acusava "193 simbolos"
cheios de lixo e **0 linhas uteis**.

### 2.3 Features nao estacionarias tornam MULTI impossivel

`FEATURES` comeca com preco absoluto. XAUUSD ≈ 2000, EURUSD ≈ 1,08. Um modelo
treinado no ouro **recebe entrada 2000x maior** no forex — nao e impreciso, e
sem sentido estatistico.

`Python/ai/features_estacionarias.py` normaliza as 5 absolutas
(`Close/ATR`, `Volume/Volume_MA`, `Spread/ATR_Pct` + retornos log) e adiciona
`Timeframe_Cod` + `Classe_Cod`, o que habilita o **MULTI multi-timeframe** —
um artefato opera M1→H4 porque o timeframe e feature, nao pasta.

Prova: o mesmo padrao de candle em ouro, euro e bitcoin gera **features
identicas**.

Dois bugs apareceram na medicao: `KCI_VD/Close` dava 1,66 no ouro e 3080 no
euro; `KCI_VD/ATR` dava 12,5 contra 23.148. `KCI_VD` ja e invariante — foi
renomeado para `KCI_VD_Inv`.

### 2.4 Teste que dependia do disco local

`test_acesso_bloqueia_multi_no_free` chamava `pode_usar_multi_modelo()` sem
contexto e esperava `False`. Na maquina onde rodei ha `vips` gravado em
`subscriptions.json` → `True`. Na maquina do dono daria `free` → `False`.

**Passaria numa maquina e falharia na outra.** E a assinatura dos 4 falsos
positivos do forward test de 01/10. O codigo de producao estava certo; o
defeito era o teste. Agora injeta o Free explicitamente via `monkeypatch`.

---

## 3. Os 3 modelos publicados

| Modelo | Simbolos | Edge | Folds | Estavel |
|---|---|---|---|---|
| `MULTI_CRYPTO` | BTC, DOGE, ETH, SOL, XRP | **+0,0594** | 5/5 positivos | sim |
| `MULTI_FIAT` | 10 pares | **+0,0566** | 5/5 | sim |
| `MULTI_METALS` | XAU, XAG | **+0,0626** | 5/5 | sim |

Todos com `publicable=true`, `live_execution=false`, `withdrawals_enabled=false`.
Folds em **expanding window** (`train` cresce de fold em fold) — sem isso o
walk-forward testaria no passado e o edge seria mentira.

---

## 4. Seguranca — o que foi medido

**Nenhuma credencial estava exposta.** Isso foi verificado, nao assumido:

| Verificacao | Resultado |
|---|---|
| `.env`, `.env.local`, `.env.mexc.local`, `.env.binance.local` | todos ignorados |
| Historico completo (`git log --all`) | so `.env.example` foi commitado |
| Segredos em codigo rastreado | nenhum (so SHA-256 e hash de commit) |

**Correcoes aplicadas:**

1. **`.gitignore`** — a regra generica `.env*` vinha depois das especificas e
   engolia os `.example`. Sem `!.env*.example`, un `git clone` novo nao traria
   o `.env.example`.
2. **gitleaks em 3 workflows que nao tinham** — `build-installer.yml` (embala o
   instalador do usuario), `ci.yml` (todo push) e `pylint.yml`. Com
   `fetch-depth: 0`, sem o qual o gitleaks so ve o ultimo commit.

---

## 5. O que ficou em aberto, e por que

### 5.1 Execucao real nao esta aplicada

O dono pediu "Opcao A" (liberar ordem real). A medicao mostrou que **a flag
nao e o interruptor**:

```rust
main.rs:644  →  flag("XAU_ENABLE_REAL_ORDERS","0")  // SÓ ESCREVE UM LOG
```

E `_trade_order` (gateway) ja vem com `XAU_ENABLE_TRADE_COMMANDS` padrao `"1"`
— o caminho de ordem **ja esta aberto**. Alem disso, `main.rs:433` usa
`std::env::var` e **nao le arquivo `.env` nenhum**: a flag so vem de variavel
de ambiente do Windows.

**O que decide ordem real e a conta no MetaTrader 5, hoje `MetaQuotes-DEMO`.**

⚠️ Ligar a flag agora produziria um log dizendo "ordens reais habilitadas" sem
que nada mude — e isso e pior que nao fazer, porque o log passaria a mentir.

### 5.2 Super-Linter continua vermelho

`validate` e `security` verdes; so `quality` reprova, com 34 linters que o
projeto nao configurou (`PYTHON_RUFF` 342 avisos, `BIOME_FORMAT` 200). Nao foi
desligado: escolher quais linters o projeto usa e decisao do dono, e desligar
so para pintar o CI de verde seria esconder defeito.

---

## 6. Estado ao fim do ciclo

| Camada | Resultado |
|---|---|
| pytest | **829 passed** |
| vitest | **189 passed** |
| tsc --noEmit | exit 0 |
| eslint | exit 0 |
| preflight | EXIT=0 |
| MQL5 | intacto |

Commits: `003060f` (ci/seguranca) · `8c5f197` (bundle + governanca MULTI).
GitHub e GitLab sincronizados em `8c5f197`.

---

## 7. Os 3 arquivos que mentem quando o build passa

Toda perda de ciclo veio daqui, nao do codigo estar errado:

1. **`.spec` sem `datas`** — compila limpo e entrega instalador sem modelo
2. **`.env` nao lido** — a flag no arquivo nao faz nada
3. **teste lendo disco local** — verde numa maquina, vermelho na outra

A regra que daqui pra frente: **medir o artefato final, nao o codigo que o
gera.**
**Nomes limpos, sem sufixo de timeframe:** `MULTI_CRYPTO`, nao
`MULTI_CRYPTO_H1`. E o que o dono pediu — um artefato, todos os horarios.

⚠️ **Limite declarado:** o gate exige 5.000 linhas por simbolo. `XAGUSD` (945)
e `USDBRL` (194) ficam fora por volume insuficiente. `INDICES` nao tem dado
nenhum — ficou registrado como pendencia, nao inventado.
| | Antes (leitura errada) | Depois |
|---|---|---|
| Linhas | 0 | **676.732** |
| Simbolos | 0 | **17** |

O CSV tambem tem **11 campos, nao 15**. O filtro de largura descartava tudo —
da a leitura "sem dados" com 85 MB na mesa.