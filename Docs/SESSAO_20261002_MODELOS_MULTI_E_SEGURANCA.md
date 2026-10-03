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

### 2.2b Uma linha com data no ano 1 matava o treino do FIAT

Este e o defeito mais caro do ciclo, e ele **nao aparecia em lugar nenhum**: o
processo nao travava por falta de memoria, ele morria com `ArrayMemoryError` e
a causa real estava tres camadas acima.

```
Time cru: '4 13:05:00'   ->  pandas parseia: 0001-01-04 13:05:00
```

**1 linha em 49.365.** Uma so. E ela estraga o reamostramento inteiro porque
`resample()` usa o **span** entre `min` e `max` para criar os bins: de 1 ate
2026 dao 2.025 anos, e um bin por minuto disso sao **71.028.348 linhas** — o
numero exato da mensagem de erro.

Tres hipoteses erradas antes da causa:

| Hipotese | Por que estava errada |
|---|---|
| "Falta de memoria" | Era, mas nao por acumulo. `gc.collect()` nao mudou nada — mesmo 542 MiB, mesmo 71028348. |
| "O `replace([inf,-inf], nan)` copia a base" | Custo real, mas nao a causa do estouro. |
| "O encoding do dataset esta errado" | O `detectar_encoding` errava mesmo (ver 2.2c), mas corrigido o encoding os anos continuavam em 1 — **o defeito era o dado, nao a leitura.** |

Encadeamento:

```
1 linha '4 13:05:00' -> parse: 0001-01-04 -> min() = ano 1
                     -> resample cria 1 bin por minuto do span
                     -> 71.028.348 linhas -> ArrayMemoryError: 542 MiB
```

Corrigido em `_descartar_timestamps_impossiveis`: janela 1990-2035 aplicada
**na carga**, com o numero de descartadas impresso no log. Foram **18 linhas em
676.732** (0,00003%). Os edges melhoraram depois disso: FIAT +0,185 e METALS
+0,250, contra +0,057 e +0,063 na rodada que sofria do defeito.

### 2.2c O `detectar_encoding` errava em arquivo sem BOM

`dataset_limpo.csv` e **UTF-8 COM BOM** (`EF BB BF`) e `dataset.csv` e
**UTF-16 LE** (`FF FE`) — medidos em byte. A heuristica antiga contava bytes
nulos em posicao impar, o que so distingue UTF-16 de ASCII: nos arquivos ja
limpos ela declarava UTF-16 sem ser.

Agora: BOM manda; sem BOM, a **tentativa de decodificar** e a prova (o primeiro
campo de um CSV de mercado comeca com data).
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

### 7.1 Um erro meu que custou um build inteiro

O primeiro `build_app.bat` desta sessao **falhou na etapa [7/7]**. A causa nao
foi falta de espaco, como o log sugeria:

```
error: proc macro panicked
  --> src\main.rs:957:14
   |
957 |         .run(tauri::generate_context!())
   = help: message: The `frontendDist` configuration is set to
          `"../dist"` but this path doesn't exist
```

**Eu tinha apagado `frontend/dist` na limpeza para liberar espaco**, achando
que era cache regeneravel. O `tauri.conf.json` aponta `frontendDist` para
`../dist`, entao o build morre no `generate_context!()`.

Duas leituras erradas minhas no mesmo minuto, que valem registrar:

| O que eu fiz | Por que errou |
|---|---|
| Apaguei `frontend/dist` para liberar disco | `frontendDist` do Tauri le essa pasta. **Nao e cache: e entrada do build.** |
| Quase apaguei `dist/mt5-gateway` achando que era redundante | o `robocopy` do passo [6/7] põe o exe em `bridge/mt5-gateway.exe` (raiz), nao em `bridge/mt5-gateway/`. **Verifiquei antes de apagar.** |

O que salvou o segundo foi ter conferido `Test-Path
'frontend\src-tauri\bridge\mt5-gateway.exe'` antes do `Remove-Item`. Um `-Force`
sem verificacao teria custado os 3 modelos e o gateway inteiro, e o build
ainda teria passado adiante.

**A regra:** antes de apagar algo grande durante um build, confirmar que o
build ja copiou para o destino final. Cache que o build ainda vai ler nao e
cache.
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