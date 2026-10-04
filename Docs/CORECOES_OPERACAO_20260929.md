# XAU AI PRO — Correcoes de Operacao e Abas 2026-09-29 (tarde)

**Foco:** o que impedia o operador de operar. Todos os achados sao reproduzidos
com comando, nao por leitura de tela.

---

## 1. Operacao automatica: 3 bugs empilhados

**Sintoma na tela:** `erro no ciclo; tentando de novo no proximo intervalo`

### 1.1 `_mt5_candles` devolvia um dict, nao a lista

`backend/auto_engine.py` fazia `pd.DataFrame(_mt5_candles(...))`. A funcao
devolve a RESPOSTA canonica (`ok`, `status`, `provenance`, `candles`, ...):

```
ValueError: All arrays must be of the same length
```

E o mesmo bug que quebrou o backtest e ja foi corrigido em
`fastapi_gateway._ai_predict_sync`. No motor, o `except Exception` generico
engolia a excecao e virava a mensagem generica — **o motor nunca chegou a
avaliar um sinal**.

**Correcao:** extrai `candles` da resposta, valida a lista e registra a causa
(`type` + `mensagem`) no historico de decisoes.

### 1.2 `ligar()` aceitava simbolo e timeframe vazios

O motor nascia com `simbolo=''`, `timeframe=''`. `_trava_instrumento` devolvia
cedo, `_mt5_candles("", "", 600)` falhava, e o operador via "erro no ciclo" sem
saber que faltava escolher o ativo.

**Correcao:** `ligar()` recusa com motivo legivel:

```
"escolha o ativo (simbolo) e o timeframe antes de ligar a operacao automatica"
```

### 1.3 A sessao do MT5 nao era inicializada

`_ensure_mt5()` (que chama `initialize()`) era invocado em **um unico lugar** do
gateway. Em qualquer processo novo — como a thread do motor — `copy_rates`
devolvia `None` e a resposta saia `terminal_disconnected`, **mesmo com o MT5
aberto e logado**.

**Correcao:** `_mt5_candles` verifica a sessao e conecta antes. A guarda usa
`getattr(..., "initialize", None)`: os dubles de teste injetam um modulo MT5
minimo, e sem isso os 7 testes de candles quebraram com `AttributeError`.

### Prova

Antes:

```
resposta ok = False | status = unavailable | code = terminal_disconnected
candles = 0
```

Depois:

```
600 candles reais
inferir -> disponivel = True | sinal = SELL | conf = 37.5
modelo = random_forest_XAUUSD_H1
```

---

## 2. Tabela de planos: 5 rotas na porta errada

**Sintoma na tela:** aba de Planos "generica, sem vida, nao chama atencao".

`SubscriptionPanel.tsx` chama 5 rotas, e o frontend fala com o gateway local
(9001, ver `apiBase()`). Todas as 5 viviam **so** no `fastapi_gateway` (9003):

| Rota                          | 9001    | 9003 |
| ----------------------------- | ------- | ---- |
| `/api/subscriptions/plans`    | ausente | sim  |
| `/api/subscriptions/me`       | ausente | sim  |
| `/api/social/strategies`      | ausente | sim  |
| `/api/subscriptions/activate` | ausente | sim  |
| `/api/social/follow`          | ausente | sim  |

A tela recebia 404 nas cinco chamadas e renderizava vazio. O conteudo existia e
esta bom:

```
PLANOS: 3  (free USD 0 | pro USD 49 | business USD 149)
ESTRATEGIAS: 3 (Trend Filter | Mean Reversion | Session Breakout)
ASSINATURA ATUAL: free | paper_trade | live=False
```

**Correcao:** as 5 rotas foram adicionadas ao `mt5_gateway`, no padrao do
projeto. Todas com `live_execution: False` e `withdrawals_enabled: False`
fixos: escolher um plano nao habilita ordem nem saque.

Detalhe: `follow_strategy(strategy_id, user_id=None)` — o segundo argumento e o
usuario, nao um booleano "seguindo". Passar `bool(...)` transformava o id em
`True/False` e quebrava o estado.

---

## 3. Calendario economico: **nao e tempo real** (PENDENTE DE DECISAO)

Este NAO foi corrigido, e o motivo precisa ser explicito.

`app/economic_calendar.py` tem uma tabela local de **16 eventos fixos** que se
repete semanalmente, com **horarios estimados** e sem previsao/realizado:

```python
{"title": "Nonfarm Payrolls (NFP)", "currency": "USD", "impact": "alto",
 "day": 4, "hour_utc": 12, ...}
```

NFP todo dia 4 as 12:00 UTC, FOMC toda quarta 18:00 UTC. O payload declara isso
em `disclaimer`, e isso esta correto — mas **uma tela de mercado profissional
nao pode mostrar horario inventado como se fosse publicado**.

O que falta para ser profissional: data exata de cada evento, previsao,
realizado e revisao. Isso vem de uma API externa (fonte de calendario
economico) ou do broker. **Requer sua decisao**, porque significa:

- escolher fornecedor e o que fazer quando a API cair;
- o app passa a depender de rede para essa aba;
- a regra do projeto exige rotular a procedencia dos dados.

---

## 4. Verificacao

| Item                               | Resultado                                   |
| ---------------------------------- | ------------------------------------------- |
| `pytest -q tests`                  | **619 passed**                              |
| `npx tsc --noEmit`                 | **exit 0**                                  |
| `candles_mt5_para_dataframe`       | novo helper unico de traducao MT5 -> treino |
| Gateway reconstruido (PyInstaller) | 29/09 18:12                                 |
| MQL5                               | intocado                                    |

### Endurecimento

`candles_mt5_para_dataframe()` centraliza a traducao de colunas que ja falhou em
tres lugares isolados (previsao do gateway, backtest, motor automatico). Um
ponto so agora.

---

## 5. Pendencias

1. **Calendario em tempo real** — requer decisao de fornecedor (secao 3).
2. **Aba Operacao**: o painel ja tem par (ativo + periodo), limites, ON/OFF e
   historico de decisoes. Falta fundir EA + modelo + sinal numa leitura so, e
   explicitar banca/alavancagem/TP-SL em linguagem de operador.
3. **Robo Resetado**: o `mt5-gateway` caiu duas vezes durante os testes porque
   ~33 requisicoes HTTP seguidas saturaram a tabela de sockets em `TIME_WAIT` na
   porta 9001. O app nao detecta que o filho morreu — o log continua dizendo
   "core spawnado com sucesso". Falta health check com reinicio automatico.
