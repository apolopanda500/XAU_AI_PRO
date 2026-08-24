# PLANO DE TESTE DE ENDURANCE - v1.2.0-RC1
## ETAPA 15.9

**Data:** 24/08/2026 | **Ambiente:** DEMO (forward test em andamento)

---

## Coletor

```
python Tools/endurance_monitor.py          # continuo (5 min/ciclo)
python Tools/endurance_monitor.py --once   # amostra unica
```

Saida: Logs/endurance_metrics.jsonl (append-only, UTC).
Metricas por amostra: heartbeat EA (system_status.json idade),
dataset_bytes + delta, predictions_fresh (<600s),
memoria terminal64/python (psutil opcional).

Instalacao opcional para memoria/CPU: pip install psutil

## Janelas e criterios de aprovacao

| Janela | Inicio | Criterios PASS |
|--------|--------|----------------|
| 24h    | apos reload do EA | heartbeat OK >= 99%; sem crescimento de memoria terminal >10%; dataset crescendo em horario de mercado |
| 72h    | +48h | idem + 0 travamentos do terminal; latencia de decisao estavel |
| 7 dias | +4d | idem + reconexoes auto-recuperadas (ConnectionGuard); logs sem ERROR crescente |
| 14 dias| +7d | tendencia de memoria plana (regressao <5%/semana); trades auditados consistentes |
| 30 dias| +16d | estabilidade global; backup automatico validado; rollback testado |

## Falha = qualquer um:
- ea_heartbeat_ok falso > 2% das amostras da janela
- Crescimento monotonicos de memoria (leak) confirmado em 2 janelas
- Travamento/restart manual do terminal ou do python engine
- Perda de dados de risco diario (RiskHub GlobalVariables)

---
*Documento oficial - ETAPA 15.9*
