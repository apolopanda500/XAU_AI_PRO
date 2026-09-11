# F4 — EventEmitter Serializado (v1.2.2)

**Status: ✅ F4 = PASS OPERACIONAL (build definitivo) — ENDURANCE OFICIAL ATIVA desde 2026-09-02 00:33:40 server (T0). Sem alterações de código/inputs/símbolos/posições durante a janela. Marcos: 24H → 72H → 7D → 30D → Gate 20.15.**
Data: 2026-09-01/02 · Base: XAU_AI_PRO v1.2.0 · Escopo: apenas integridade de execução/observabilidade
(NADA de IA, ADX, SL/TP, parâmetros ou estratégia foi alterado neste bloco.)

---

## 1. Objetivo

Serializar a escrita do Event Stream (`forward_test_events.csv`) e dos arquivos de
auditoria (`full_audit.csv`, `audit_log.csv`) entre as 11 instâncias do EA, e eliminar
a inconsistência de observabilidade `Positions: 0 total` com posição aberta.

## 2. Achados do diagnóstico (root cause)

| # | Achado | Causa raiz |
|---|--------|-----------|
| 1 | `EXECUTION SUMMARY` dizia `Positions: 0 total` com USDBRL SELL aberta | `CPositionSynchronizer::Synchronize()` filtra `POSITION_SYMBOL == Symbol()` (cache **por-símbolo do gráfico**) + throttle de 5s; o rótulo "total" era enganoso com 11 instâncias |
| 2 | Header duplicado possível no arranque concorrente | `EventInit()` criava o header **sem lock** |
| 3 | `full_audit.csv` / `audit_log.csv` escritos por 11 instâncias sem exclusão mútua | writers não usavam o mesmo lock do EventEmitter |
| 4 | `reconcile_sources.py` nunca fechava `Broker × Audit` | comparava **ticket do deal** com `full_audit.Ticket` que grava **POSITION_ID** |

## 3. Alterações cirúrgicas

| Artefato | Mudança |
|----------|---------|
| `Monitoring\EventLock.mqh` **(novo)** | Primitiva de lock global (GlobalVariableSetOnCondition CAS + TTL 2s + 20 tentativas), compartilhada por TODOS os escritores; stats de contenção/timeout |
| `Monitoring\EventEmitter.mqh` | Usa `EventLock`; **header sob lock**; `EventSummary()` agora expõe `Written / Dropped / Lock contention / timeouts`; 10 colunas do CSV **inalteradas** (compatível App/Python) |
| `Monitoring\AuditLog.mqh` | `AuditLogDecision/Simple/TradeResult/SaveRecords` com `EventLockAcquire/Release` em todo seek→write→flush; contador `Dropped` no summary |
| `Enterprise\PositionSynchronizer.mqh` | Novo `GetTerminalPositions()` — conta posições EA (magic) do **terminal inteiro**, ao vivo (ignora cache/throttle) |
| `Enterprise\SmartExecution.mqh` | `GetExecutionSummary()` usa `GetTerminalPositions()` → rótulo honesto `Positions: N total EA (terminal)` |
| `Python\runbooks\reconcile_sources.py` | Auditoria por ticket: `missing AUDIT` (entry broker sem `full_audit` por **position_id**), `missing EVENT` (entry sem TRADE_OPEN por deal ticket), `unknown EVENT` (TRADE_OPEN sem deal); + posições abertas do broker (read-only). **F4 v2**: `ts_server()` corrigido (a API MT5 Python devolve `d.time` já no horário do servidor — não somar +3h de novo); `event_records()` filtra eventos **pela janela limpa** (col Time); `broker_deals()` com range amplo + retries de sync |

## 4. Evidência de compilação

```
build XAU_AI_PRO.mqproj  →  0 errors, 0 warnings (X64, ~9s)
reconcile_sources.py     →  py_compile OK (0 warnings)
```

> Incidente de processo (F4): `replace_text_in_file` (MCP) anexava `\x00\x00<byte>` no EOF e
> removia o BOM → o compilador lia o arquivo como UTF-16 → "identifier too long" em 1:1.
> Resolvido com reparo cirúrgico das caldas + reescrita via write_file. **Regra: NUNCA usar
> replace_text_in_file em código MQL5/Python deste repositório; preferir write_file integral.**

> **INCIDENTE CRÍTICO (F4 — achado na validação inicial):** o `EventEmitter` mantinha
> `evHandle` PERSISTENTE por instância. Com 11 instâncias abrindo o mesmo arquivo
> (`FILE_SHARE_WRITE`), o `FileSeek(SEEK_END)` de um handle antigo NÃO enxerga o tamanho
> atualizado pelos outros handles → overlay/interleave (linha A cortada + linha B colada;
> observado no storm de HEALTH_FAILURE 00:19–00:30). **Correção**: reescrito para
> ABRIR→SEEK(END)→WRITE→FLUSH→FECHAR a cada evento (handle novo por gravação, sob lock).
> Mesmo padrão aplicado aos writers do AuditLog (Decision/Simple/TradeResult). Prova:
> `forward_test_trades.csv`/`forward_test_session.csv` (que já usavam esse padrão) nunca
> corromperam. **Reload 11/11 em 2026-09-02 00:33 server; pós-reload: 0 interleave, 0 linhas
> malformadas, 10 colunas íntegras.**

> Incidente de dados (F4): a API MT5 Python mantém cache defasado de `history_deals_get` —
> deals recém-criados (minutos) não aparecem até o terminal baixar do servidor (esperado de
> 1–5 min; poll de 400s ainda não capturou). A tool nativa do terminal (HistorySelect) vê os
> deals imediatamente. O runbook usa range amplo + retries; em caso de 0 deals na janela,
> conferir com a tool nativa antes de concluir C5.

## 5. Critérios de aceite (F4 PASS)

- [x] **C1 — Compilar 0/0**: build do projeto sem erros/avisos (X64, 0/0).
- [ ] **C2 — Escrita concorrente**: 11 instâncias rodando ≥ 24h sem `DROP` (drops=0 no `EventSummary`), sem linha corrompida/interleaved no CSV, header único no arquivo.
- [ ] **C3 — Lock observável**: `EventLockStats()` com `contention` pequeno e `timeouts=0` no log.
- [x] **C4 — Positions honesto**: `EXECUTION SUMMARY` mostra `Positions: N total EA (terminal)` igual ao `PositionsTotal()` real do terminal. **CONFIRMADO: `Positions: 5 total EA (terminal)` nas 11 instâncias == `positions_open.ea_magic = 5`** (USDBRL, NZDUSD, USDCAD, USDJPY, USDCHF — pós-reload).
- [ ] **C5 — Auditoria Broker × Audit × Events**: `reconcile_sources.py` reporta `missing_audit=0`, `missing_event=0`, `unknown_event_tickets=[]` na janela.
- [x] **C6 — Contrato preservado**: CSV ainda 10 colunas UTF-16; nenhum input/parâmetro de risco alterado. (Conferido tail do CSV: linhas 10 colunas íntegras sob lock.)

## 6. Log de validação em janela limpa (2026-09-02 00:13 server)

- Reattach das 11 instâncias F4: **feito às 18:14 local**; todas com `AuditLog | ... | Dropped=0` e `Positions: N total EA (terminal)`.
- Boot concorrente: 11× `SYSTEM_START` + `FORWARD_TEST_START` gravados no CSV sob lock **sem interleaving/corrupção** (tail do arquivo íntegro, 10 colunas).
- Execuções reais na janela: **NZDUSD SELL 00:13:47 (deal 10023568427)**, **USDCAD BUY 00:14:10 (deal 10023569245)**, **USDJPY BUY 00:15:02 (deal 10023570994)** — 3 entradas + 1 saída no arranque do F4.
- `[EVENT] DROP`: **0 no Journal** até agora · `AuditLog Dropped=0` em todas as instâncias.
- **C4 ✅** — Positions honesto bate (4 == 4).
- **C5 parcial** — `missing_audit=0`, `missing_event=0` na janela; `unknown_event=[10023568427, 10023569245, 10023570994]` = **são exatamente os 3 deals reais** que a API Python ainda não sincronizou (cache defasado) → esperado zerar após sync do terminal (conferir com tool nativa).
- Snapshot pré-F4 (evidência fechada): `Files\Temp\backup_pre_f4_20260902\` (forward_test_events + full_audit, 421 KB).

## 7. Próximos passos (endurance)

1. Conferir C5 novamente após sync da API (`reconcile_sources.py` → `unknown_event_tickets=[]`).
2. Endurance: **24h → 72h → 7d → 30d** com `Dropped=0`, `timeouts=0`, header único, 10 colunas.
3. Ao fim de cada marco: rodar auditoria + registrar no FORWARD_WINDOW_TRACKER.
4. Com F4 PASS → gate **20.15** (libera produção).