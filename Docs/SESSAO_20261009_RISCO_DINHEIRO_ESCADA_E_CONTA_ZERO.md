# Sessão 09/10/2026 — risco em dinheiro, escada de padrões, build e a conta a zero

> Documento de trabalho. Sem data e sem hora de propósito: as regras valem para
> sempre, os números não. Se um número aqui divergir do que o comando medir,
> **o comando vence**; corrija o número.

Árvore principal do EA (decisão do dono, vigente nesta sessão):
`...\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\XAU_AI_PRO`

---

## 1. O que o dono mandou, e o que foi feito

| pedido | situação |
|---|---|
| Trava de margem livre que não trava (era 20) | feita — `MinFreeMargin=10.0` nos 2 default e 3 `.set`, e nos 24 gráficos |
| DD diário deve ser perda realizada | feita — `GetDailyLossPercent()`, gate e tela com a mesma medida |
| Tela que mostra número que o gate não usa | feita — `PerdaDia` (trava) e `Amplitude` (pico-vale), nomeadas |
| Risco em **dólares**, não pontos crus | feita — `RiskPerTradeUsd` + `RewardRatio`, conversão única |
| Escada de padrões TP = SL = N | feita — 9 `.set`, de 2 a 10 dólares |
| Mover TP/SL ao vivo, fechar 30% | **já existia** — `ManagePositions()` no `OnTick` |
| Gatilhos da gestão em pontos crus | convertida — `PartialTriggerUsd`, `BreakEvenTriggerUsd`, `BreakEvenOffsetUsd` |
| Sem stop a partir de 0,4 lote | implementada com o número do dono — **hoje não dispara**, ver §4 |
| Escada de lotes 0,2/0,3/0,4/0,5 | **impossível nesta conta** — ver §4 |
| App: build, desinstalar, instalar, testar | build e instalação feitos — **bloqueado na porta**, ver §6 |
| Documentar tudo | este documento |

---

## 2. Defeitos corrigidos nesta sessão

### 2.1 `terminal_aberto()` falhava ABERTO

`backend/chart_attach.py` decidia se o MT5 estava aberto procurando `lock*` na pasta
de dados. **MEDIDO: zero arquivos `lock*`, com `terminal64.exe` rodando.** A guarda
respondia "fechado" com o terminal aberto, e `anexar_ea` gravaria o `.chr` num MT5
vivo — que o descarta ao sair. Exatamente o "trabalho perdido" que a docstring da
própria função descreve.

Os testes existentes faziam `monkeypatch` da detecção, então nunca pegariam.

Corrigido com duas fontes: `lock*` **e** processo `terminal64.exe` (`tasklist` no
Windows, `/proc` no Linux, `ps` como reserva, sem dependência nova). Fora do `if`
que checa a raiz: mesmo sem raiz resolvida, um terminal vivo é motivo para não
gravar. 5 testes novos, incluindo a prova negativa.

### 2.2 `definir_input_ea` — por que não usei `anexar_ea`

MEDIDO nos 24 gráficos deste terminal: **`expertmode` não é uniforme** — 11 com
**37** e 13 com **5**. `_montar_bloco_expert` só escreve 4 ou 5, e a API recebe
`autotrade: bool`. Passar esses gráficos por `anexar_ea` reescreveria **37 como 5**,
mudando o estado que pode ser o que mantém o Algo Trading ligado, sem ninguém saber
o que 37 significa.

`definir_input_ea` troca **só a linha do input**, preservando `expertmode`, `path`,
símbolo, timeframe e os outros 112–129 inputs. 10 testes novos.

### 2.3 Backup: 44 falhas com caminho vazio

```
[BACKUP] Backup com problemas | copiados=64 | falhas=44
[BACKUP] Origem nao encontrada:        <- 44x, caminho VAZIO
```

`ExpandPattern` escrevia **sempre a partir de `out[0]`** e não aceitava índice
inicial. O chamador a usava **duas vezes no mesmo array** — `FILE_COMMON` e depois
`LOCAL` — somando os retornos em `found`. A segunda chamada sobrescrevia a primeira
enquanto `found` contava as duas: 44 + 64 = 108 posições percorridas, só 64
preenchidas. As 44 restantes eram lixo, com `origPath` vazio.

Por isso a mensagem saía sem caminho — e mandava o operador procurar *arquivo*
faltando quando o defeito era *índice*. Agora há `start` como índice inicial, e
entrada sem caminho é contada no relatório (`sem_caminho=`).

### 2.4 Pontos crus — a mesma doença, quatro vezes

| onde | era | ficou |
|---|---|---|
| `MaxSpread` | pontos (5000 no BTCUSD) | `MaxSpreadPct=0.6` |
| `StopLossPoints` / `TakeProfitPoints` | pontos (US$ 20 no USDJPY, US$ 0,03 no BTCUSD) | `RiskPerTradeUsd` + `RewardRatio` |
| `PartialTrigger` | pontos (75% do alvo no ouro, 1,5% no BTCUSD) | `PartialTriggerUsd` |
| `BreakEvenTrigger` / `BreakEvenOffset` | pontos | `BreakEvenTriggerUsd` / `BreakEvenOffsetUsd` |

Todos com a **definição única** `DistanciaPontosParaRiscoUSD()`, consumida por
`ExecutionEngine` e `OrderManager` (que tinham a fórmula **duplicada**).

MEDIDO depois da conversão, com 0,01 de lote: **US$ 2,00 de stop e US$ 2,00 de alvo
em GOLD, BTCUSD, ETHUSD, EURUSD, GBPUSD, USDJPY, USDCAD, USDCNH, USDSEK, AUDUSD,
NZDUSD e USDCHF**, e nenhum viola o stop level da corretora.

---

## 3. Erros meus nesta sessão

Registrados porque o próximo ciclo precisa saber o que não repetir.

1. **Conclusão errada por janela de tempo errada.** Disse que a correção de DD "não
   estava no ar". A janela que usei (21:28:00–21:31:44) **incluía as linhas
   anteriores ao reanexar** (21:28:50). O dono estava certo: era o EA errado antes.
2. **`/inc` errado no MetaEditor.** Apontei para `Experts\XAU_AI_PRO` em vez da raiz
   `MQL5`. O MetaEditor **apagou o `.ex5`** e falhou com `error 106`. Recompilado em
   1 minuto; o EA em execução não foi afetado (código em memória), mas houve janela
   sem `.ex5` em disco com AUTO ligado.
3. **Corrupção de acentuação.** Troquei `MinFreeMargin` fazendo round-trip por ASCII:
   `—` virou `???`, `ç` e `È` viraram `??`, e dois caracteres chineses (`智能`) viraram
   6 `?`. **Achei pelo `git diff`, não pelo tamanho** — o byte count bateu, o conteúdo
   não. Reparei recuperando do blob do `HEAD` e conferi: bytes idênticos ao original.
4. **Regex com três erros.** `\s21:(2[89]|3\d\d)\.` exigia ponto onde vem `:`;
   `Tstamp '21:28:50'` sem milissegundos devolvia `-1` e o filtro não filtrava;
   e comparei objetos `MatchInfo` em vez de `$_ .Line`.
5. **Campo errado em script.** Escrevi `ea`/`simbolo`/`periodo`; as chaves reais são
   `expert`/`symbol`/`period_size`. Por isso reportei "0 gráficos com EA anexado" —
   são 24.
6. **Asas aninhadas e regex de remoção.** A inserção no `preflight.py` quebrou a
   sintaxe com aspas dentro da string, e o regex de remoção não casou, deixando 18
   blocos em vez de 9. Removi os 18 por linha e agora o `py_compile` roda **dentro**
   do próprio script: se a inserção quebrar a sintaxe, ele aborta.
7. **Chave de API impressa.** Li `config/assistant.ini` inteiro e imprimi `ApiKey` e
   `ApiKeyMQL5` no console. O `AGENTS.md` §12 proíbe. Devia ter lido **o nome da
   chave**, nunca o valor. Se este histórico for compartilhado, rotacionar.
8. **Alarme sem segunda medição.** Anunciei "a conta está em 0,00" sem esperar e ler o
   histórico. O número estava certo; a conclusão apressada é que não era.

---

## 4. O tamanho da conta decide o que é possível

MEDIDO na conta 391773676 (balance 12,13, margem livre 15,48, piso 10,00):

| símbolo | 0,01 | 0,05 | 0,1 | 0,2 | 0,5 |
|---|---|---|---|---|---|
| GOLD | 4,15 ✅ | 20,74 ❌ | 41,48 ❌ | 82,96 ❌ | 207,39 ❌ |
| EURUSD | 1,12 ✅ | 5,61 ❌ | 11,22 ❌ | 22,44 ❌ | 56,09 ❌ |
| USDCAD | 1,00 ✅ | 5,00 ✅ | 10,00 ❌ | 20,00 ❌ | 50,00 ❌ |
| BTCUSD | 0,82 ✅ | 4,09 ✅ | 8,18 ❌ | 16,36 ❌ | 40,90 ❌ |

**Maior lote que passa: 0,01 a 0,05.** A escada 0,2/0,3/0,4/0,5 que o dono pediu
**não existe nesta conta** — 0,4 de ouro exigiria 165,91 de margem contra 15,48
livres. Decisão do dono: "conta suporta", ou seja, fica o que a conta suporta.

### 4.1 A regra "sem stop a partir de 0,4" está implementada e não dispara

`NoStopFromLot = 0.4`, implementado com o número do dono, **não trocado por um que
coubesse**. Como 0,4 não abre, a regra só acende se a conta for funded. O log é alto
e explícito, para não ser lido como falha:

```
[RISCO] SEM STOP | GOLD | lote 0.40 >= NoStopFromLot 0.40 | alvo em 200 pontos
```

**Aviso de risco, medido e não teórico:** sem stop, uma vela M5 típica de 0,2 lote
no EURUSD move **US$ 6,20 = 51% do balance**, e o p90 de 24h move **US$ 13,00 =
107%**. O limite diário de 5% **bloqueia operações novas, mas não fecha nem limita a
que já está aberta**. Sem stop, a posição não tem teto.

---

## 5. A CONTA FOI A ZERO — e não foi o EA deste projeto

MEDIDO, leitura apenas:

```
conta 391773676 | balance 0,00 | equity 0,42 | posições abertas: 0

09/10 02:29:29  #262204747  USDCAD  SAIDA    0,01    -1,20   magic 0
09/10 02:33:27  #262205597  BTCUSD  ENTRADA  0,05      0,00   magic 0
09/10 02:53:04  #262210934  BTCUSD  SAIDA    0,05  -16,13   magic 0
09/10 02:53:04  #262210937  (sem símbolo)         +5,20   magic 0
09/10 02:53:04  #262210938  (sem símbolo)         -5,20   magic 0
                                              ───────
                                              -17,33
```

**Todo o deal tem `magic 0`.** O EA deste projeto é `magic 2026001`
(`MagicNumber=2026001` em todos os presets). `magic 0` é operação de outra coisa.

Reforçando que **não foi o XAU AI PRO**:

- **Nenhum** deal com `magic 2026001` nesse período.
- O EA estava **bloqueado** desde 22:33 por `[SAFETY] Daily loss limit: 3.17/0.61` —
  ele não abriu nada nessas horas.
- O EA **não abre socket** (verificado: só `WebRequest` do Telegram). Nada dele
  poderia ter fechado posição.

Os dois últimos deals (+5,20 e −5,20, mesmo segundo, sem símbolo, volume 0,00) parecem
fechamento compensado. **Aberto: se essas operações foram do dono.** Se não foram, é
operação não autorizada na conta — outra investigação, bem mais séria.

Nota: `assistant.ini` do MT5 tem `PermissionsTrade=0`, ou seja o assistente do MT5
**não pode operar**. Isso não elimina outras origens.

---

## 6. App: build e instalação feitos, bloqueado na porta

### 6.1 O que passou

```
preflight                          2 avisos, nenhuma falha bloqueante
build_app.bat                      MSI 344,9 MB + NSIS 222,2 MB
desinstalação (uninstall.exe /S)   exit=0, binário e uninstaller removidos
instalação (NSIS /S)               exit=0
exe instalado 13.508 KB, versão 1.2.4
bridge / core / Python\models      presentes
MULTI_CRYPTO / MULTI_FIAT / MULTI_METALS  presentes
```

### 6.2 O bloqueio: MT5 e o app querem a mesma porta

Abrindo pelo atalho, como usuário normal, o app sobe a janela e **não sobe o
backend**. Com stdout capturado:

```
[gateway] snapshot inicial: equity=10.75 posicoes=1 ea=alive
Traceback (most recent call last):
  File "mt5_gateway.py", line 3794, in <module>
  File "mt5_gateway.py", line 3778, in main
  File "backend\gateway_server.py", line 147, in criar_servidor
PermissionError: [WinError 10013] Foi feita uma tentativa de acesso a um soquete
                 de uma maneira que e proibida pelas permissoes de acesso
[PYI-7844:ERROR] Failed to execute script 'mt5_gateway' due to unhandled exception!
```

MEDIDO: quem está escutando em `127.0.0.1:9001` é **`terminal64`**. E a causa:

```
config\assistant.ini do MT5:
  [MCP.MetaTrader]
  Enable=1
  Endpoint=http://127.0.0.1:9001/mcp

backend\mt5_gateway.py:55:
  PORT = 9001
```

**MT5 e o gateway estão configurados para a mesma porta.** Quem sobe primeiro ganha;
o app sempre perde.

A porta está hardcoded em **18 lugares**, incluindo
`frontend\src-tauri\tauri.conf.json:41` (CSP) e `main.rs:398`. Mudar é grande.

**Duas saídas, nenhuma aplicada sem o dono decidir:**

1. Desligar `[MCP.MetaTrader]` no MT5 (`Enable=0`). O projeto **já tem** MCP de
   trading próprio; o do MT5 é redundante. Uma linha.
2. Tornar a porta configurável e mover o gateway. Correção maior, mas é a que
   sobrevive a qualquer futuro conflito de porta.

---

## 7. Estado e o que está pendente

### Validado

```
MetaEditor (árvore real)   0 errors, 0 warnings
ex5                        23:03:42, 433,1 KB
pytest -q tests            1298 passed, 2 skipped
preflight                  2 avisos, nenhuma falha bloqueante
```

### Pendente

1. **Reanexar o EA** — o risco em dólares, a tela `PerdaDia`/`Amplitude` e o
   conserto do backup só entram no ar depois disso. O `.ex5` está compilado desde
   23:03:42.
2. **Port dos 4 arquivos para o repo** — `Core/Config.mqh`, `Core/ExecutionEngine.mqh`,
   `Core/PositionManager.mqh`, `Management/BreakEven.mqh` estão **só na árvore real**.
   Os dois lados divergem bastante (repo sempre maior), então é edição cirúrgica, não
   cópia. O dono Priorizou a árvore real e adiou o port.
   **Consequência medida:** `pytest tests/test_mql5_compila.py` compila a árvore do
   **repo**, então **não prova mais a árvore real**. Só o MetaEditor manual prova.
3. **Portar os 9 `Padrao_*.set` e as correções do backup para o repo** — já feitos.
4. **Commitar** — 25 arquivos pendentes. Nada foi commitado; o dono ainda não pediu.
5. **Resolver a porta do gateway** (§6.2) e refazer build + instalação.
6. **Duplicados medidos:** dois `Temp/monitor_conta.py` (PIDs 7652 e 2704) e dois
   `backend.trading_mcp` (PIDs 7276 e 11948) rodando ao mesmo tempo, escrevendo no
   mesmo `monitor_conta.jsonl`.
7. **Perfil `Default` tem um gráfico em `XAUUSD`**, símbolo que a XMGlobal não
   oferece nesta conta. O perfil que opera ouro é `F1_SINGLE_11SYM`, que tem `GOLD`.

---

## 8. Regra que este ciclo deixou escrita

Ponto não é dinheiro, e distância não é risco. Quando um limite é uma **distância**,
ele significa coisas diferentes em cada símbolo, e a diferença é de um a quatro
centenas de vezes. Quando o limite é um **montante**, ele significa a mesma coisa em
todo lugar — e é o que o dono比率 precisa ver na tela.

O `AGENTS.md` §9 já dizia que formatação de número é configuração, não enfeite, e que
toda preferência precisa de um consumidor real. Esta sessão mostrou a metade que falta:
**um controle whose unit is wrong não tem consumidor nenhum** — o operador lê, não
entende, e culpa o componente errado.
