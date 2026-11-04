# Ciclo 91 — 04/11/2026 19:05 — fail-closed do token, IA 30F viva e raiz limpa

> Documento de estado deste ciclo. Os números abaixo foram **medidos** nesta
> sessão; se um comando futuro medir diferente, o comando vence e este arquivo
> deve ser corrigido. Nada aqui é promessa de lucro.

---

## 1. O que estava errado (medido)

| # | Defeito | Onde | Gravidade |
|---|---|---|---|
| 1 | Auth **fail-open**: sem `XAU_GATEWAY_TOKEN`, o middleware aceitava qualquer chamada | `backend/fastapi_gateway.py:104` (`if API_TOKEN:`) | alta — leitura de conta e ordem sem credencial |
| 2 | `XAU_GATEWAY_TOKEN` em texto claro na raiz do projeto | `Files/XAU_AI_PRO/TOKEN_PARA_BACKEND.txt` | alta — cópia do segredo fora do `.env` |
| 3 | Launcher armava execução REAL só por ser executado | `start_gateway.bat` (`XAU_ENABLE_REAL_ORDERS=1`, `XAU_MCP_TRADING=1`) | alta — dois cliques no Explorer = autorização inteira |
| 4 | 34 arquivos de uso único poluindo a raiz | `Files/XAU_AI_PRO/*.py`, `*.bat`, `*.txt` | baixa — ruído, risco de executar lixo |
| 5 | `pytest` ausente do `.venv` | `.venv` (sem módulo e sem `pytest.exe`) | média — a suíte Python não roda neste terminal |
| 6 | `.env` com 2 chaves (104 bytes) contra 16 do `.env.example` | `Files/XAU_AI_PRO/.env` | **não é defeito** — ver §4 |

---

## 2. Fail-closed do token — corrigido e provado

**Antes** (`fastapi_gateway.py`):

```python
if API_TOKEN:                       # sem a variavel, NADA era exigido
    auth = request.headers.get("authorization", "")
    ...
```

**Depois**:

```python
if not API_TOKEN:
    # FAIL-CLOSED: ... e melhor ficar inacessivel do que aberto.
    return _send({"ok": False, "error": "sem token configurado"}, 401)
auth = request.headers.get("authorization", "")
if auth != f"Bearer {API_TOKEN}":
    ...
```

Paridade com `backend/mt5_gateway.py::_autorizado`, que já era fail-closed
(`if not API_TOKEN: return False, "sem token configurado"`).

### Prova negativa (o caso que DEVE reprovar)

App ASGI real em `127.0.0.1:9012`, `API_TOKEN = ""`, banco de sessões isolado:

```
--- API_TOKEN vazio (fail-closed) ---
OK  health sem token: 401 (esperado 401)
OK  health token inventado: 401 (esperado 401)
OK  health token vazio: 401 (esperado 401)
OK  ping publico sem token: 200 (esperado 200)
--- API_TOKEN configurado (paridade com o que roda em 9011) ---
OK  health com token correto: 200 (esperado 200)
OK  health com token errado: 401 (esperado 401)
OK  health sem token: 401 (esperado 401)
RESULTADO: OK
```

A rota pública `/api/auth/ping` continua alcançável: fail-closed não pode
trancar a porta que emite a sessão.

### Prova em produção (9011, depois do reinício)

```
OK      health sem token: 401 (esperado 401)
OK      health token errado: 401 (esperado 401)
OK      health token correto: 200 (esperado 200)
OK      predict com token: 200 (esperado 200)
predict: available=True signal=SELL prob_buy=0,3635 prob_sell=0,6365
         price=4063,84 atr=17,439393164602258 hash=5305081777808310
RESULTADO: OK
```

O gateway subiu com `XAU_ENABLE_REAL_ORDERS=0`, `XAU_ENABLE_DEMO_ORDERS=0`,
`XAU_ENABLE_MT5_EXECUTION=0`, `XAU_ENABLE_TRADE_COMMANDS=0`,
`XAU_ENABLE_EMERGENCY_RESUME=0`, `XAU_MCP_TRADING=0`.

### Nota operacional medida

Depois de matar o processo, `netstat -ano` e `Get-NetTCPConnection -State Listen`
continuam mostrando `127.0.0.1:9011 ... LISTENING 0`. **É resíduo do socket
morto, não um servidor.** A medida correta é HTTP: conexão recusada = porta
livre. Concluir "porta ocupada" pela linha `LISTEN pid 0` trava o operador sem
motivo — foi o que travou o reinício na primeira tentativa.

---

## 3. A IA voltou a responder (XAU-30F-v4)

O runtime `backend/ai_inference.py` passou a despachar o construtor de features
e a decodificação de probabilidade pela **versão declarada no próprio artefato**
(`meta["feature_version"]`) e pelas `classes_` do modelo, em vez de assumir 25
features e 3 classes.

- `ai_inference.py`: 40 483 → 47 184 bytes (adição, não reescrita).
- Os 80 artefatos `25F-v2` mantêm **exatamente** o caminho anterior.
- O artefato publicável de XAUUSD é `XAU-30F-v4`, **binário** (`classes_=[0,1]`).
  O código antigo lia `probs[2]` como BUY — em modelo binário isso é sempre
  `0.0`, e `probs[1]` (probabilidade de SUBIR) ia para o campo NEUTRO. Alinhar
  só a contagem de features deixaria BUY mudo para sempre.

Prova independente: `xau_model_tools` recalculou `p_sell=0,6932 / p_buy=0,3068`
e o runtime devolveu os mesmos dígitos. Pelo HTTP, `feature_hash=5305081777808310`
é idêntico ao `Python/models/XAUUSD_H1.meta.json`.

Qualidade declarada do modelo (não é lucro): `edge +0,0363`, `AUC 0,5630`,
4/5 folds positivos, e **accuracy 0,5361 abaixo do baseline 0,5524**.

---

## 4. O `.env` com 2 chaves NÃO é regressão (medido)

Varredura de todas as 16 chaves do `.env.example` contra todo o código
(`.py`, `.mq5`, `.mqh`, `.ps1`, `.bat`, `.ts`, `.tsx`), buscando o nome literal:

| Chave | Consumidor real |
|---|---|
| `XAU_GATEWAY_PORT` | 10 módulos — **presente no `.env`** |
| `XAU_GATEWAY_TOKEN` | 16 módulos — **presente no `.env`** |
| `FIGMA_TOKEN`, `FIGMA_FILE_KEY` | `scripts/sincronizar_figma.py`, `scripts/validar_figma.py` (integração opcional) |
| `ASSET`, `TIMEFRAME`, `LOG_LEVEL`, `MODEL_PATH`, `ENVIRONMENT` | falso positivo: são nome de variável, enum, constante local ou nome de input MQL5 — não variável de ambiente |
| `TRADING_PAIR`, `BROKER_API_KEY`, `BROKER_API_SECRET`, `DATABASE_PATH`, `LOG_FILE`, `RETRAIN_INTERVAL`, `MAX_POSITION_SIZE`, `STOP_LOSS_PERCENT`, `TAKE_PROFIT_PERCENT` | **nenhum consumidor** |

Ou seja: as 16 chaves que sumiram do `.env` são, na prática, um template de
coisas que ninguém lê — o defeito do §9 do `AGENTS.md` ("controle sem
consumidor"). O EA e o gateway não perderam nada. As duas chaves que restam são
exatamente as duas que o sistema usa.

Se o dono quiser a integração Figma de volta, `FIGMA_TOKEN` e `FIGMA_FILE_KEY`
voltam ao `.env` quando forem usadas.

---

## 5. Token em texto claro — apagado

`TOKEN_PARA_BACKEND.txt` (132 bytes, 3 linhas) continha **a mesma string** do
`XAU_GATEWAY_TOKEN` do `.env`. Medido:

- arquivos **versionados** que contêm essa string: **nenhum** → não houve
  vazamento para o git;
- arquivo apagado; o valor continua apenas no `.env`, que é ignorado pelo git.

Recomendação: se esse arquivo circulou por chat, e-mail ou backup, **rotacione**
o token. Enquanto ele só existiu nesta máquina, a rotação é opcional.

---

## 6. Launcher de execução REAL — fechado por padrão

`start_gateway.bat` armava `XAU_ENABLE_REAL_ORDERS=1`, `XAU_ENABLE_DEMO_ORDERS=1`,
`XAU_ENABLE_MT5_EXECUTION=1`, `XAU_ENABLE_TRADE_COMMANDS=1`,
`XAU_ENABLE_EMERGENCY_RESUME=1` e `XAU_MCP_TRADING=1` **só por ser executado**.
Dois cliques no Explorer eram a autorização inteira — o oposto do §4 do
`AGENTS.md`.

Agora:

```
start_gateway.bat        -> todas as portas de execucao em 0 (leitura/diagnostico)
start_gateway.bat real   -> arma execucao, com aviso e 5 s para abortar
```

Também ganhou `cd /d "%~dp0"`, para funcionar a partir do Explorer.

---

## 7. Raiz limpa

- **34 arquivos movidos** para `Files/Backup/raiz_lixo_20261104/` (reversível):
  25 `.py` de uso único (`check_all.py`, `fix_p6.py`, `regen_raiz.py`,
  `remove_main_line.py`, ...), 3 `.bat` quebrados (`runpy.bat` começa com `off`
  em vez de `@echo off`; `run_py.bat` chama `python3.11` que não está no `PATH`)
  e 6 `.txt` de anotação.
- **1 arquivo apagado**: `TOKEN_PARA_BACKEND.txt` (§5).
- Antes de mover, foi medido que **nenhum** desses scripts é importado por
  `backend/`, `Python/`, `tests/`, `app/` ou `scripts/`.
- `check_all.py` e `check_main.py` eram **versionados**: o commit registra a
  remoção dos dois.

---

## 8. EA pronto para uso real — o que foi garantido e o que NÃO foi liberado

**Garantido (medido):**

| Guarda | Onde | Valor |
|---|---|---|
| `EnableRealAccountGuard` | `Core/RealAccountGuard.mqh:43` (default) | `true` |
| `EnableRealAccountGuard` | `Presets/XAU_AI_PRO.PRO.set:259` | `true` |
| `EnableRealAccountGuard` | `Profiles/Tester/XAU_AI_PRO.set:262` | `true` |
| `RealGuardBlockMinLotExceedsCap` | `RealAccountGuard.mqh:44` | `true` |
| `RealGuardStoplessEmergencyRMultFloor` | `RealAccountGuard.mqh:45` | `1.5` R |
| `RealGuardMaxUnarmedPositions` | `RealAccountGuard.mqh:46` | `1` por símbolo |
| `RiskPercent` | `XAU_AI_PRO.PRO.set:13` | `1.0` |
| `MaxDailyLossUsd` | `XAU_AI_PRO.PRO.set:15` | `60.0` |
| `MaxDrawdownPercent` | `XAU_AI_PRO.PRO.set:16` | `15.0` |
| Portas de execução do gateway | `start_gateway.bat` | **0** por padrão |
| Auth do gateway | `fastapi_gateway.py` | **fail-closed** |

**NÃO liberado, e por quê:** o único backtest completo no período medido está
`REPROVADO` (`RELATORIO_BACKTEST_20260901_20261101.md`): PF **0,6206**, acerto
**41,4%**, **10–11** perdas seguidas, contra o critério do dono de PF > 1,20 e
perdas seguidas ≤ 8. Guarda ligada não transforma estratégia perdedora em
ganhadora; ela limita o dano **quando** a estratégia for boa.

**Incoerência aberta, medida:** `RewardRatio` é `0,65` no preset de produção
(`XAU_AI_PRO.PRO.set:34`) e `1,30` no `.set` do testador
(`XAU_AI_PRO.set:37`). Com `RewardRatio = 0,65` o TP é 65% do SL, então um
acerto de 41,4% não paga o custo — a aritmética exige > 60% de acerto para
empatar. Medir o A/B de `MinRewardRatio` (0,55 → 1,5/2,0) é o próximo passo com
número, e **não** foi feito neste ciclo (o Testador está ocupado, §10).

---

## 9. Validação deste ciclo

```
Tools\agent-toolkit.ps1 check
  arquivos analisados: 108
  [OK] encoding UTF-8 valido em todos os fontes
  [OK] chaves balanceadas em todos os fontes
  [OK] todos os #include locais resolvidos
  RESULTADO: OK

Tools\agent-toolkit.ps1 compile
  Result: 0 errors, 0 warnings, 29318 ms elapsed, cpu='X64 Regular'
  [OK] binario atualizado: XAU_AI_PRO.ex5 (2026-11-04 19:05:25)
```

**Não rodou:** a suíte `pytest`. O `.venv` não tem `pytest` instalado
(`requirements-dev.txt` pede `pytest>=9.0.3`), então a validação Python foi feita
por scripts determinísticos próprios, que exercitam o caminho real (app ASGI +
HTTP + `ai_inference.inferir`). Instalar as dependências de desenvolvimento
exige rede e é decisão do dono.

---

## 10. Continua aberto (dono / próximo ciclo)

1. **Allowlist de WebRequest — já resolvida (medido 04/11 18:06).**
   `http://127.0.0.1:9011` está permitido: o journal devolve `HTTP=401` com
   corpo de 37 B (resposta do gateway) em vez de `body=0B` (erro `4014`). O que
   faltava era o **formato** da entrada — sem barra final e sem caminho. Token e
   porta passaram a ser lidos do `.env` em tempo de execução
   (`AIGatewayTokenEfetivo`/`AIGatewayUrlEfetiva`), então os gráficos **não**
   precisam ser reconfigurados: precisam apenas receber o `.ex5` novo (§10.4).
2. **Testador ocupado**: 5 processos `metatester64.exe` ativos nesta medição;
   nenhum backtest foi lançado. Re-medir quando o slot estiver livre, com o EA
   `v1.2.134` e ticks reais.
3. **`Data\prediction_XAUUSD.json`**: `WebRequest` não funciona dentro do
   Strategy Tester. Para o EA ver IA no backtest é preciso gerar esse arquivo;
   no gráfico real/demo o caminho HTTP já responde.
4. **Reanexar o EA** nos 13 gráficos `XAU_P216_LIVE` para o `.ex5` de
   `19:05:25` passar a valer (compilar não reanexa).
5. **`pytest`** no `.venv` (decisão do dono: instalar `requirements-dev.txt`).
6. **`RewardRatio` 0,65 vs 1,30** e o A/B de `MinRewardRatio` (§8).
7. **Conta real**: não, enquanto PF < 1,20.
