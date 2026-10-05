# PARTE 1 DA SESSAO 05/10/2026 — MEDIDO, CORRIGIDO E O QUE FALTA

> Complemento de `SESSAO_20261005_ESTADO_E_CONTINUACAO.md` (registro do inicio
> do dia). Onde os dois se contradizem, **este vence** — tudo aqui foi medido
> por comando nesta sessao.

## 0. TAREFA RECEBIDA

Dono, em ordem: (a) "casas decimais" de Configuracoes nao funciona; (b) tirar
o que e generico e as mensagens de aviso; (c) pesquisar o padrao XM Global +
MT5, app baseado nessas duas corretoras; (d) barra inferior estilo MT5 com
grafico XM Global operavel ao vivo; (e) aba Historico mostrar operacoes E
movimentacoes (deposito/saque), melhor explicado; (f) aba Sistema, melhorar;
(g) "tudo 10/10".

**NAO ENTREGUE** (secao 4): (b), (c), (d), (f) e a parte visual de (e).

## 1. O APP JA ESTAVA INSTALADO (leitura ERRADA no registro original)

O §7.5 do registro original diz que `C:\Users\Micro\AppData\Local\XAU AI PRO`
estava AUSENTE. **Esta errado.** Medido:

```
XAU AI PRO.exe   13.677.056 bytes  FileVersion 1.2.4
atalho Desktop   -> C:\Users\Micro\AppData\Local\XAU AI PRO\XAU AI PRO.exe
atalho Start Menu-> presente
Python\models    39 .pkl + 39 .meta.json (inclui os 3 MULTI_*)
bridge\          mt5-gateway.exe 34.474.525
core\            xau-ai-pro-core.exe 9.154.560
```

Reinstalar teria jogado fora uma instalacao boa. O que faltava era **subir**:
app e MT5 estavam fechados.

## 2. QUATRO DEFEITOS REAIS CORRIGIDOS (todos com prova)

### 2.1 `tests/test_mql5_compila.py` — corpo de `_compilar` colado no teste

O corpo inteiro da funcao estava duplicado dentro de
`test_log_da_compilacao_e_interpretavel`, depois dos asserts. O teste
RETORNAVA uma tupla (nao verificava nada daquela parte), rodava uma 3a
compilacao do MetaEditor (~11 s) e o pytest contava GREEN emitindo so um
`PytestReturnNotNoneWarning` no meio de 1030 pontos.

Corrigido: bloco removido (18 linhas). Medido: `1030 passed, 2 warnings ->
1030 passed, 1 warning` e `169,89s -> 138,62s`.

### 2.2 `pytest.ini` — o warning virou erro (trava)

```
filterwarnings = error::pytest.PytestReturnNotNoneWarning
```

Teste NEGATIVO da propria guarda: um teste que retorna valor agora da
`1 failed` onde antes passava. Usei `error` e nao `strict` de proposito:
`strict` promoveria tambem o `StarletteDeprecationWarning` (de
`fastapi/testclient.py`, dependencia de terceiros) e a suite reprovaria por
algo que o projeto nao controla.

### 2.3 `scripts/endurance_test.py` — dois contratos errados com o gateway

| Linha | Antes | Correto | Efeito do erro |
|---|---|---|---|
| 48 | `X-Gateway-Token` | `Authorization: Bearer` | 401 em TODA consulta |
| 79 | `/health` | `/api/health` | 404 — rota nao existe |

`mt5_gateway.py:2594-2596` aceita uma unica forma
(`auth != f"Bearer {API_TOKEN}"`), e o gateway so conhece `/` e `/api/health`
(`mt5_gateway.py:2750`). E a **5a ocorrencia** da regra do §11 do registro
original: dois lados discordando do nome do mesmo campo. O endurance test
reprovaria 100% das amostras e culparia o gateway por erro do cliente.

VALIDADO EMPIRICAMENTE contra gateway real com token conhecido:
`Authorization: Bearer` -> `True`, `gateway_build =
xau-ai-pro-1.2.4-universal-20260928`; `/health` -> `HTTP 404`; `/api/account`
-> `200`. Sem 401.


### 2.4 `backend/mt5_gateway.py` — DEPOSITO E SAQUE VIRAVAM "SELL"

O mais grave. Era um ternario de dois estados:

```python
"type": "BUY" if deal_type == getattr(mt5, "DEAL_TYPE_BUY", 0) else "SELL",
```

O MT5 tem **DEZ** tipos de deal. `BALANCE` (2) e `CREDIT` (3) — deposito,
saque, credito — caiam no `else` e voltavam como **SELL**. O frontend
desenhava uma VENDA sem simbolo, que era dinheiro entrando na conta.

MEDIDO na conta real 391773676 (XMGlobal-MT5 14), `history_deals_get` de
10 anos:

```
type=0 BUY     -> 1
type=1 SELL    -> 1
type=2 BALANCE -> 2   CD-AST-PIC 265376085 (+5,52)
                          EXP05-AST-PIC 265376085 (+0,10)
type=3 CREDIT  -> 1   Credit-In-100%-$100-NewClients (+5,62)
```

**Tres das CINCO linhas do historico da conta nao eram operacao**, e as tres
apareciam como "SELL". O `comment` da corretora e a prova de que nao eram
operacoes: nenhum desses nomes aparece numa compra ou numa venda.

Corrigido com `_TIPOS_DEAL` (0..9, medidos no pacote MetaTrader5 5.x desta
maquina), `_tipo_deal` e `_movimentacao_de`. O `type` agora e o nome
VERDADEIRO (`BALANCE`, `CREDIT`, `BONUS`, `COMMISSION`...), e cada linha
ganha `categoria` (`operacao`/`movimentacao`), `movimentacao` (`Deposito`,
`Saque`, `Credito`, `Bonus`, `Comissao`...) e `comment`.

O SENTIDO vem do VALOR, nao do tipo: `DEAL_TYPE_BALANCE` cobre deposito E
saque, e `DEAL_TYPE_CREDIT` e entrada. Medido e documentado no codigo.

Validado na conta real: 5 linhas, 2 operacao, 3 movimentacao, e
`Credit-In-100%-$100-NewClients` aparece como `Credito +5,62`.

### 2.5 `frontend/src/lib/historico.ts` — o PnL somava dinheiro recebido

`resumir()` somava TODOS os deals no resultado. Com o backend antigo, os
+11,24 de deposito e credito entravam como se fossem lucro: a aba mostrava
"+5,62 de lucro" sem nenhuma operacao correspondente. Agora `total`, `wins`,
`losses`, `winRate` e `profitFactor` consideram SO operacoes; as
movimentacoes vao para `movEntradas`/`movSaidas`, com nome proprio.

`ehMovimentacao()` usa `categoria` quando o backend enviou e cai para um
rascunho estrito (sem `symbol`, sem `volume` E sem `price`) quando nao veio.

**O RASCUNHO ESTREITO NAO E PARANOIA.** A primeira versao classificava com so
"sem simbolo" e QUEBROU 5 testes que ja existiam: eles montam deals como
`{ realizedPnl: 100 }`, sem simbolo e sem volume, e passaram a contar como
movimentacao — `resumir` devolvia 0 em vez de 825,25. O campo `realizedPnl`
so existe em EXECUCAO de ordem, e por isso hoje e o sinal mais forte: sua
presenca exclui movimentacao.

## 3. MEDICOES DE APOIO

Frontend: `235 passed` (24 arquivos), `tsc --noEmit` limpo.
Python: `1045 passed, 0 falhas` (ver secao 5).
MetaEditor: `0 errors, 0 warnings` (via `tests/test_mql5_compila.py`).

## 4. O QUE NAO FOI ENTREGUE

**(b) "tirar o generico e as mensagens de aviso"** — nao entregue. "Generico" e
"mensagens de aviso" nao tem criterio medivel no pedido. Medir exige saber
quais avisos o dono viu, e onde. **PERGUNTAR.**

**(c) padrao XM Global + MT5** — pesquisa feita, NADA implementado. Medido
de terceiros (nao do catalogo da XM): Micro e Standard compartilham a mesma
estrutura de spread e mudam so no lote minimo; Ultra Low tem spread menor
(Gold $0,32-$0,35 contra $0,56-$0,58 no Standard); Zero e quase-zero mais
comissao, so na entidade CySEC.

**ATENCAO — CONFLITA COM REGRA DO PROJETO.** `AGENTS.md`: *"Nenhuma corretora
pode ser caminho exclusivo. MT5 e uma entrada entre nove em
`backend/broker_registry.py`, nao o padrao"*, com trava em
`tests/test_auto_engine.py::TestRoteamentoPorCorretora`. Escolher XM Global
como base **reduz** as nove corretoras. Precisa de decisao explicita do dono
antes de mexer.

**(d) barra inferior estilo MT5** — nao entregue. JA EXISTE parcialmente:
`frontend/src/theme/mt5-terminal.css` (`.mt-status-strip`) e `LatenciaBar`
(rodape; o proprio codigo diz "Na MEXC e no MT5 a latencia e um item de
RODAPE"). Construir por cima disso, nao do zero.

**(f) aba Sistema** — nao entregue. `SystemHealthOnly.tsx` ja mede CPU, RAM,
disco, temperatura, GPU, latencia, com cache de modulo entre montagens.

## 5. COLISAO COM O OUTRO AGENTE — LER ANTES DE EDITAR

Esta sessao trabalhou **em paralelo** com outro agente no mesmo repositorio
(OpenCode, com modelos Space Bunny Alpha). Ele esta mexendo em:

```
backend/connection_service.py      +93
backend/fastapi_gateway.py         (alterado)
backend/audit_log.py               (alterado)
backend/vip_progress.py            (alterado)
frontend/src/components/ConnectionSettings.tsx
frontend/src/components/VipsTab.tsx + VipsTab.test.tsx
frontend/src/components/EditarConexao.tsx  (novo) + teste
frontend/src/lib/connections.ts     +52
frontend/src/hooks/useAppStore.ts   +18
frontend/src/theme/vips.css         +27
tests/test_connection_contract.py   +205   <-- arquivos DELE
tests/test_vip_progress.py          +173   <-- arquivos DELE
```

Meus arquivos (nao mexer sem reler):

```
backend/mt5_gateway.py                      <-- historico/movimentacoes
frontend/src/lib/historico.ts               <-- classificacao
frontend/src/lib/historico.test.ts
frontend/src/components/tabs/HistoryTab.tsx
tests/test_movimentacoes.py                 <-- NOVO, 13 testes
pytest.ini
scripts/endurance_test.py
tests/test_mql5_compila.py
```

### AS 2 FALHAS QUE NAO SAO MINHAS

Na suite completa aparecem:

```
FAILED tests/test_connection_contract.py::test_trocar_credencial_nao_exige_excluir_e_recriar
FAILED tests/test_connection_contract.py::test_update_nao_muda_o_mercado_da_conexao
```

Diagnostico: `assert 'api_key' not in '{"id": "mex...: "api_key"}'`. O teste
prova que a resposta da API **nao** deve conter `api_key`, mas o proprio
`payload` que ele manda tem `api_key` — o teste se auto-contcontra.

COMPROVADO que nao e interferencia minha:

```
pytest -q tests/test_connection_contract.py              -> 13 passed
pytest -q tests/test_connection_contract.py test_vip_progress.py -> 44 passed
pytest -q tests --ignore=tests/test_connection_contract.py -> 1045 passed, 0 falhas
```

Os testes dele passam ISOLADOS e falham JUNTO de outros arquivos: e estado
compartilhado entre testes, e o arquivo e dele. Nao corrigi — mexer no
trabalho do outro agente seria colidir.

## 6. APP NO AR (medido ao fim da sessao)

```
XAU AI PRO.exe   6096   Trading Desk, Responding
mt5-gateway      7364   porta 9001
xau-ai-pro-core  10160  portas 9002 + 9003
terminal64       13284  391773676 - XMGlobal-MT5 14 - [BTCUSD,M15]
EA               RUNNING, autotrading=True, balance 7,63, equity 13,25
preflight        --etapa app-rodando -> ok (1 aviso: arquivos pendentes)
```

**O GATEWAY MORRE SOZINHO.** Caiu 2x nesta sessao, sem crash no Log de
Aplicacao. E o comportamento que o §7.3 do registro original ja descreve:
"ele morre com o processo pai". Contornado reiniciando o app instalado (que
o supervisiona), nao subindo o gateway na mao.

**VAZAMENTO DE `xau-ai-pro-core` — ACHADO NOVO, NAO CORRIGIDO.** A cada
reinicio do app sobra um processo `xau-ai-pro-core` orfao. Medido ao fim da
sessao: **8 processos**, com espacamento de ~45 s (1 por reinicio), todos com
23 MB:

```
10160  06:05:26    8700  06:43:39    13352  06:44:55    2884  06:45:40
 8576  06:46:25    7648  06:47:10   15236  06:47:55    3836  06:52:43
```

As portas 9002/9003 ficam com o PID mais antigo (10160), entao o app funciona
— mas o consumo cresce a cada reinicio e ninguem ve. Causa provavel: o
supervisor mata o `XAU AI PRO.exe` e o core nao recebe o encerramento (o
mesmo caminho que derruba o gateway). **NAO INVESTIGUEI A FONTE** — e o
primeiro item a fechar quando houver um ciclo sem o outro agente mexendo.


**401 em `/api/health` E CORRETO — NAO MEXER.** O gateway exige
`Authorization: Bearer` e o Tauri injeta token POR SESSAO, que prevalece
sobre o `.env` (`_token_do_ambiente_ou_dotenv`: ambiente vence arquivo). Sem
o token da sessao, tudo 401 — fail-closed. E o comportamento correto.

**`--timeout` NAO EXISTE** no pytest deste projeto; usar `-q tests` direto.

## 7. O QUE FALTA PARA 10/10

1. Decidir o padrao XM Global + MT5 — **respeita ou revoga** a regra das
   nove corretoras? (item 4c)
2. Dizer quais "mensagens de aviso" tirar. (item 4b)
3. `build_app.bat` + `install_app.bat` para ver o Historico na tela.
4. Commitar. **NADA foi commitado** — 21 arquivos modificados no working
   tree, metade dos quais do outro agente. Commitar junto mistura os dois
   trabalhos; commit parcial e o caminho seguro.


**(e) parte visual** — backend, lib e tabelas prontos; falta rebuild e
instalador para ver na tela.


---

# PARTE 3 — AUDITORIA DE REPAROS (05/10/2026, mais tarde)

Modo reparos. Tudo abaixo medido por comando nesta rodada.

## A. ESTADO VERDE (medido)

```
Python    1113 passed, 0 falhas, 1 warning  (296,79 s)
Frontend   283 passed, 26 arquivos, 0 falhas (66,61 s)
tsc       --noEmit limpo
MetaEditor 0 erros (via tests/test_mql5_compila.py)
preflight --etapa app-rodando -> ok (1 aviso: arquivos pendentes)
```

**AS 2 FALHAS DA PARTE 1 FORAM CORRIGIDAS PELO OUTRO AGENTE.** Na Parte 1 a
suite dava `test_connection_contract.py` 2 falhas; agora `1113 passed` sem
nenhuma. Nao foi este agente: o arquivo consta como modificado no git e a
correcao nao esta em nenhum arquivo meu.

Frontend subiu de 235 para 283 testes: o outro agente criou
`src/theme/fluidness.test.ts` (16 testes) e outros.

## B. AS MINHAS 4 CORRIGIDOES SOBREVIVERAM A EDICOES PARALELAS

Reconferido campo a campo depois de o outro agente mexer nos mesmos arquivos
(`mt5_gateway.py` foi de +114 para +183 linhas de diff; `HistoryTab.tsx`, de
+159 para +369):

```
backend/mt5_gateway.py:1566  _TIPOS_DEAL
backend/mt5_gateway.py:1580  def _tipo_deal
backend/mt5_gateway.py:1588  def _movimentacao_de
backend/mt5_gateway.py:1631  "categoria": "movimentacao" if movimentacao else "operacao"
backend/mt5_gateway.py:1632  "movimentacao": movimentacao
frontend/src/lib/historico.ts:72-74   movQtd / movEntradas / movSaidas
frontend/src/lib/historico.ts:124     export function ehMovimentacao
frontend/src/lib/historico.ts:138     export function rotuloMovimentacao
pytest.ini:59-60                      filterwarnings = error::pytest.PytestReturnNotNoneWarning
scripts/endurance_test.py:61          cabecalhos = {"Authorization": f"Bearer {token}"}
scripts/endurance_test.py:84          ok, saude = _consultar("/api/health", token)
```

As edicoes dele foram ADITIVAS: nenhuma das minhas linhas sumiu, e o
`tsc --noEmit` segue limpo com o codigo dos dois.

## C. PENDENCIAS — LISTA CONSOLIDADA

### PRIORIDADE 1 — AFETA DECISAO DO OPERADOR

**P1.1. VAZAMENTO DE `xau-ai-pro-core`** (achado na Parte 1, confirmado aqui)
Cada reinicio do app deixa um processo orfao. Medido nesta rodada: **6
processos** (eram 8 antes; cairam sozinhos — o encerramento e lento, nao
imediato). 23 MB cada, ~45 s de espacamento = 1 por reinicio. As portas
9002/9003 ficam com o PID mais antigo, entao o app FUNCIONA; o crescimento e
invisivel. **NAO INVESTIGADO — causa raiz aberta.**

**P1.2. O GATEWAY E O APP MORREM SOZINHOS** (3a vez nesta sessao)
Apos ~40-60 s de o app subir, `mt5-gateway` (9001) e `XAU AI PRO.exe`
desaparecem, sem crash no Log de Aplicacao. Provavel causa comum com P1.1: o
supervisor nao encerra os filhos. Contornado reiniciando o app — **mas e um
`Stop-Process`, nao um pedido de fim pelo app. Para operar direto pelo app,
isto tem de ser resolvido.**

### PRIORIDADE 2 — DADOS ERRADOS NA TELA

**P2.1. DUPLICATAS NO HISTORICO** (pedido do dono, NAO CORRIGIDO)
`dealChave` monta a chave com `broker | id | symbol | executedAt | side`.
Tres buracos medidos no codigo:
- `position_id` EXISTE no tipo `Deal` (linha 31) e **nao entra na chave**.
  Duas operacoes que compartilham ticket e horario na mesma conta colidem.
- `type` **nao entra na chave**. `side` vem das exchanges e `type` do MT5;
  uma linha so com `type` (padrao do MT5) tem `side` vazio, e todas as
  movimentacoes do mesmo instante colidem entre si.
- `entry` (IN/OUT) **nao entra na chave**. Abertura e fechamento da MESMA
  posicao com o mesmo ticket e o mesmo segundo viram um registro so.
O campo `position_id` foi feito para exatamente isso e esta sendo ignorado.

### PRIORIDADE 3 — INTERFACE (outro agente trabalhando; NAO TOCAR)

**P3.1. Aba Robo** — o dono pediu operacao automatica + grafico XM Global ao
vivo + mini terminal embaixo, aba simples e leve. O outro agente reescreve
`RobotTabs.tsx` e apagou `MesaXM.tsx`.
**P3.2. Aba Calendario** — dono pediu reconstruir com estilo do calendario do
MT5. Ele mexendo em `EconomicCalendarTab.tsx`, `calendar.css`,
`useEconomicData.ts`.
**P3.3. Aba Sistema** — dono pediu "melhorar mais um pouco".
`SystemHealthOnly.tsx` ja mede CPU, RAM, disco, temperatura, GPU e latencia.

### PRIORIDADE 4 — DECISAO DO DONO (bloqueia P3)

**P4.1. "Tirar o generico e as mensagens de aviso"** — sem criterio mensuravel.
**P4.2. Base XM Global + MT5** — conflita com `AGENTS.md` ("nenhuma corretora
pode ser caminho exclusivo; MT5 e uma entrada entre nove") e com a trava
`tests/test_auto_engine.py::TestRoteamentoPorCorretora`.

## D. MCP — PESQUISA FEITA (05/10/2026)

Fonte: documentacao oficial, **spec 2026-07-28**.

- **STDIO** = servidor local, um cliente. **Streamable HTTP** = remoto, varios
  clientes. `backend/trading_mcp.py` usa o gateway HTTP local (9001).
- **Notifications** (`tools/list_changed`) existem para o servidor avisar que a
  lista de ferramentas mudou. O gateway hoje NAO as emite: o painel so
  descobre ferramenta nova recarregando a tela.
- **Discovery** por `tools/list` com cursor de paginacao. O `TOOLS` do projeto
  e uma lista fixa em Python.
- **`_meta`** transportam `protocolVersion`, `clientInfo`, `subscriptionId`.

**O QUE O MCP DO PROJETO JA CUMPRE (medido em `backend/trading_mcp.py`):**
```
L63   request_id = f"mcp-{acao}-{os.getpid()}-{time.time_ns()}-{next(_SEQ)}"
L64   "confirm": True
L172  close_position tambem monta request_id proprio + confirm: True
L32   _SEQ = itertools.count(1) -> request_id unico com clock grosso
```
Ou seja: idempotencia por `request_id` e `confirm` obrigatorio estao la, como
o `AGENTS.md` exige. **Nao mexer nisso.**

**CANDIDATOS AVALIADOS — NENHUM APLICADO.** Mudar MCP com conta real
operando exige teste proprio; nada abaixo foi tocado.

1. `tools/list_changed` quando um adaptador de corretora sobe ou cai. Baixo
   risco, ganho real: o painel deixa de depender de reload.
2. Declarar `readOnlyHint` / `destructiveHint` / `idempotentHint` no schema.
   O projeto JA tem essa separacao no codigo (`tool_call` divide leitura de
   `place_order`), mas **nao no schema declarado** — quem le o `TOOLS` nao
   sabe o que e leitura e o que mexe em dinheiro.
3. Negociar `protocolVersion` no bootstrap. Risco de breaking change.

## E. O QUE ESTA LIMPO E CONFIRMADO

- **Sem nome fixo de ativo:** `app/market_symbols.py:35` e `:71` devolvem `""`.
  `return ""  # sem ativo fixo`.
- **Sem corretora como caminho exclusivo:** `backend/broker_registry.py`
  mantem o catalogo; trava em `TestRoteamentoPorCorretora`.
- **Sem saque/transferencia:** `tests/test_movimentacoes.py::TestNadaDeDinheiro
  ForaDaCorretora` le o fonte do gateway e reprova se aparecer `/api/withdraw`,
  `/api/transfer`, `/api/saque` ou `/api/transferencia`.
- **Credencial nunca em log:** nesta sessao so NOMES de chave foram lidos;
  nenhum valor de token foi impresso ou gravado.

