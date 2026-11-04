# 04/11/2026 — o ADX nunca era lido no Strategy Tester

Ciclo 94 · P1.91 · v1.2.135 → **v1.2.136** · 19:46–20:05

---

## 1. O pedido

"proximo". Três ciclos (93, 93b, 93c) tinham fechado com a mesma frase: *não há
número novo porque o slot do Strategy Tester está ocupado*. O próximo item de
valor não podia continuar a ser "esperar pelo slot": era preciso saber **quem**
o ocupava.

## 2. O slot não estava travado — estava a trabalhar

```
Get-CimInstance Win32_Process -Filter "name='metatester64.exe'"
8772  | pai 1000 (Services) | 16:13:19 | (sem command line legível)
12896 | pai 1000 (Services) | 16:13:23 | (sem command line legível)
11832 | pai 1000 (Services) | 16:13:33 | (MetaTester64)
4212  | pai 1000 (Services) | 16:13:37 | (MetaTester64)
4476  | pai 12016 (terminal64.exe) | 18:08:28 |
        "metatester64.exe" /local /address:127.0.0.1:3000 /password:... /dlls
```

O processo 4476 é o agente local do terminal, lançado no arranque do run. O
journal do tester diz qual:

| Campo | Valor medido |
|---|---|
| ficheiro | `Tester\logs\20261104.log` (114 521 544 B, mtime 19:49:11) |
| `.ini` | `Profiles\Tester\XAI_BASE_v131.ini` |
| símbolo / período | XAUUSD **H1** |
| intervalo | 2026.09.01 → 2026.11.01 |
| modelo | `Model=1` (1 minuto OHLC), depósito 10 000 |
| progresso às 19:49 | 2026.09.11 16:00 — **11 de 61 dias (~18 %)** |
| CPU | 1653,03 → 1655,56 s em 8 s (≈0,32 core, a subir) |

Conclusão: o `tester still started` era **verdade**. As secções §9 e §10 do
`PENDENCIAS.md` falavam de "runs fantasma" — não existem. Nada foi lançado por
cima e nenhum PF foi inventado.

## 3. O defeito que o run expôs

No meio deste journal há uma linha que não devia existir:

```
18:08:33.261  [ADX] INIT OK | Symbol=XAUUSD | Period=14
18:08:33.261  [ADX] SEM LEITURA | XAUUSD | BarsCalculated=-1 | tratado como neutro (fail-open)
...
2026.09.11 16:00  [CENARIO] XAUUSD | SEM_LEITURA | ADX=sem leitura | ATR%=0.53
2026.09.11 16:00  [SCANNER] RESUMO | ... | ADX(sem/ok)=2093/0
```

**2093 leituras de ADX, zero boas**, dez dias de simulação depois da
inicialização. O `ATR%` do mesmo bloco lê 0,53 sem problema.

### A causa

`Indicators/ADX.mqh`, nos dois sítios (`GetADX()` e `GetADX(string)`):

```mql5
int calculadas = BarsCalculated(adxHandle);
if(calculadas < ADXPeriod * 2)
   return -1.0;          // <- nunca chega ao CopyBuffer
```

No tester, `BarsCalculated()` devolve `-1` enquanto o indicador não foi
calculado. E **quem manda calcular é o `CopyBuffer`** — precisamente a chamada
que o guarda impedia. O guarda bloqueava o único acto que o desbloqueava: um
impasse auto-sustentado, e invisível porque saía como `fail-open` (neutro) em
vez de erro.

### A prova diferencial

`GetATR()` (`Indicators/VolatilityFilter.mqh:61`) lê o ATR **sem** esse guarda:

```mql5
if(CopyBuffer(volatilityATRHandle, 0, 0, 3, volatilityATRBuffer) <= 0)
   return 0.0;
```

E devolve `ATR%=0.39`…`0.53` no mesmo run, no mesmo símbolo, no mesmo segundo.
Portanto não é limitação do Strategy Tester nem falta de histórico: é o guarda.

## 4. A correção (v1.2.136)

Uma linha em cada um dos dois sítios:

```mql5
// antes
if(calculadas < ADXPeriod * 2)
// depois
if(calculadas > 0 && calculadas < ADXPeriod * 2)   // v1.2.136 P1.91: -1 NAO e warm-up, e impasse -> tentar CopyBuffer
```

- `-1` (sem dado calculado) → tenta o `CopyBuffer`, que dispara o cálculo;
- valor positivo pequeno (aquecimento real) → continua a devolver `-1.0` como
  antes, exactamente a semântica da v1.2.94;
- a mensagem de falha do `CopyBuffer` passa a publicar `BarsCalculated`, para não
  voltar a ser silenciosa.

## 5. Impacto — porque isto vale mais do que o slot

Todo o backtest feito até hoje **mediu um EA sem ADX**:

| Consumidor | Efeito com `GetADX() == -1` |
|---|---|
| `MarketScenarioDetect` | `SCENARIO_UNKNOWN` → factor de lote 1.00 sempre |
| gate dinâmico (`DynADXClear`) | fail-open permanente |
| `Core/DecisionEngine.mqh:158` | ramo "sem leitura" sempre |
| `Core/ValidationEngine.mqh:388` | validação de ADX neutra |

Ou seja: **o PF 0,6206, os 41,4 % de acerto e as 10–11 perdas seguidas não
descrevem o EA que corre nos 13 gráficos**. Não são uma medida da produção — são
uma medida de um EA diferente. A regra do dono não muda (PF > 1,20 e perdas
seguidas ≤ 8 antes de se falar de conta real); o que muda é que o próximo número
tem de ser medido com o build v1.2.136.

## 6. Validação

```
Result: 0 errors, 0 warnings, 28316 ms elapsed, cpu='X64 Regular'
04/11/2026  19:53           834.986 XAU_AI_PRO.ex5
#define EA_VERSION_STRING "1.2.136"
#property version   "1.336"   (era "1.326" — parado desde a v1.2.126)
```

Em produção nada muda: com o mercado aberto `BarsCalculated` é > 0 no caminho
normal, logo o ramo alterado é o que já era executado.

## 7. O que ficou aberto

1. **Re-medir** PF / win rate / streaks com v1.2.136 quando o run das 18:08
   terminar (ETA ~8–9 h a partir das 18:08). O `.ini` não precisa de versão: o
   caminho do `.ex5` é o mesmo.
2. **`[AI] FILE EM FALTA | Data\prediction_XAUUSD.json`** no tester: o ficheiro
   existe em `MQL5\Files\Data\`, mas o tester lê
   `Tester\Agent-127.0.0.1-3000\MQL5\Files\`, onde não está. `Tester\` é raiz de
   leitura, não de escrita, logo a cópia não pode ser feita por ferramenta.
   Copiar resolve para **um** run e congela a previsão; a solução real é o EA
   procurar a previsão em `FILE_COMMON`, para o backtest ler o mesmo ficheiro que
   a produção lê.
3. `CONVERSAS.md` tem caracteres corrompidos de sessões antigas (mojibake UTF-8
   relido como ANSI). Registado, não tocado: corrigir texto histórico é uma
   operação diferente e merece decisão do dono.
4. Push para `origin` (`forge.mql5.io`) continua bloqueado por credenciais
   expiradas. O `github` recebe.
