# Acto ALFA-002 — Decisão do DONO: crescimento sem stop na banca baixa (23/11/2026)

## Decisão do DONO (verbatim)
> "eu sou o DONO, vou mandar e fazer sim minha decisão agora mudou, vou manter minha estratégia nova do crescimento sem stop banca baixa ok"

## Regra em vigor (confirmada no código, v1.2.223)
- `EnableGrowthPolicy = true` (Core/Config.mqh:2070)
- `GrowthSmallLimitUsd = 50.0` — degrau pequena/média
- `GrowthStopMinBancaUsd = 100.0` (Config.mqh:2101) — **abaixo de US$ 100, a proteção NÃO arma**
- `GrowthSmallTargetUsd = 0.70`, `GrowthSmallLotTarget = 0.01` — alvo/lote da banca pequena
- Comportamento: **banca baixa = CRESCIMENTO PURO**, sem stop a subir. O SL da entrada continua (proteção obrigatória da ordem); o que não existe é um stop levantado acima da entrada.
- Jornal (v1.2.220, 11:05:07): `[GROWTH] stop por degrau | banca=PEQUENA | protecao=NAO`.

## O que este acto NÃO faz
- Não liga o motor automático (`ativo=false` medido).
- Não envia ordens.
- Não altera inputs de risco, lote, alvo, spread, RR ou confiança de IA.
- Não toca nas posições abertas do DONO.
- Não cria automação no Windows (o DONO vetou tarefas agendadas).

## Estado do gateway (ALFA-001)
- Gateway 9027 com token de 68 caracteres (raiz `.env`), PID 9680, health 200.
- `/api/ai/predict?symbol=ETHUSD&timeframe=H1` → `available:true, signal:BUY, confidence:41.2` (inferência real).

## Pendências que continuam (fora do código)
- Rede/ISP: retransmit 4,18%, ping 200 ms, 3 quedas em 5 min → SAFE_MODE intermitente.
- Banca real ~$4,51–6,60: `[TRADE BLOCK] SAFETY | Amplitude 20,10%` — bloqueio de risco legítimo.
- GATE_REAL 3/12, PF 0,66, forward 0/30 — operar em real continua reprovado pelas regras escritas.

O DONO reassumiu a decisão e confirmou a estratégia de crescimento sem stop na banca baixa; este agente regista e mantém o motor desligado até nova ordem explícita de operação.
