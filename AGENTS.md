# AGENTS.md — XAU AI PRO

> Documento de trabalho para qualquer agente que mexe neste repositório.
> Sem data e sem hora de propósito: as regras valem para sempre, os números
> não. Se um número aqui divergir do que o comando medir, **o comando vence**;
> corrija o número.

> **ESTADO DE HOJE: [`Docs/PASSAGEM_20261007_PRIMEIROS_PASSOS.md`](Docs/PASSAGEM_20261007_PRIMEIROS_PASSOS.md)**
> O que fazer primeiro, os números medidos e o que está aberto. Leia antes de
> mexer em qualquer coisa — este arquivo diz as regras, aquele diz o estado.

## 1. O que este projeto é

Plataforma de operação de múltiplas corretoras. Uma conta **REAL** opera por
três caminhos independentes, e o dono escolhe qual usar a cada momento:

```
MOTOR -> IA -> decide ativo, timeframe e limites -> opera   (backend Python)
EA    -> IA -> decide sinal                             -> opera   (MT5)
MESA  -> voce -> monta a ordem                            -> opera   (grafico)
```

Não há botão de confirmação por ordem. A responsabilidade de operar é do
dono; a de decidir é da IA ou dele, conforme o caminho escolhido.

### Componentes

| Pasta | Responsabilidade |
|---|---|
| `backend/` | gateway local (porta 9001), adaptadores de corretora, risco, auditoria, fila, MCP de trading |
| `frontend/` | interface React/TypeScript empacotada por Tauri |
| `core/` | componentes Rust do Core (portas 9002/9003) |
| `MQL5/Experts/XAU_AI_PRO/` | Expert Advisors, editáveis com recompilação manual |
| `app/` | interface Tkinter legada, integração local, memória e configuração |
| `tests/` | suíte Python do gateway e da lógica de aplicação |
| `scripts/` | build, instalador, preflight, auditorias e ferramentas de prova |
| `Docs/` | decisões, levantamentos e o estado medido de cada ciclo |
| `mcp/` | catálogo interno de servidores MCP; não é configuração do OpenCode |

---

## 2. A única proibição

**Nenhum saque, transferência, resgate ou movimentação de fundos para fora da
corretora. Em nenhum adaptador, em nenhuma rota, em nenhum cliente, em
nenhuma tela.**

`withdrawals_enabled` e `transfers` permanecem `False` fixos. Uma ordem de
compra ou venda não altera esse valor, e nenhuma refatoração pode torná-lo
condicional.

**Ler** movimentação de saldo é permitido e necessário: o histórico mostra
depósito, saque, crédito, bônus e comissão porque o operador precisa saber de
onde veio o dinheiro. **Mover** dinheiro é proibido.

A trava é `tests/test_movimentacoes.py::TestNadaDeDinheiroForaDaCorretora`:
lê o fonte do gateway e reprova se aparecer `/api/withdraw`, `/api/transfer`,
`/api/saque` ou `/api/transferencia`. **Nunca remova nem enfraqueça esse teste.**

---

## 3. Nenhum ativo e nenhuma corretora são presumidos

Duas regras do dono, ambas verificadas por teste.

**Nenhum símbolo pode ser presumido.** Símbolo vazio é **recusa com motivo**,
nunca um ativo padrão. Uma lista fixa de ativos contra os milhares que a
corretora oferece é exatamente essa presunção. A classe de um ativo vem da
**hierarquia que a corretora preenche**, não de palavra solta no nome — sem
fronteira de palavra, `SOL` casa dentro de "Solvar".

Trava: `tests/test_ai_inference.py::TestNenhumAtivoPresumido`.

**Nenhuma corretora pode ser caminho exclusivo.** `backend/broker_registry.py`
é o catálogo. Escolher uma corretora na tela tem de ser a corretora que
realmente opera, e a resposta segue sendo a que a corretora devolveu.

Trava: `tests/test_auto_engine.py::TestRoteamentoPorCorretora`.

O que **não** viola a regra: tabelas de mapeamento, o `Literal` de
`backend/universal_contracts.py` (é a lista do que é suportado) e o próprio
`broker_registry` (é o catálogo).


---

## 4. Execução REAL

Execução real exige, nesta ordem: validação completa em DEMO, forward test
aprovado, endurance test e autorização explícita do dono.

Gates, liberadas por padrão e podendo ser ligadas:

```
XAU_ENABLE_MEXC_EXECUTION=1     XAU_ENABLE_BINANCE_EXECUTION=1
XAU_ENABLE_BYBIT_EXECUTION=1    XAU_ENABLE_OKX_EXECUTION=1
XAU_ENABLE_MT5_EXECUTION=1      XAU_ENABLE_TRADE_COMMANDS=1
XAU_MCP_TRADING=1               XAU_ENABLE_EMERGENCY_RESUME=1
XAU_ENABLE_DEMO_ORDERS=1        XAU_ENABLE_REAL_ORDERS=1
```

**Toda** ordem continua exigindo `confirm=true` e `request_id` idempotente, e
passa por `risk_gate`, `intent_log` e `audit_log`. Nenhuma refatoração remove
essas três camadas para "simplificar".

O token de sessão é injetado pelo Tauri por sessão e **prevalece** sobre o
`.env`. Sem ele o gateway recusa tudo com 401 — isso é **fail-closed correto**,
não defeito. Não "conserte" isso.

---

## 5. A regra que mais caro neste projeto

**Onde dois lados do mesmo dado discordam do nome, o sintoma é recusa com
motivo errado — e o operador culpa a coisa errada.**

Já aconteceu com `volume`/`quantity`, `ts`/`timestamp`, `symbol`/`esperado`,
`X-Gateway-Token`/`Authorization`, `/health`/`/api/health` e `side`/`type`.
Cada vez, o defeito real era do **cliente**, e o relatório mandava o operador
olhar o **servidor**.

Antes de investigar qualquer "recusa", "campo faltando" ou "não funciona",
confirme **qual nome o outro lado realmente lê**. Leia o código de quem
consome, não o de quem produz.

O mesmo vale no sentido inverso: um teste que **repete** o código em vez de
importá-lo prova que o código está certo mesmo quando está errado. O teste
precisa exercitar o caminho inteiro.

---

## 6. Teste verde pode estar escondendo defeito

Já aconteceu de três formas independentes:

- um duble de teste lia o **campo errado** e o teste passava;
- um teste de tradução **repetia** o código em vez de importá-lo;
- uma verificação contava **117 elementos** quando esperava 13.

Portanto:

1. **Nunca** `xfail` onde existe compilador e código. Onde há erro, tem de
   reprovar. `skip` que mascare erro é o mesmo defeito que o teste existe para
   pegar.
2. **Nunca** afrouxar uma trava para ela parar de reprovar. Se o teste falha,
   ou o código está errado, ou o teste está errado — as duas outras opções são
   fingir.
3. `pytest.ini` promove `PytestReturnNotNoneWarning` a **erro**: um teste que
   **retorna** valor em vez de usar `assert` não verifica nada, e passa calado
   no fim de uma saída de mil pontos.
4. **Uma trava que proíbe DOCUMENTAR é o defeito, não a proteção.** MEDIDO em
   07/10/2026: o teste *"o mapa é config e o código não tem nome de ativo"*
   (§3) varria o arquivo e reprovou no texto que documentava a medição. A regra
   do §3 estava certa; **o teste é que estava errado**. Ao escrever uma trava
   textual, **case a REGRA, não a palavra** — e se a regra for "nenhum nome no
   código", meça o código sem comentário nem docstring. Use `tokenize`, não
   regex: um `#` dentro de string (URL, caminho) não é comentário, e o regex
   apaga a linha inteira junto com o código dela.

**Toda correção precisa de prova negativa.** Um teste que só passa não prova
que a guarda funciona. Escreva também o caso que **deveria reprovar** e
confirme que reprova.

---

## 7. MQL5 compila fora do repositório

Alterar `.mq5`, `.mqh`, `.mq4` ou `.set` **exige recompilar no MetaEditor64**
(`C:\Program Files\MetaTrader 5\MetaEditor64.exe`) e **reanexar o EA ao
gráfico**. Compilar não reanexa.

**Nenhum workflow compila MQL5.** O `.ex5` não é versionado. A consequência é
medida e precisa estar escrita: **um `.mq5` quebrado passa o CI inteiro.**

O que fecha a lacuna, obrigatório antes de considerar a mudança pronta:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_mql5_compila.py
```

Esse teste invoca o MetaEditor de verdade. Ele pula onde o MetaEditor não
existe (CI em Linux) — nunca `xfail`.

Guarda de alteração: `scripts/preflight.py::checar_mql5()` reprova qualquer
diff em `MQL5/Experts` que não esteja declarado em `AUTORIZACOES_MQL5`.
Alteração declarada dá **aviso**, nunca `ok`, porque compilar e reanexar são
passos fora do repositório.

---

## 8. Desenvolvimento

A raiz usa Python 3.11 ou 3.12. As dependências legíveis estão em `requirements.txt`; as dependências de desenvolvimento estão em `requirements-dev.txt`.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q tests
```

Frontend:

```powershell
Set-Location frontend
npm ci
npm test
npx tsc --noEmit
npm run build
```

Backend:

```powershell
Set-Location backend
npm ci
npm run lint
npm run build
```

Core:

```powershell
Set-Location core
cargo fmt --all -- --check
cargo check --locked
cargo test --locked
```


O cache de build do Rust vive **fora** do disco de codigo, em
`Temp\cargo-target` (definido por `scripts\build_app.bat`). O `target` dentro
do repositorio ja chegou a alguns GB e derrubou o `cargo check` com erro de
disco cheio antes de qualquer teste.

### Validacao antes de dizer que terminou

| Mudanca | Validacao minima |
|---|---|
| gateway / adaptador | `pytest -q tests/test_execution_adapters.py tests/test_universal_execution.py tests/test_broker_coverage.py` |
| historico / movimentacao | `pytest -q tests/test_movimentacoes.py` |
| EA (`.mq5`/`.mqh`) | `pytest -q tests/test_mql5_compila.py` **e** reanexar no grafico |
| frontend | `npx tsc --noEmit` **e** `npx vitest run` |
| qualquer coisa | a suite Python inteira |

Nao reporte "pronto" com suite parcial rodando. **Meça e mostre o numero.**

### Preflight

```powershell
.\.venv\Scripts\python.exe scripts\preflight.py --etapa app-rodando
```

A etapa importa. Com o app no ar, a porta 9001 **deve** estar ocupada:
`preflight.py` usa `esperar_livre=etapa != "app-rodando"`. Rodar a etapa errada
acusa falha onde o sistema esta correto.

Antes de `git status` travar: `.\scripts\limpeza_segura.ps1 -Apply -DebugCache`.
Nao apagar nada com build ou teste no ar.

---

## 9. Formatação de número é configuração, não enfeite

Toda preferência precisa de um **consumidor real**. Um controle que nada lê é
pior que a ausência dele: o usuário acredita que está protegido.

Ao remover um controle, **meça o uso antes** e registre no código o que foi
removido e por quê. Um controle que volta sem consumidor volta como defeito.

**Casas decimais não é preferência global.** Preço, volume, percentual e
moeda têm precisões diferentes, e a conta real tem contratos que exigem casas
distintas em Forex e em cripto. A ficha do símbolo que a corretora entrega é a
fonte; uma preferência global é atalho.

---

## 10. Camadas de dado que não podem ser misturadas

**Operação** é compra ou venda: tem símbolo, volume e preço. **Movimentação de
saldo** é depósito, saque, crédito, bônus ou comissão: não tem símbolo e não
tem volume.

O MT5 grava as duas como **deal**, no mesmo histórico. Reduzir o tipo do deal
a dois estados (`BUY` e "todo o resto é SELL") faz um depósito aparecer como
venda, e o resumo de performance somar dinheiro que **entrou** como se fosse
**lucro**.

Consequência direta: acerto, fator de lucro e resultado do período medem **só
operação**. Entrada e saída de saldo têm nome, cartão e coluna próprios.

Ao tocar em histórico, meça com a **conta real**: `history_deals_get` de
vários anos, contando por tipo. Um `else` que engole um tipo de deal é
invisível em teste sintético e evidente no dado real.

---

## 11. Trabalho em paralelo no mesmo repositório

Quando mais de um agente compartilha o working tree:

- **Não commite arquivo que o outro também alterou** sem separar por hunk.
  `git apply --cached` com patch seletivo é o caminho seguro.
- Antes de editar, releia o arquivo. Ele pode ter mudado desde a última
  leitura.
- Falha de teste em arquivo do outro agente **não é sua** — mas é preciso
  **comprovar**: rode o arquivo dele isolado. Passando isolado e falhando junto,
  é estado compartilhado, não interferência sua.
- Registre em `Docs/` quais arquivos são de quem, com caminho e tamanho do
  diff. Sem isso, o próximo ciclo não sabe o que pode tocar.

---

## 12. Regras operacionais

- Não registrar token, senha, DSN, chave de API ou conteúdo de `.env` em
  log, mensagem, commit ou resposta HTTP. Para verificar se existe, leia **o
  nome da chave**, nunca o valor.
- Não usar dado simulado como se fosse dado de mercado real. Backfill, cache e
  payload mockado são rotulados.
- Manter alias de usuário, requisição e intenção **idempotentes por
  `request_id`**.
- Não habilitar MCP opcional sem credencial, dependência verificada e teste de
  conexão.
- `Docs/version.json` é a fonte da versão. `sync_version.py --check` reprova
  manifesto divergente, e `gateway_build` é derivado dele: frontend e core
  comparam esse valor, e divergência derruba o bootstrap com tela branca.
- O MCP de trading carrega `request_id` idempotente e `confirm` obrigatório em
  toda escrita. **Não mexer nisso** sem teste próprio.

---

## 13. Entregável

1. O que mudou, com **medida antes e depois**.
2. O que **não** foi feito, e por quê.
3. O que exige ação do dono, escrito como pergunta, não como suposição.
4. Estado do app, medido: processos, portas, heartbeat da conta.

**Nunca** declarar "pronto" sem os números.

---

## 14. Recuperação de arquivo corrompido (06/10/2026)

**Um arquivo zerado tem o MESMO tamanho do original, e o `git diff` chama de
"binário modificado".** MEDIDO: `PriceChart.tsx` tinha 19.157 bytes — todos
`0x00`, sem uma quebra de linha — e o original em `HEAD` também tinha 19.157.
O diff dizia `Bin 19157 -> 19157 bytes`.

Se aquilo for lido como "arquivo binário", a restauração natural é
`git checkout` do `HEAD` — e o `HEAD` era a versão **antiga**, sem 24 horas de
trabalho.

**Como se descobre:** ler os bytes, não confiar no diff.

```powershell
$b = [System.IO.File]::ReadAllBytes("caminho.tsx")
"zeros=$($b.Count -eq ($b | Where-Object { $_ -eq 0 }).Count)"
```

Zero no primeiro bloco é **arquivo destruído**. Não é binário, não é
encoding, não é BOM.

**Onde procurar a cópia boa, em ordem:**

1. **`.git`**: `git cat-file blob HEAD:<caminho>` — costuma ser a versão
   **antiga**, e por isso o último recurso, não o primeiro.
2. **checkpoint do editor**: `git log --all --oneline -S "<símbolo que só a
   versão nova tem>" -- <arquivo>`.
3. **source map do `dist`**: `frontend/dist/assets/*.js.map` tem `sourcesContent`
   com o **TypeScript original**, e o `.map` é do **último build**. Foi o que
   salvou aqui: 71.001 bytes contra 19.157 do `HEAD`.

Extrair:

```python
import json, pathlib
m = json.loads(pathlib.Path("frontend/dist/assets/index-XXX.js.map").read_text(encoding="utf-8"))
i = [n for n, s in enumerate(m["sources"]) if s.endswith("PriceChart.tsx")][0]
print(m["sourcesContent"][i])
```

**Cuidado com `>` do PowerShell:** ele reescreve o arquivo em UTF-16 e
corrompe o blob. Use `cmd /c "git cat-file blob ... > arquivo"`.

**`git status` recusando com `bad signature 0x00000000`** é o **índice**
zerado, não o repositório: `git read-tree HEAD` reconstrói. O stash, se existir,
é um arquivo à parte (`git/refs/stash`) e um arquivo zerado ali **não tem
reconstrução**.

**Deixe o backup antes de reconstruir**, e o `stash` quebrado movido para fora
em vez de apagado — `git update-ref -d` falha quando o ref está quebrado.

**Depois de recuperar, meça antes de dizer que consertou:** um `.tsx` zerado faz
`tsc` despejar milhares de `TS1127` e derruba 7 arquivos de teste ao mesmo
tempo, e o sintoma parece "o projeto quebrou". **Nunca** esconder falha de teste
alheio em silêncio — nomeie o arquivo e o dono.


