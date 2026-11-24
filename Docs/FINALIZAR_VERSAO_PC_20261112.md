# FINALIZAR VERSÃO PC — app XAU AI PRO (12/11/2026, sessão CMD)

> Para **ALFA** e **DELTA**. Documento partilhado: quem executar cada item
> apaga-o DEPOIS, ou acrescenta ofecho — não rescrevam por cima. Trabalho
> entre os três agentes: **não commitar por conta de outros**.

## Estado medido (não suposto)

- App desktop instalado: **1.2.181** (`%LOCALAPPDATA%\XAU AI PRO\`). Atalho OK. Sonda:
  arranca, `xau-ai-pro-core` sobe, sidecar `mt5-gateway` sobe em 9011.
  **WS Online · MT5 conectado · 3 posições EA abertas.**
- Source no disco: `Files\XAU_AI_PRO` (VERSION 1.2.181) — inclui todas as correções
  das sessões anteriores (fallback público **declarado**, OHLC no cabeçalho, etc.).
- **vitest: 1006 passed (82 ficheiros).** **tsc --noEmit: exit 0.** **vite build: exit 0.**
- Backend Python no venv do projeto funciona: `_universal_candles('mt5','metals','XAUUSD','M1',3)`
  devolve 10 candles reais (~3907, MT5 vivo). O problema NÃO é MT5 nem Python.

## O BUG (confirmado em teste, dois lados)

**Sintoma no app (captura 22:40):** aba ROBÔ → GRÁFICO AO VIVO, XAUUSD M1:

```
M1 · Abr 3.917,60089766 · Máx igual · Mín igual · Fecha igual
· yahoo · dados públicos (sem execução)
```
eixo de preço desenhando a mesma série pública (3916 flat no último candle).

**Cadeia:**
1. `OperacaoAutomatica.tsx` → `market = mercadoDaFicha ?? auto?.market ?? marketSalvo ?? ''`
   — `mercadoDoAtivo(assetClass)` traduz `'metal'`→`'metals'` (correto), **mas**
   quando a ficha ainda não chegou ou `auto.market` vem singular (`'metal'`),
   o frontend manda `market=metal`.
2. `marketApi.ts`: `normalizeMarketSource('mt5','metal')` → **null** → `getCandles`
   LANCA (razão correta, mas o cavalo já tropeçou).
3. Se chegar no backend com qualquer `market` fora de `MT5_MARKETS`
   (`broker_registry.py:22` — `"metals"` plural), `normalize_read_scope`
   levanta `ValueError("mercado não suportado para mt5")`.
4. `fastapi_gateway.universal_candles` → `_read_exception_response(... candles=[] ...)`
   → resposta **sem velas** com fallback publico (`_com_fallback_publico` →
   `mercado_publico._yahoo`) → **yahoo GC=F M1 ~3916, último candle plano
   (Abr=Máx=Mín=Fecha=3916.0)** — exatamente o que a tela mostra.
   ⚠️ Alias FM: o MT5 está **vivo e com os dados** — o fallback para yahoo está
   a servir dado público STALE declarado como opção apenas sem corretora.

**Root cause:** aliasing singular↔plural de classe de mercado divergiu entre
motor (`auto_engine`/EA, singular) e gateway/frontend (plural). O backend
`normalize_market` (`broker_registry.py:75`) aceita só "metals" — **não mapeia
`'metal'` → `'metals'`** como `mercadoDoAtivo` faz no frontend.

## O que falta para "PC pronto" (ordem sugerida)

### 1. CMD — fix de aliasing (FEITO e medido, 12/11 22:50)
- `normalize_market`: adicionados `'metal'`→`'metals'`, `'index'`→`'indices'`,
  `'indice'`, `'stock'`/`'equity'`→`'stocks'`, `'commodity'`→`'commodities'`,
  `'bond'`→`'bonds'`, `'titulo'`.
- Provas: `normalize_read_scope('mt5','metal','XAUUSD')` → `market: 'metals'` ✓;
  `_universal_candles('mt5','metal','XAUUSD','M1',3)` → **10 candles reais MT5**,
  `fallback_publico: None` ✓ (antes: ValueError → yahoo plano).
- **As 4 falhas** em `test_candles_publicos_sem_conta.py`
  (`test_candles_mexc_saem_sem_credencial`, `test_candles_binance_saem_sem_credencial`,
  `test_exchange_vazia_cai_no_publico_e_declara`, `test_exchange_que_explode_nao_derruba_a_rota`)
  **não são minhas** — são do rename para "só MT5 ativo" (commit `e0e899d0`,
  mexc/binance agora `code_only`). Os testes ainda esperam candles crus de
  exchanges removidas. **Ação do ALFA/DELTA:** decidir — atualizar os testes para
  o contrato novo (exchange `code_only` → candles vazios + motivo
  "corretora não suportada") ou reverter a decisão. Não resolver em silêncio.
- **NÃO** tocar em `broker_registry.py` sem alinhar com o CMD (agora com aliasing).

### 2. ALFA — frontend
- `OperacaoAutomatica.tsx`: `market` com `mercadoDoAtivo` **primeiro** (ficha →
  class) e **nunca** singular sem traduzir: se chegar `'metal'`, normalizar para
  `'metals'` antes de passar ao `PriceChart`. Garantir que o denominador
  `normalizeMarketSource` recebe sempre plural.
- Verificar por que, na captura, `velasPublicas=true` apareceu com WS ON —
  depois do fix backend, confirmar `fonteVelas` = `'MT5'` no RN/arremesso.
- Testes: `AcompanharModelos.grafico.test.tsx` + `OperacaoAutomatica` (se existir):
  caso "ficha ainda não chegou" não mostra yahoo; mostra skeleton/erro honesto.

### 3. DELTA — validação ponta a ponta + rebuild
- Rodar o app **instalado** após novo build (ver 5) e confirmar na aba ROBÔ:
  - cabeçalho **sem** `Abr=Máx=Mín=Fecha` planos;
  - `Candles OHLC reais · MT5` (ou equivalente), **não** yahoo;
  - sinais do modelo e linhas TP/SL nas posições abertas (AUDUSD, GBPUSD, USDCAD).
- Se ainda cair em yahoo, colher `gateway_autostart.log` e `Logs/` no momento.

### 4. AMBOS — higiene PC antes de build (regra desta sessão)
- Disco: **8,3 GB livres** (medido). Build Tauri precisa ~1–2 GB — OK.
- `npm run typecheck` (exit 0 hoje), `npm test` (1006 ok), `npm run build` (exit 0),
  depois `tauri build` (o que for o script do projeto — conferir
  `build_validacao.cmd` / `installer\` para NSIS).
- **NÃO** `git add -A`; o repo tem WIP alheio (`Python/data_engine_xau.py`,
  `scripts/treinar_ia.py`, `Python/models_rebuild/`).

### 5. Build + instalação + docs
- Rebuild NSIS da versão PC → instalar → verificar no app instalado
  (capture com `PrintWindow` ou `UIA` — o app instalado responde a UIA).
- Atualizar `README.md` (versão/changelog), `Docs/STATUS_ATUAL.md` e
  `Docs/INDICE.md` com o que foi medido e como reproduzir.
- Atualizar `CHANGELOG.md` (entrada desta correção).

## Limites honestos
- O fallback público **existe por decisão do dono** (gráfico vivo sem corretora)
  e está DECLARADO na tela. O fix é para o MT5 **vivo** nunca cair nele: teste
  com MT5 aberto deve dar MT5; com MT5 fechado, yahoo rotulado como
  `dados públicos (sem execução)` — nunca velas planas sem aviso (se a última
  vela for degenerada, mostrar `—` no OHLC, não `3.917,60089766`).
- Android é **depois**; este doc é PC.

## 6. Build bloqueado por infra (CMD, resolvido 12/11 23:25)

O build parou no passo `[5/7] Compilando gateway Python`:

```
FileNotFoundError: ...MQL5\Files\Temp\py311\python.exe
```

Causa: `.venv\pyvenv.cfg` apontava `home`/`executable`/`base-executable` para
`Files\Temp\py311\python.exe` — a distribuição embutida perdeu o `python.exe`
(só restam `.pyd`/`.dll`). O venv funciona (ele mesmo é a cópia), mas o
PyInstaller segue o cfg e morre.

Correção aplicada pelo CMD: `.venv\pyvenv.cfg` redirecionado para
`.venv\Scripts\python.exe` (backup em `.venv\pyvenv.cfg.bak_20261112`).
**Isto é crítico**: sem o cfg apontando para um python.exe existente, todo
build futuro morre no passo 5. Se o ALFA/DELTA recriarem o venv, o pyvenv.cfg
volta ao padrão — verificarem.

Nota: o PyInstaller do passo `[5/7]` **exige** `frontend\src-tauri\Python\models`
já preenchido — ele corre ANTES do passo `[6/7]` (robocopy) que o popula.
Se essa pasta estiver vazia (como estava em 12/11, junto com o build quebrado),
todo build morre com `ERROR: Unable to find ... Python\models`. Pré-preencher
uma vez com:

```powershell
robocopy Python\models frontend\src-tauri\Python\models /E /XD _backup* /XF *.tmp
```

(é idempotente e não apaga nada — usado assim, igual ao passo 6/7).

## 7. Estado 13/11 00:40 (CMD) — o que está feito e o que não

Feito pelo CMD nesta sessão:
- `backend/broker_registry.py`: aliasing singular→plural (`metal`→`metals`,
  `index`, `stock`/`equity`, `commodity`, `bond`, …). Prova:
  `_universal_candles('mt5','metal','XAUUSD','M1')` → 10 candles MT5 reais,
  `fallback_publico: None`. **O gateway embutido no bundle tem esse fix desde
  a reconstrução de 23:09** (DELTA).
- `DeclaracoesConfianca.tsx`: email `rickjax1234@gmail.com`, build line
  (`Build: XAU AI PRO v{APP_VERSION} · Windows · <conta>`), `/api/health`
  com estado honesto quando o token não passa.
- `SeletorModelo.tsx`: **fix do "mapa não aparece"** — modelos de classe
  (`MULTI_*`) não entram nas opções de `Par para operar`; estado persistido
  com nome de classe de modelo devolve `''` (rejeitado como par). Medido:
  erro na tela era `Gráfico indisponível: nenhuma fonte publica respondeu
  para MULTI_METALS M5 (...)`; causa = motor configurado com o modelo de
  classe como se fosse ativo.
- `.venv/pyvenv.cfg` redirecionado (build voltou ao passo 5).
- Docs: CHANGELOG (nova entrada), README 1.2.9→1.2.181, FINALIZAR (este doc).
- Testes após meus fixies: **1018 passed, 1 flaky falha (testa verde na
  corrida seguinte)** — o floppy é desse spec (`charts-BvswnGBj.js`?) rever.
  `tsc --noEmit` exit 0.
- Bump de versão feito por OUTRO agente: 1.2.181 → 1.2.182 → 1.2.183
  (manifestos inclui VERSION, package.json, Cargo.toml, tauri.conf.json).

NÃO está feito:
- **Instalador 1.2.183**: a build do outro agente (`tauri:build --bundles nsis`)
  estava a correr às 00:29-… — aguardar; ela também falha no MSI anterior
  por colisão de target (os error 32). NSIS era o entregável.
- **App instalado = 1.2.182 sem os meus fixies** (DeclaracoesConfianca,
  SeletorModelo). Reinstalar depois que o instalador 1.2.183 sair.
- `Docs/STATUS_ATUAL.md` (DELTA atualizou para 1.2.182/12-11 23:45) —
  desatualizado se sai o 1.2.183.
- Working tree sujo multiagente; nada commitado (D-3 intacto).

## Contato
CMD (esta sessão, 12/11). ALFA e DELTA decidem a divisão e reportam aqui EMPENHO
(não sobrescreverem) o resultado medido.

**Medições-chave para copiar:** `vitest 1006/1006 · tsc 0 · vite build 0 ·
_universal_candles('mt5','metals') ok · yahoo M1 flat 3916.0 diagnóstico`.

---

## ALFA — lado FRONTEND fechado, com prova por mutação (12/11/2026, 23:05)

> Acrescentado por ALFA (append, o resto do doc está intacto). Medições abaixo
> são de comando, não de leitura de código.

### O que mudou (7 ficheiros, todos em `frontend/`)

| Ficheiro | Mudança | Porquê |
|---|---|---|
| `frontend/src/lib/mercadoCanonico.ts` | **NOVO** — tabela única de nomes de mercado + `mercadoCanonico()` | espelha `normalize_market` (gateway) e `mercado_do_ativo` (motor); terceiro lado da paridade do §5 |
| `frontend/src/lib/mercadoCanonico.test.ts` | **NOVO** — 5 testes | mede a tabela contra o consumidor REAL (`normalizeMarketSource`), não repete a tabela |
| `frontend/src/components/AcompanharModelos.tsx` | import + arg do `useCatalogoAtivos` e `market` derivado passam por `mercadoCanonico` | é o componente que desenha o gráfico da aba ROBÔ (`RobotTabs.tsx:148`) |
| `frontend/src/components/OperacaoAutomatica.tsx` | import + arg do catálogo + `market` derivado | mesma cadeia na aba de operação |
| `frontend/src/components/charts/PriceChart.tsx` | `mercadoParaConsulta` canoniza em vez de só `trim()` | último portão antes de `normalizeMarketSource` — cobre todo chamador, presente e futuro |
| `frontend/src/components/charts/PriceChart.regras.test.ts` | +2 testes | prova o portão e a recusa de nome desconhecido |
| `frontend/src/components/AcompanharModelos.grafico.test.tsx` | mock de `useCatalogoAtivos` passa a **registar o `market` de cada render** (`estado.escoposCatalogo`) + 2 testes | antes o teste só via o sintoma a jusante; agora mede o elo que estava quebrado |

### Medido antes → depois

| Medida | Antes | Depois |
|---|---|---|
| `npx tsc --noEmit` | exit 0 | **exit 0** (sem saída) |
| `npx vitest run` (suíte inteira) | 1006 passed / 82 ficheiros | **1015 passed / 83 ficheiros** (+9 testes, +1 ficheiro) |
| `npx vitest run` só nos 3 ficheiros do alvo | — | **3 passed / 57 passed** (4,84 s) |

### Provei que o teste não é decorativo (§6) — duas mutações

Mutação 1 — `AcompanharModelos.tsx:294` revertida para
`String(auto?.market || '').toLowerCase(),`:

```
× PROVA: `auto.market = metal` vira `metals` no pedido dos candles
AssertionError: expected [ 'metal', 'metal' ] to not include 'metal'
   1006|     expect(estado.escoposCatalogo).not.toContain('metal');
Tests  1 failed | 1 passed | 28 skipped (30)
```

Mutação 2 — `AcompanharModelos.tsx:336` revertida para
`String(mercadoDaFicha ?? auto?.market ?? '').toLowerCase();`:

```
× PROVA: ficha AINDA NAO CHEGOU — o pedido e da CORRETORA, nunca do publico
AssertionError: expected 'metal' to be 'metals' // Object.is equality
   1035|     expect(estado.pedidos[0].market).toBe('metals');
Tests  1 failed | 1 passed | 28 skipped (30)
```

Restaurado a seguir (backup em `Files\Temp\AcompanharModelos.fix.bak`), e
`findstr` confirma 294 `mercadoCanonico(auto?.market),` e 336
`const market = mercadoCanonico(mercadoDaFicha ?? auto?.market ?? '');`
— depois disso, verde outra vez.

**Achado da mutação 2, medido:** com `market = 'metal'` o componente **ainda
emite** o pedido com `metal` (`estado.pedidos[0].market === 'metal'`) e
`every(p => p.market !== 'livre')` **passa**. Ou seja: `metal` não vira
`livre` por renomeação — quem recusa é `normalizeMarketSource`, a montante do
HTTP. A rota LIVRE da captura das 22:40 vem de `market === ''`, não de
`metal`. Está registado assim para ninguém procurar o defeito no sítio errado.

### O que NÃO fiz (e porquê)

- **Não toquei** em `backend/broker_registry.py` (é do CMD; está `M` no git e
  li o diff — 9 linhas de aliasing, medidas com `normalize_read_scope` e
  `_universal_candles`).
- **Não commitei nada.** `git status --porcelain` nos caminhos do alvo:
  `M broker_registry.py` (CMD), `M version.ts` (não é meu), os 5 meus `M`,
  e `?? lib/mercadoCanonico.ts` / `?? lib/mercadoCanonico.test.ts`.
- **Não instalei nem recompilei** o app — é do DELTA.
- Não decidi os 4 testes de `tests/test_candles_publicos_sem_conta.py`
  (mexc/binance `code_only`) — ver abaixo.

### Para DELTA (app instalado) e para o dono

1. Instalar o build novo e capturar a aba ROBÔ: o cabeçalho **não** pode ter
   `Abr = Máx = Mín = Fecha`; a fonte tem de dizer `MT5`, não `yahoo`; e a
   linha de TP/SL tem de aparecer nas 3 posições abertas (AUDUSD, GBPUSD,
   USDCAD). Se ainda cair no público, guardar `gateway_autostart.log` e
   `Logs/` no momento — o texto do erro diz qual portão recusou.
2. **Decisão pendente (ALFA/DELTA), 4 testes vermelhos** em
   `tests/test_candles_publicos_sem_conta.py` — herança do commit "só MT5
   ativo" (`test_candles_mexc_saem_sem_credencial`,
   `test_candles_binance_saem_sem_credencial`,
   `test_exchange_vazia_cai_no_publico_e_declara`,
   `test_exchange_que_explode_nao_derruba_a_rota`). Actualizar ao contrato
   novo (exchange `code_only` → velas vazias + motivo "corretora não
   suportada") **ou** reverter a decisão. Não se resolve em silêncio (§6.2).
3. O fallback público continua **por decisão do dono** e declarado na tela.
   O fix serve para o MT5 vivo nunca cair nele.

---

## ALFA — P1.3623 fechada pela opcao (a), com prova por mutacao (12/11/2026, 23:20)

**Decisao executada:** a do dono, "P1.3623: recomendado" = (a) atualizar os testes ao contrato novo.

**Primeiro, a correcao da minha propria premissa** (estava escrita nesta doc e na P1.3623): `mexc` e `binance` NAO passaram a `code_only`. Medido:

```
READ_BROKERS  ['mt5']            CODE_ONLY_BROKERS  []
read_brokers() ['mt5']           code_only_brokers() []
BROKERS  mt5 -> active | binance, mexc, bybit, okx, bitget, coinbase, kraken, kucoin -> planned
```

Portanto a recusa que os testes recebem e `canonical_unavailable(reason='corretora não suportada')` (HTTP 501), nao `_unsupported_read_response` ("esta em code_only"). Dois motivos diferentes, e o motivo e o que o operador le.

**Contrato medido** (`_universal_candles`, 23:14):

| chamada | resposta |
|---|---|
| `('mexc','crypto-spot','BTCUSDT','M15',5)` | `ok False`, `status unsupported`, `candles []`, `count 0`, `error 'corretora não suportada'`, `source 'universal_gateway'`, sem `fallback_publico`, HTTP 501 |
| `('mt5','metals','XAUUSD','M1',3)` | `ok True`, `status ok`, `source 'mt5_gateway'`, 3 velas reais |
| `('mt5','metals','','M15',5)` | `ValueError('symbol é obrigatório')` |

**Ficheiro reescrito:** `tests/test_candles_publicos_sem_conta.py`. Antes `4 failed, 2 passed in 0.97s`; **depois `16 passed in 0.84s`**. Backup em `Files\Temp\test_candles_publicos_sem_conta.bak_20261112.py`.

Os quatro nomes que descreviam o contrato morto saíram com ele. Entraram, entre outros, dois que antes nao existiam:
- `test_mt5_com_vela_entrega_a_vela_da_corretora_e_nao_encosta_no_publico` — a **regressao do bug das 22:40**: com o publico armado para explodir, se a vela da corretora for descartada o teste reprova;
- `test_mt5_sem_vela_cai_no_publico_e_declara` — a decisao do dono de 12/10 continua provada: o fallback vive, e so no ramo do `mt5`, declarado (`execucao is False`).

**Prova negativa (AGENTS.md 6), duas mutacoes no codigo de PRODUCAO, revertidas e provadas por MD5:**

1. `READ_BROKERS` alargado para `{"mt5","mexc","binance"}` (a reversao da decisao "so MT5 ativo") -> `AssertionError: corretora fora de READ_BROKERS instanciou cliente de exchange: broker=mexc ...` / `1 failed, 13 passed`.
2. `_com_fallback_publico` com o `return` inicial desligado -> `NaoDeviaChamar: MT5 entregou vela e o publico foi chamado mesmo assim` / `1 failed, 15 passed`.

Restauro: `certutil -hashfile backend\mt5_gateway.py MD5` -> `6674edce39f2bf03157b7c7583e71003` (igual ao de antes), `backend\mt5_gateway.py` ausente de `git status --porcelain`, `findstr MUTACAO` -> nada.

**Tres achados para quem mexer nisto depois:**

1. Parametrizacao derivada da mesma fonte que mede fica **cega** quando a fonte se move: com a mutacao 1, `PLANEJADAS` recalculou, `mexc`/`binance` saíram dela e o teste parametrizado continuou verde. Quem reprovou foi o caso FIXO do `mexc`. Os dois existem por isso.
2. `except Exception` em `_com_fallback_publico` **engole a prova negativa**: um duble que levantasse `AssertionError` seria comido em silencio. O duble levanta `NaoDeviaChamar(BaseException)` de proposito.
3. `_exchange_client` tem mapa fixo de 4 exchanges (`binance`, `mexc`, `bybit`, `okx`) e `LookupError` para o resto: alargar `READ_BROKERS` sem alargar esse mapa troca uma recusa com motivo por uma excecao.

**NAO fiz:** nao toquei em `backend/broker_registry.py` (CMD) nem deixei alteracao em `backend/mt5_gateway.py`; nenhuma trava afrouxada; nenhum `xfail`/`skip`; nenhum commit.

### ATENCAO — estado medido da conta MUDOU durante este ciclo (23:16 local)

`get_trading_open_positions` -> **8 posicoes abertas**, nao 3:

| ticket | simbolo | lado | volume | aberta | SL | TP | motivo | lucro |
|---|---|---|---|---|---|---|---|---|
| 11377687783 | GBPUSD | sell | 0.13 | 21:26:59 | 1.32802 | 1.31074 | Expert | -6.37 |
| 11379736620 | USDCAD | buy | 0.22 | 03:01:44 | 1.42282 | 1.42747 | Expert | -2.62 |
| 11379812300 | AUDUSD | sell | 0.21 | 03:07:46 | 0.68380 | 0.67480 | Expert | -10.29 |
| 11380534170 | XAUUSD | buy | 0.01 | 04:06:58 | **sem SL** | 3913.56 | Mobile | -1.01 |
| 11380601488 | XAUUSD | buy | 0.01 | 04:14:55 | **sem SL** | 3913.02 | Mobile | -0.25 |
| 11380607962 | XAUUSD | buy | 0.01 | 04:15:24 | **sem SL** | 3911.55 | Mobile | +1.03 |
| 11380610665 | XAUUSD | buy | 0.01 | 04:15:37 | **sem SL** | 3911.43 | Mobile | +1.13 |
| 11380615024 | XAUUSD | buy | 0.01 | 04:16:01 | **sem SL** | 3911.35 | Mobile | +1.84 |

As XAUUSD nao sao do EA (magic `2026001`, comment `XAU_AI_PRO`); sao `reason: Mobile`, comment vazio, **sem stop loss**, abertas entre 23:06 e 23:16 local. Nao mexi em nenhuma — nao e a minha lane e nao ha ordem para isso. Duas consequencias medidas:
- o motor vai recusar por `max_posicoes = 2` com 8 posicoes abertas (o bloqueio previsto no STATUS_ATUAL agora e 4x maior);
- a validacao do DELTA "TP/SL visiveis nas 3 posicoes abertas" passou a ser "8 posicoes, 5 delas sem SL".

---

## ALFA — verificacao do ciclo, com o numero honesto da suite (12/11/2026, 23:38)

**A minha lane, medida agora:** `pytest -q tests\test_candles_publicos_sem_conta.py` -> **16 passed in 0.28s** (antes do P1.3623: `4 failed, 2 passed`). Frontend, os 3 arquivos que eu toquei -> **Test Files 3 passed (3) / Tests 57 passed (57)** em 5.26s (`mercadoCanonico.test.ts`, `AcompanharModelos.grafico.test.tsx`, `PriceChart.regras.test.ts`). `backend\mt5_gateway.py` continua `6674edce39f2bf03157b7c7583e71003` e ausente do `git status`. Sem `xfail`, sem `skip`. Nada commitado.

**A suite inteira, medida e NAO verde — e importante que ninguem leia "verde" amanha:**

```
pytest -q tests                     -> 6 errors during collection (todos ModuleNotFoundError: No module named 'tkinter')
pytest -q tests --ignore=<os 6>     -> 28 failed, 1493 passed, 8 skipped, 2 errors in 333.76s
```

Nenhuma das 28 e regressao deste ciclo, e isso esta provado sem stash: `backend/mt5_gateway.py` nao aparece em `git status` (e byte-identico ao HEAD) e as nove linhas de `status` do `backend/broker_registry.py` sao **iguais no HEAD e no worktree** — `mt5`=`active`, e `binance/mexc/bybit/okx/bitget/coinbase/kraken/kucoin`=`planned` ja no HEAD.

**Classificacao (28 falhas + 2 erros = 30 pontos):**

| Causa | Onde | Pontos | Dono |
|---|---|---|---|
| Contrato antigo de corretora (a mesma decisao "so MT5" que o P1.3623 corrigiu num arquivo so) | `test_connection_contract` (8), `test_gateway_endpoints` (4), `test_universal_account` (3), `test_auto_engine` (4), `test_auto_escolher_modelo` (1), `test_trading_mcp_market` (1) | **21** | CMD |
| `tkinter` ausente no `.venv` | 6 modulos nao coletam + `test_tabs_regression` (2 erros) + `test_app_core` (2) | 10 | CMD/DONO |
| `dist\mt5-gateway` a meio | `test_spec_gateway::test_bundle_pyinstaller_tem_os_modelos` | 1 | DELTA |
| versao do app (1.2.182) x versao do EA (1.2.210) | `test_versao_consistente` | 2 | DELTA/CMD |
| nome/motivo do modelo de classe `MULTI_*` | `test_ai_inference` | 2 | quem publica os modelos |

**DOIS AVISOS QUE VALEM ANTES DE GERAR O INSTALADOR:**

1. **`dist\mt5-gateway` esta castrado.** `dir /b dist\mt5-gateway` devolve **so** `_internal`; dentro, so `yaml` e `yarl`; `mt5-gateway.exe` -> `EXE_AUSENTE`; nenhum `MULTI_*.pkl`; mtime 23:04:50. Gerar o NSIS deste estado produz um instalador **sem gateway e sem modelos**, e a tela instalada diria "modelos nao carregam" sem excecao em lugar nenhum. Ordem segura: `scripts\build_app.bat` ate ao fim -> `scripts\medir_artefato_gateway.py` exit 0 -> **so depois** o NSIS.
2. **A versao mudou DEBAIXO da medicao.** O `pytest` leu `#property "1.391"` e `EA_VERSION_STRING "1.2.191"`; minutos depois a leitura da `"1.410"` e `"1.2.210"`, enquanto `sync_version.py --check` diz `Todos alinhados` nos 9 portadores do app em **1.2.182**. Quem medir versao aqui tem de repetir a leitura e dizer a hora.

Detalhe completo em `MQL5\Experts\XAU_AI_PRO\PENDENCIAS.md`: **P1.3626** (tkinter), **P1.3627** (as 21), **P1.3628** (os dois avisos). Nenhum arquivo de outro dono foi tocado.

## DELTA — 13/11/2026 01:05 — versao PC 1.2.183 construida, medida e fechada ate onde o repositorio alcanca

**Estado medido agora (nao suposto):**

- `npx vitest run`: **83 ficheiros / 1019 testes verdes** (`VITEST_EXIT=0`, 668 s) e
  `npx tsc --noEmit`: `TSC_EXIT=0`. Corridos **depois** da edicao do ALFA em `SeletorModelo.tsx`
  (00:04:45) — a corrida anterior (1014/1019) era snapshot a meio, nao defeito.
- `pytest -q tests/test_candles_publicos_sem_conta.py`: **16 passed** — as 4 falhas herdadas de
  "so MT5 ativo" estao fechadas no working tree.
- `pytest -q tests/test_spec_gateway.py tests/test_versao_consistente.py`: **19 passed, 2 failed**
  (as 2 estao em "aberto" abaixo; `test_spec_gateway` passou).
- Bateria do artefacto (`scripts/medir_artefato_gateway.py --exe Temp\dist-gw\mt5-gateway\mt5-gateway.exe`):
  **exit 0** — `gateway_build=xau-ai-pro-1.2.183-universal-20261113`, 5 rotas `401` sem token,
  `401` com token errado, `withdrawals_enabled=False`, `transfers_enabled=False`, ordem
  `execute=false` -> `stage=validated`.
- **O binario medido e o binario empacotado:** `SHA256(Temp\dist-gw\mt5-gateway.exe) ==
  SHA256(frontend\src-tauri\bridge\mt5-gateway.exe)` = `B786CAD4C8912862D78A9764FC67ED0A4B38E29E8AD7ADCB67B37C6C1A73230A`.
- Bundle NSIS: `XAU AI PRO_1.2.183_x64-setup.exe`, **142 102 924 B**, SHA256
  `EEB57D996A9A5F9A47FC3EA1D29277BB9B9EF31CF536EE4E94594CFECC4D5AAD`, `TAURI_EXIT=0`;
  `XAU AI PRO.exe` 13 998 080 B com FileVersion e ProductVersion `1.2.183`.
- **O NSIS leva gateway e modelos** (o aviso 1 do ALFA nao se aplica a este bundle): `resources`
  do `tauri.conf.json` e `bridge/**/*`, e o `bridge` tem `mt5-gateway.exe` 28 759 944 B (00:26:07),
  `_internal` com **3497** ficheiros e **8 `.pkl` + 8 `.meta.json`** em `_internal\Python\models`
  (`MULTI_METALS.pkl` 47 605 777 B, `MULTI_FIAT.pkl` 64 522 465 B, `MULTI_CRYPTO.pkl` 70 286 993 B
  e mais 5). 484 MB no bridge, comprimidos no NSIS. O `dist\mt5-gateway` tambem ja tem o exe +
  3498 ficheiros (hash `3D1149…` — build anterior, 23:58:36; o empacotado e o das 00:26:07).

**Causa real do "Grafico indisponivel" (fechada nesta versao, com prova):** o simbolo pedido ao
grafico era o **nome do modelo** (`MULTI_METALS`, do `MULTI_METALS.meta.json`), nao um par.
`ListaModelos.escolher` gravava-o em `selectedSymbol` e em `/api/auto/config`. Correcao em tres
portoes com a mesma guarda `ehClasseDeModelo()`: escrita (`ListaModelos`), leitura (`parNaTela`,
que tambem limpa o `localStorage` persistido) e seleccao (`SeletorModelo`). Provas:
`classe_de('MULTI_METALS')=OUTROS`, `simbolo_valido('MULTI_METALS')=False`,
`_tentativas_multi('MULTI_METALS','M5')=[]`, `_tentativas_multi('XAUUSD','M5')` ->
`MULTI_METALS_M5`; `_universal_candles('mt5','metals','XAUUSD')` -> `count=10`,
`fallback_publico=None`, ultima vela O 3.918,76 / H 3.921,40 / L 3.917,63 / C 3.919,43; e
`MULTI_METALS` -> `ok=False, count=0` (recusa com motivo, nunca dado falso).

**Corrida do MSI:** `light.exe` escreveu `output.wixpdb` e **nunca criou `output.msi`** (ficou
parado 20 min, CPU congelada). A corrida foi terminada e o NSIS reconstruido com
`npm run tauri:build -- --bundles nsis`, que e o entregavel. O MSI continua sem completar.

**ABERTO — precisa de decisao do dono, nao resolvido em silencio:**

1. **DUAS COPIAS DO EA DIVERGEM, e uma tem dois dias.** A copia do REPOSITORIO
   (`Files\XAU_AI_PRO\MQL5\Experts\XAU_AI_PRO\XAU_AI_PRO.mq5`, 104 834 B, 10/11 04:38) diz
   `#property version "1.391"` e `EA_VERSION_STRING "1.2.191"`; a copia do TERMINAL, que e a que
   compila e corre (113 779 B, 12/11 17:36), diz `"1.410"` e `"1.2.210"`. O
   `test_versao_consistente.py` le a copia do repositorio, logo mede 1.391/1.2.191 contra
   `VERSION="1.2.183"`. Sincronizar a copia do repositorio NAO fecha o teste — so mudaria os
   numeros para 1.410/1.2.210 —, porque o teste exige que o EA acompanhe a versao da APP
   (`aceitos = ['1.2.183','1.2183','1.383']`). Decisao: **qual linhagem manda?** (a) a app sobe
   para `1.2.210` e o EA fica; (b) o EA desce para `1.2.183`/`1.383` (exige recompilar no
   MetaEditor e **reanexar os 15 graficos**, o que derruba o bit de negociacao com posicoes
   abertas); (c) o teste passa a comparar so as fontes do EA entre si. Nao toquei em nenhum
   `.mq5`/`.mqh`.
2. **Instalacao do NSIS:** nao executada — escreve em `%LOCALAPPDATA%\XAU AI PRO` e em
   `Program Files`, fora das raizes autorizadas do terminal. Acao do dono. Depois de instalar,
   o `%LOCALAPPDATA%\XAU AI PRO\bridge` deve ser apagado antes (AGENTS.md 7), senao o NSIS nao
   substitui binario com o mesmo numero de versao e o app roda com bridge velha.
3. **A IA da frota em 9027** e servida pelo Python do repo arrancado as 13:01:04 de 12/11, com o
   `broker_registry.py` anterior ao fix de aliasing. So muda com reinicio do processo, e reiniciar
   com posicoes abertas exige ordem do dono.
