# XAU_AI_PRO — Protocolo de Conclusão do Endurance (ETAPA 20.6)

Data inicio oficial: 2026-08-25 19:08:38 (ultimo OnInit, build v1.2.1-crashfix,
ex5 402736B @ 17:57) · Status: EM CURSO

## 1. JANELAS E MARCOS
| Fase | Build | Inicio | Marcos |
|---|---|---|---|
| E1 (24h) | v1.2.1-crashfix | 25/08 19:08 | 8h=26/08 03:08 · 24h=26/08 19:08 |
| E2 (72h+) | v1.2.2-opt (apos aplicacao) | ~26/08 20:00 | 48h=28/08 · 72h=29/08 |
| E3 (7d/30d) | v1.2.2-opt | pos-E2 | 7d=~03/09 · 30d forward continuo |

## 2. CRITERIOS PASS POR CHECKPOINT
[PASS] exige TODOS:
- [ ] 0 reinicios nao planejados (OnInit sem acao manual)
- [ ] 0 SIGNAL ERROR / invalid handle / INIT FAILED / crash
- [ ] [ADX] CopyBuffer failed apenas esporadico (<10/dia, throttle ativo)
- [ ] Heartbeat ForwardHeartbeat presente no log
- [ ] DD diario < 5% e equity protection nao disparada de forma indevida
- [ ] Trades (se houver) com SL/TP corretos e lot <= configurado
- [ ] Reconciliacao: nenhuma posicao orfa/desconhecida

[FAIL imediato] qualquer um:
- SIGNAL ERROR recorrente (>3/hora)
- Travamento/crash da thread ou terminal
- Drawdown > MaxDrawdown config
- Ordem enviada fora do padrao (lot/magic errados)

## 3. PROCEDIMENTO APOS 24H (E1 -> E2)
1. Validar checkpoint 24h (26/08 ~19:08) = PASS
2. Sincronizar fix v1.2.2-opt p/ data folder:
   - Release/v1.2.0/EA/Core/PositionManager.mqh  -> MQL5\Experts\XAU_AI_PRO\Core\
   - Release/v1.2.0/EA/Management/BreakEven.mqh  -> MQL5\Experts\XAU_AI_PRO\Management\
   (hashes devem bater com commit f891f71)
3. F7 no MetaEditor (0 erros/0 warnings) -> novo .ex5
4. Reattach nos 6 graficos (FORWARD_DEMO_REATTACH_v120.md)
5. Novo inicio de janela E2 = ultimo OnInit registrado
6. Registrar na tabela abaixo

## 4. LOG DE CHECKPOINTS (preencher)
| # | Data/Hora | Uptime | ErrosCrit | Trades | P/L | DD% | no-changes | Result |
|---|---|---|---|---|---|---|---|---|
| CP0 | 25/08 20:33 | 1h25m | 0 | 3C/1A | +0.78 flut | 0.23 | 913* | PASS (*acumulado de antes da janela) |
| CP1 | 26/08 03:08 | 8h | | | | | | |
| CP2 | 26/08 19:08 | 24h | | | | | | |
| CP3 | pos-reattach v1.2.2 | | | | | | | reset janela |
| CP4 | 29/08 | 72h | | | | | | |
| CP5 | 03/09 | 7d | | | | | | |

## 5. COMO EU (assistente) EXECUTO UM CHECKPOINT
Ler MQL5\Logs\<YYYYMMDD>.log do data folder D0E8209F... e medir desde o
ultimo OnInit: reinicios, erros criticos, ADX failed, trades, ultima linha
P/L, contagem no-changes. Colar resultado neste documento via commit.

## 6. CONCLUSAO
Endurance concluido = CP2 PASS (E1) + CP4 PASS (E2 72h) + reconciliacao
Broker x AuditLog x CSV sem divergencias. Entao liberar gate parcial para
decisao de capital (ainda sujeito ao PF>1 economico).
