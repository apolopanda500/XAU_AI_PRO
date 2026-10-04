# Levantamento 30/09/2026 — paridade entre corretoras e estado do ambiente

> Levantamento feito **antes** de mexer em comportamento. Não altera nenhuma
> rota nem trava. Registra o que foi verificado por comando, o que está
> partido e a ordem de correção proposta.
>
> **Motivo:** o dono definiu duas regras que o código não cumpre —
> _"não deixar XAUUSD em códigos como comando ou exclusivo"_ e
> _"também não colocar MT5 como comando ou exclusão; o app tem que funcionar
> para todos de forma padrão livre"_ — e pediu para juntar pendências e
> correções em etapas antes de executar.
>
> Precedente: [`SESSAO_20260930.md`](./SESSAO_20260930.md) seção 13 — _"quase
> todo bug apareceu da mesma forma: o teste passava, a tela mentia"_.

---

## 1. As duas regras, e o que já existe no projeto

A regra **já está escrita** em `app/market_symbols.py:32`:

```python
return ""  # sem ativo fixo — UI pede seleção / usa símbolo do chart MT5
```

O mesmo arquivo, docstring: _"Resolver genérico de símbolos/timeframes — sem
hardcode de ativo"_. O `backend/` descumpre essa regra em pontos que **tomam
decisão de trading**.

---

## 2. Ativo inventado (nenhum símbolo pode ser presumido)

> **Status: CORRIGIDO na Etapa 1 (30/09/2026).** A tabela abaixo registra o que
> foi encontrado; o que mudou esta em §7.

| #   | Arquivo:linha                 | Código                                                | Gravidade | Estado                  |
| --- | ----------------------------- | ----------------------------------------------------- | --------- | ----------------------- |
| A1  | `backend/ai_inference.py:184` | `str(symbol or "XAUUSD").strip().upper() or "XAUUSD"` | **Alta**  | **corrigido** (Etapa 1) |
| A2  | `backend/backtest.py:168`     | `symbol: str = "XAUUSD"`                              | Média     | **corrigido** (Etapa 1) |
| A3  | `backend/copilot_data.py:159` | `simbolos: str = "XAUUSD"`                            | Baixa     | **corrigido** (Etapa 1) |

### A1 é o achado mais grave da sessão

A docstring **imediatamente acima** (linhas 176-178) descreve este defeito como
já corrigido:

> _"O artefato é `<SIMBOLO>_<TF>` (XAUUSD_H1, BTCUSD_M15, ...). Antes o caminho
> era fixo em XAUUSD, então pedir BTCUSD devolvia o modelo de ouro — sinal de
> outro ativo apresentado como se fosse do ativo pedido."_

O caminho dos arquivos **foi** corrigido (linhas 186-187 usam `{simbolo}`).
Mas o `or "XAUUSD"` da linha 184 **ficou**. Efeito real hoje:

```
inferir("", candles, "H1")  ->  carrega XAUUSD_H1.pkl  ->  devolve sinal de OURO
```

O chamador que passa símbolo vazio recebe decisão de trading do ativo errado,
com confiança real, e nada no retorno denuncia isso.

**Por que voltou:** o mesmo padrão da seção 13 — corrigiu-se o caso visível
(o caminho) e ficou o caso silencioso (o default). É a segunda vez que este
par exato reaparece: `docs/ESTADO_E_PENDENCIAS.md` linha 36 registra
_"Inferência usava coluna `time`, features esperavam `Time`"_ no mesmo módulo.

---

## 3. Corretora fixada (MT5 como caminho exclusivo)

> **Status: CORRIGIDO nas Etapas 2, 3 e 4 (30/09/2026).** A tabela abaixo
> registra o que foi encontrado; o que mudou esta em §7.

### 3.1 O motor não usa a corretora que o operador escolhe — **CRÍTICO**

`MotorAuto` aceita, valida e **expõe** `broker` e `market`:

- `auto_engine.py:192-229` — valida contra `broker_registry` e recusa
  combinação inválida com mensagem boa.
- `auto_engine.py:164,233` — `snapshot()` e `configurar()` devolvem
  `"broker": self.broker or "mt5"`.

### 3.2 MT5 é o único que não pode ser cadastrado como conexão

`backend/connection_service.py`:

| Linha         | Código                                                                                                 | Efeito                                  |
| ------------- | ------------------------------------------------------------------------------------------------------ | --------------------------------------- |
| 17            | `if broker not in {"binance","mexc","bybit","okx"}: raise ValueError("MT5 usa a sessão do terminal…")` | MT5 é exceção, não padrão               |
| 16, 33, 39-51 | o mesmo conjunto repetido 3×; `if/elif/elif/else` escolhe o cliente                                    | 4 corretoras em código, não em catálogo |
| 34            | `if item["broker"] not in {...}: raise ValueError("Sincronize MT5 pela sessão do terminal.")`          | MT5 fora do fluxo de conexão            |

O `broker_registry` já tem 9 corretoras com capacidades declaradas. A camada
de conexão ignora o registro e mantém a lista hardcoded.

### 3.3 Defaults de corretora em leitura

| Arquivo:linha                                 | Padrão                            |
| --------------------------------------------- | --------------------------------- |
| `copilot_data.py:158,166,171,181,190,197,201` | `broker: str = "mt5"` (7 funções) |
| `fastapi_gateway.py:590,601,608,1169,1189`    | `Query(default="mt5")`            |
| `trading_mcp.py:110,114,118,128`              | `args.get("broker", "mt5")`       |

`universal_contracts.py:19` (`Broker = Literal[...]`) **não** é violação: é a
lista de corretoras do sistema.

---

## 4. O que **não** é violação (não tocar)

| Arquivo                                         | Por quê                                                                                         |
| ----------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `broker_registry.py`                            | MT5 é **uma entrada entre 9**; é o catálogo                                                     |
| `universal_contracts.py:19`                     | `Literal` = a lista de corretoras suportadas                                                    |
| `asset_registry.py`                             | lê o catálogo de símbolos **do terminal conectado**                                             |
| `market_data.py:69-98`                          | `YF_MAP`/`STOOQ_MAP`/`CATEGORY_MAP` são **tabelas de mapeamento**; XAUUSD é uma linha entre 20+ |
| `auto_engine.py:429-449` (`_trava_instrumento`) | **bloqueia** modelo de outro ativo — é a defesa, não o defeito                                  |

---

## 5. Ambiente: o disco era o bloqueio real

| Momento                              | Livre      |
| ------------------------------------ | ---------- |
| Início da sessão                     | 0,87 GB    |
| Após remover `target\debug` (3,9 GB) | **6,2 GB** |

`cargo check` falhou **duas vezes** com `Espaço insuficiente no disco (os error
112)`, antes de qualquer teste. A pendência _"Liberar espaço em disco"_ de
`SESSAO_20260930.md` §11 era **bloqueante**, não cosmética.

**ACL corrompida (recorrente).** `scripts\limpeza_segura.ps1` falhou com
_"O acesso ao caminho … foi negado"_; `docs/SESSAO_20260930.md` §8 documenta o
mesmo sintoma (_"`.git`: ACL corrompida no `.pytest_cache` travava
`git status`"_).

**Correção aplicada (Etapa 0.1):** `Resolve-Icacls()` + `try/catch` em volta
de cada remoção. Antes, o `Remove-Item` sob `$ErrorActionPreference = 'Stop'` era
erro **terminating** e abortava o lote inteiro — um alvo travado impedia todos
os outros de serem limpos. Agora o script sempre sai com `exit=0`, avisa o que
não conseguiu e segue.

**Limite honesto:** o `.pytest_cache` desta máquina **não** é recuperável sem
shell elevado — nem o dono consegue lê-lo, e `takeown` responde _"Acesso
negado"_. O `icacls` resolve ACL herdada quebrada (foi o que destravou o
`target\debug`, 3,9 GB), não esse caso. O script avisa em vez de fingir.

Mas o `_loop` (linhas 451-505) **ignora os dois**:

```python
## 6. Segunda pendência resolvida hoje: o log que mentia

`SESSAO_20260930.md` §11: *"o `mt5-gateway` caiu 2× … O log continuou dizendo
'core spawnado com sucesso' — mentira."*

Verificado em `main.rs`: o log era escrito no `.map(|child| …)` do
`Command::spawn()`, que só prova que o Windows **aceitou criar** o processo.
`OWNED_CHILDREN` guardava o `Child` e **nunca** chamava `try_wait()`.

### Sobre a causa: uma medição minha estava errada

Primeira medição: backlog 5 → 27 recusas/7,65 s; backlog 128 → 0/1,62 s.
A diferença apontava para `request_queue_size`.

**Repetida com a CPU folgada, a diferença desapareceu** — os dois cenários
deram 0 falhas, 3 vezes seguidas. As 27 recusas eram **artefato de um `cargo
check` rodando em paralelo**, ou seja, CPU saturada. O script
`scripts/provar_backlog.py` existe agora para **tentar refutar** a hipótese, e
imprime "a máquina está folgada e o experimento não diz nada" quando não
distingue — em vez de apresentar um número como prova.

O defeito real (log mentindo, sem `try_wait()`, sem supervisão) é **verificado
por leitura do código**, não por medição.

---

## 7. Etapas

Cada etapa é independente e verificável.

### Etapa 0 — Ágil — **EXECUTADA em 30/09/2026**

| # | Correção | Estado |
|---|---|---|
| 0.1 | `Resolve-Icacls()` + `try/catch` em `limpeza_segura.ps1` | **feito** — script sai `exit=0` e limpa o lote |
| 0.2 | `CARGO_TARGET_DIR` = `Temp\cargo-target` em `build_app.bat` | **feito** — destino já na allowlist e no `.gitignore` |
| 0.3 | `TestNenhumAtivoPresumido` em `test_ai_inference.py` | **4 testes, 2 falham** (travam A1) |
| 0.4 | `TestRoteamentoPorCorretora` em `test_auto_engine.py` | **4 testes, 3 falham** (travam 3.1) |

**As 5 falhas são o resultado esperado da Etapa 0.** Os testes existem para
destravar os defeitos: cada um que corrigir o código vira verde sozinho. Um
teste que passa antes da correção não provava nada.

```

FAILED test_ai_inference.py::TestNenhumAtivoPresumido::test_simbolo_vazio_nao_carrega_o_modelo_de_ouro
E assert RandomForestClassifier(...) is None
FAILED test_ai_inference.py::TestNenhumAtivoPresumido::test_simbolo_ausente_e_recusado_com_motivo
FAILED test_auto_engine.py::TestRoteamentoPorCorretora::test_loop_nao_importa_mt5_gateway_direto
FAILED test_auto_engine.py::TestRoteamentoPorCorretora::test_loop_nao_chama_trade_order_do_mt5
FAILED test_auto_engine.py::TestRoteamentoPorCorretora::test_loop_usa_o_router_universal
5 failed, 52 passed

```

A primeira falha é a prova empírica do A1: `inferir("", candles, "H1")` devolve
um `RandomForestClassifier` — **sinal de ouro para um ativo não escolhido**.

### Etapa 1 — Nenhum ativo é presumido — **EXECUTADA em 30/09/2026**

| # | Correção | Estado |
|---|---|---|
| 1.1 | `ai_inference.py`: símbolo vazio → recusa, nunca XAUUSD | **feito** — `TestNenhumAtivoPresumido` 4/4 verde |
| 1.2 | `backtest.py:168`: `symbol` obrigatório | **feito** — `test_backtest_exige_simbolo` |
| 1.3 | `copilot_data.py`: `simbolos` obrigatório | **feito** |
| 1.4 | Regra em `AGENTS.md` | **feito** (na Etapa 0) |

**Resultado: as 2 travas do ativo inventado ficaram verdes.** Restam as 3 do
roteamento, que sao da Etapa 3.

O que mudou alem do `or "XAUUSD"`:

- `inferir()` recusa símbolo vazio **antes** de reamostrar e montar as 25
  features — nao depois.
- `MOTIVO_SEM_SIMBOLO` e constante: o mesmo texto aparece em `_carregar` e em
  `inferir`, e as duas precisam concordar, senao a tela mostra um motivo e o log
  registra outro.
- `/api/ai/predict` recusa na porta, sem gastar 600 candles do MT5 para um
  simbolo inexistente.
- `leitura_do_mercado` e `relatorio_mercado` passam a exigir `broker` e
  `market`: o default `"mt5"` escolhia um par que o chamador nao pediu.

**Verificacao de que nao sobrou nenhum:**

```

Select-String -Path backend\*.py,app\*.py -Pattern 'symbol[s]?\s*[:=]\s*["'']XAUUSD|or\s+["'']XAUUSD'
ai_inference.py:198 <- comentario que documenta o bug corrigido

```

Uma unica ocorrencia, e e a frase *"2. O DEFAULT ficou. `str(symbol or "XAUUSD")`
sobreviveu ao conserto do caminho"* — o registro do que era.


### Etapa 2 — Paridade de conexão — **EXECUTADA em 30/09/2026**

| # | Correção | Estado |
|---|---|---|
| 2.1 | `connection_service` lê `broker_registry` em vez do set local | **feito** |
| 2.2 | Cliente por corretora virou registro (`CLIENTES`) | **feito** |
| 2.3 | **MT5 entra no mesmo fluxo** | **feito** |
| 2.4 | `connection_store` distingue `api_key` de `session` | **feito** |

A diferença entre MT5 e as exchanges deixou de ser um `raise` e passou a ser um
**dado**: `CORRETORA_POR_SESSAO` e `CLIENTES` declaram que a credencial vem de
lugares diferentes, e `credential_source` na resposta diz à interface o que
pedir. O `save_connection` deixou de exigir API key — gravar string vazia no
DPAPI seria mentira, e a listagem agora diz `configured: false`.

**Teste que mudou de opinião:** `test_save_rejeita_api_key_para_mt5` afirmava
`422 "não cadastre API key para MT5"`. Ele **fixava a regra antiga**. Virou
`test_mt5_entra_no_mesmo_fluxo_de_conexao`, mais dois testes novos (corretora
desconhecida, mercado incompatível).

### Etapa 3 — Motor multi-corretora — **EXECUTADA em 30/09/2026**

`backend/market_access.py` (novo) resolve `(broker, market, symbol)` em chamada
concreta. O `_loop` deixou de importar `mt5_gateway`: candles, risco e envio
passam pelo par configurado, e o envio continua sendo do `UniversalRouter` com
`intent_log`.

`snapshot()` e `configurar()` perderam o `or "mt5"`, e `ligar()` passou a exigir
corretora — sem ela, o erro só apareceria depois de inferência, risco e sizing.

**As 3 travas do roteamento ficaram verdes** (44 passed no arquivo).

Um ajuste de método: `test_loop_usa_o_router_universal` passou **por acaso**,
porque a docstring nova do `_loop` cita o código antigo. Passou a ler a AST e
ignorar docstring e comentário — um teste que varre o texto acusa a própria
evidência do bug.

### Etapa 4 — Padronização — **EXECUTADA em 30/09/2026**

| # | Correção | Estado |
|---|---|---|
| 4.1 | `copilot_data`, `fastapi_gateway`, `trading_mcp`: `broker` obrigatório | **feito** |
| 4.2 | Catálogo do MCP vem de `broker_registry` (9 corretoras) | **feito** |

`/api/market/symbols` perdeu o `broker or exchange or "mt5"` e agora responde
`400` com a lista de mercados da corretora pedida. As 7 rotas `/api/universal/*`
passaram de `Query(default="mt5")` para `Query(min_length=1)`.

### Verificacao de que nao sobrou nenhum

```

Select-String -Pattern 'or "mt5"|= "mt5"|default="mt5"|\? "mt5"'

```

Sobram **comparações** (`if broker == "mt5"`), que são legítimas — são o
código tratando MT5 como uma corretora entre outras. E a constante
`CORRETORA_POR_SESSAO = "mt5"`, que é a diferença **declarada**.

---

## 8. Trava de saque - intacta

`withdrawals_enabled` e `transfers` seguem `False`. `risk_gate.withdrawal_allowed()`
retorna `False`. Nenhuma das etapas acima habilita saque, e nenhuma toca em
`XAU_ENABLE_MT5_EXECUTION`.

---

## 9. Estado final

```

pytest 659 passed, 0 failed
vitest 169 passed (19 arquivos)
tsc exit 0
build exit 0
saque 0 violacoes de withdrawals_enabled/transfers
segredos 0 bloqueios
MQL5 intocado
disco ~0,5 GB livres (ver lição de disco abaixo)
git 20 modificados + 5 novos, nenhum commit

````

**As cinco etapas (0 a 4) estao concluidas. Zero pendencia de teste.**

O que mudou em relacao ao inicio da sessao: `inferir("", ...)` devolvia um
`RandomForestClassifier` de ouro, e o motor com `broker="binance"` enviava a
ordem para o MetaTrader. Os dois agora recusam com motivo, e a recusa acontece
antes de gastar inferencia.

`cargo test` ainda nao rodou: o `CARGO_TARGET_DIR` novo (Etapa 0.2) so entra em
vigor no proximo `build_app.bat`, e o build Rust precisa de ~4 GB.

### Licao de disco (custa tempo toda sessao)

O consumo nao e do codigo, e da **dupla build**: `target\debug` (1,6 GB) e
`target\release` (1,6 GB) coexistem, e nenhum dos dois e necessario ao mesmo
tempo. Some-se a isso o `.venv` (1,5 GB) e as duas instalacoes do app
(871 MB + 393 MB).

Sequencia pratica quando o disco aperta:

```powershell
.\scripts\limpeza_segura.ps1 -Apply -DebugCache   # cache de depuracao
Remove-Item frontend\src-tauri\target\release -Recurse -Force   # so antes de rebuild
````

O `limpeza_segura.ps1` trata `target\debug` e `Temp\cargo-target`; o
`target\release` **nao** entra na limpeza automatica porque e o diretorio de
trabalho do `tauri build` e o usuario pode querer o binario assinado que saiu
dele. A copia assinada vive em `release\<versao>\`.

def risk_state(): from backend.mt5_gateway import _risk_state, _mt5
def enviar(...): from backend.mt5_gateway import _trade_order
resposta = _mt5_candles(self.simbolo, self.timeframe, 600)

```

**Consequência:** o operador escolhe `binance`, a tela confirma `binance`, o
histórico registra `binance` — e a ordem vai para o MT5. A tela mente sobre a
corretora que está sendo operada.

Isto é a pendência *"Conectar motor ao UniversalRouter"* de
`SESSAO_20260930.md` §11, e o comentário em `auto_engine.py:122-135` afirma que
já foi resolvido:

> *"MULTI-CORRETORA (2026-09-29) … Agora `broker` e `market` são estado do
> motor, validados contra o catálogo"*

Só a **validação** foi feita. O **roteamento** não. `UniversalRouter.adapter_for`
existe e sabe escolher entre os 5 adaptadores — o motor simplesmente não o usa.

**Cobertura:** `tests/test_auto_engine.py` tem **25 testes** e **nenhum**
menciona `broker` no roteamento. O único teste de `configurar` (linha 326) é
`test_configurar_rejeita_valor_invalido`, sobre `banca: -1`.
```
