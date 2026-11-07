# Ciclo 95 - 04/11/2026 20:10 - P1.92: o backtest lia um EA SEM IA (v1.2.137)

> Pedido do dono: "proximo" (avancar para o proximo item de valor com o
> Strategy Tester bloqueado), mantendo a regra de governacao: conta real so
> com PF > 1,20 e perdas seguidas <= 8, e mesmo ai com
> `EnableRealAccountGuard=true` e risco baixo.

---

## 1. Estado medido a entrada

| Facto | Medicao |
|---|---|
| Slot do Strategy Tester | **OCUPADO**. `Tester\logs\20261104.log` com 130 885 948 bytes e mtime `2026-11-04T22:58:02Z` (a crescer durante a sessao); ultima linha de arranque as `18:08:28` com `XAI_BASE_v131.ini` |
| `tester_list_result_windows` | lista **vazia** - coerente com run em curso, nao com slot livre |
| Conclusao | **P-02 continua aberto. Nenhum run lancado, nenhum PF novo.** |
| Graficos vivos | 13 janelas do perfil `XAI_P216_LIVE`, todas com `Experts\XAU_AI_PRO\XAU_AI_PRO.ex5` anexado |
| Inputs em uso (amostra chart01 XAUUSD H1) | `AutoTrade=true`, `MagicNumber=2026001`, `AIUseGateway=true`, `AIGatewayUrl=http://127.0.0.1:9011/api/ai/predict`, `AIGatewayToken=""` (token lido do `.env` em runtime), `MinAIConfidence=60.0`, `AllowTradeWithoutAI=false`, `EnableRealAccountGuard=true` |
| Journal das ultimas 2 h | sem `4014`, `4060`, `5200`, `5202` e sem `[AI]` de erro; o EA esta em silencio por `DiagGate` (estado estavel). Unica linha de erro: `Notifications send request failed (connect to 194.164.179.242 failed, 10060)` = **P-05**, ja registado |

---

## 2. O defeito que este ciclo fecha

O ciclo 94 (P1.91) provou que **todo backtest feito ate hoje mediu um EA sem
ADX**. Ao fechar esse item ficou aberto, na mesma medicao, um segundo defeito
da mesma familia:

```
[AI] FILE EM FALTA | Data\prediction_XAUUSD.json
```

**Causa (medida, nao inferida):** dentro do Strategy Tester o sandbox de
ficheiros e `Tester\Agent-<ip>-<porta>\MQL5\Files\`, e o pipeline Python
escreve em `<terminal>\MQL5\Files\`. O ficheiro existia - `MQL5\Files\Data\
prediction_XAUUSD.json`, 1082 bytes, mtime `2026-11-04T22:28:52Z` - e era
**invisivel** para o backtest. Logo o portao de IA corria sempre sem previsao:
o backtest media um EA **diferente** do que corre nos 13 graficos.

Isto e o mesmo erro de metodo do P1.91: o instrumento de medicao nao estava a
medir o produto.

---

## 3. Correcao aplicada

`AI/AIConnector.mqh`, dentro de `LoadAIPrediction`:

1. **Resolucao de raiz.** Depois do fallback de nome normalizado, o ficheiro
   passa a ser procurado na raiz **LOCAL** e, se ausente, em **`FILE_COMMON`**.
   `FILE_COMMON` resolve para a pasta comum verdadeira tambem dentro do
   tester - facto ja medido na v1.2.45 (isolamento do `trade_history.csv`).
2. **`fileRoot` entra nas flags de `FileOpen`**, para o handle abrir a mesma
   raiz em que o ficheiro foi encontrado.
3. **A linha `[AI] LOAD` passa a publicar `ROOT=LOCAL|COMMON`.** A raiz deixou
   de ser invisivel no journal - foi exactamente essa invisibilidade que
   deixou o defeito passar por "fail-open" durante semanas.
4. **Ordem preservada:** em producao o ficheiro local existe, `fileRoot=0` e o
   comportamento e identico ao anterior. Nenhum limite, regra de entrada ou de
   saida, lote, alvo, stop, spread, preco ou parametro de risco foi tocado.

### 3.1. Copia em Common refrescada

`Common\Files\Data\prediction_XAUUSD.json` existia mas era de **25/08/2026**
(521 bytes) - 70 dias parado. Foi substituido pela copia do snapshot actual do
gateway (1082 bytes, `timestamp_utc=2026-11-04T22:28:22`, `signal=SELL`,
`confidence=63.6`, `model_id=XAU-30F-v4`, `feature_hash=5305081777808310`).

**Porque isto basta para o run:** a regra de idade e
`age = TimeGMT() - predUtc`, com `age<0` fixado a `0`. Num backtest que comece
em `2026.09.01`, o relogio simulado e **anterior** ao `predUtc` do snapshot,
logo `age` fica em `0` e a previsao e aceite durante toda a simulacao.

**Limitacao que fica escrita, para nao ser lida como virtude:** o sinal e
**congelado no instante do run**. Um backtest com este ficheiro mede "EA com o
sinal de 04/11 22:28", nao "EA com IA a evoluir barra a barra". `WebRequest`
com `Authorization: Bearer` nao funciona dentro do tester, portanto a
alternativa (IA real por barra) nao existe hoje. Qualquer resultado tem de ser
lido com essa ressalva.

---

## 4. HG-01: drift de versao encontrado e corrigido

| Sitio | Antes | Depois |
|---|---|---|
| `Enterprise/VersionManager.mqh` `EA_VERSION_STRING` | `1.2.136` | `1.2.137` |
| `XAU_AI_PRO.mq5` cabecalho | `v1.2.136` | `v1.2.137` |
| `XAU_AI_PRO.mq5` `#property version` | `"1.326"` | `"1.337"` |

`#property version` aceita so `xxx.yyy`, e a formula do projeto e
`minor*100 + patch`. Logo `"1.326"` = `2*100+126` = **v1.2.126**, oito versoes
atras do `EA_VERSION_STRING`. Era exactamente o descasamento que a regra HG-01
existe para impedir - o journal diria 1.2.136 e o binario dizia 1.2.126.

---

## 5. Validacao

```
Result: 0 errors, 0 warnings, 27713 ms elapsed, cpu='X64 Regular'
```

- `.ex5` reconstruido: **836 938 bytes**, `04/11/2026 20:05:18`
  (antes: 834 986 bytes, 19:53).
- Compilador: `metaeditor64.exe` build 6296, `/inc` na raiz `MQL5`.
- Log do compilador: `MQL5\Files\Temp\compile_v12137.log`.

---

## 6. Incidente registado (transparencia)

Ao procurar a ferramenta de compilacao, foi executado por engano
`DiagGateSelfTest.ex5` no grafico `22884787070177` (XAUUSD H1) via
`chart_add_script`. E um script de **auto-teste do DiagGate**: le e escreve
apenas o seu proprio ficheiro de resultado, nao envia, modifica nem fecha
ordens. Nao houve alteracao de estado de trading. O utilizador fica informado
porque a acao nao estava planeada.

---

## 7. O que fica aberto

1. **P-02 (DONO):** o slot continua ocupado pelo run das 18:08. Sem isso nao ha
   PF novo. Re-medir com **v1.2.137** quando libertar.
2. **Reanexar o EA nos 13 graficos** para o `.ex5` de `20:05:18` valer:
   compilar nao reanexa. Enquanto nao for feito, os graficos correm o build
   anterior em memoria. (A correcao P1.92 nao muda a producao; a P1.91 tambem
   nao muda o caminho com mercado aberto, mas o build deve ser o mesmo.)
3. **Conta real continua recusada.** O numero que existe - PF 0,6206, acerto
   41,4%, 10-11 perdas seguidas - foi medido num build **sem ADX**, logo nao
   descreve este EA. Nao serve nem para autorizar nem para recusar com
   precisao: serve para recusar por prudencia ate haver medicao valida.
4. **P-05:** notificacoes nao saem do terminal (rede/credenciais).

---

## 8. Ficheiros tocados

- `MQL5\Experts\XAU_AI_PRO\AI\AIConnector.mqh` - resolucao LOCAL/`FILE_COMMON`
  e `ROOT=` na linha `[AI] LOAD`.
- `MQL5\Experts\XAU_AI_PRO\Enterprise\VersionManager.mqh` - `1.2.137` +
  entrada de changelog.
- `MQL5\Experts\XAU_AI_PRO\XAU_AI_PRO.mq5` - cabecalho e `#property version`.
- `MQL5\Common\Files\Data\prediction_XAUUSD.json` - copia refrescada (dado
  gerado, fora do controlo de versao).
- `PROGRESS.md`, `PENDENCIAS.md`, `CONVERSAS.md`, `Tools\HANDOFF.md` e este
  documento.
