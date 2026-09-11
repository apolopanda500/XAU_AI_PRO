# XAU_AI_PRO — PROTOCOLO DE RECONCILIAÇÃO (ETAPA 20.8)

> Preparado: 2026-08-28 18:45 UTC | Janela de referência: início 28/08 18:35 UTC (21:35 servidor)
> Regime: **passivo** — documento de contrato; nenhuma execução sobre runtime.

---

## 1. FONTES E CONTRATOS

| # | Fonte | Arquivo / origem | Encoding | Papel |
|---|---|---|---|---|
| S1 | Broker | MT5 History (deals magic 2026001) | n/d | **Verdade de execução** (ticket, px, vol, profit) |
| S2 | AuditLog (novo) | Terminal `MQL5\Files\Data\full_audit.csv` | ANSI | Registro por-deal do EA |
| S3 | EventStream | Terminal `MQL5\Files\Data\forward_test_events.csv` | **UTF-16 LE + BOM, linhas `\r\r\n`** | Eventos e transições de estado |
| S4 | Backend | `system_status.json` + `dataset.csv` | JSON/CSV | Heartbeat + coleta |
| S5 | Telemetria | Common `Files\Data\forward_test_session.csv` | ANSI | Snapshot ConnGuard (não é contrato de trade) |

**Fonte canônica das operações:** S1 (broker). S2 e S3 devem derivar de S1 sem divergência.

---

## 2. CHAVES DE CASAMENTO (MATCH KEYS)

| Par | Chave primária | Chave secundária |
|---|---|---|
| Deal de entrada | `order_id` (ordem) / `position_id` | symbol + open_time + volume + price |
| Deal de saída | `order_id` (ordem de fechamento) | position_id + close_time + volume |
| Evento no stream | `Ticket` (col. 5) | symbol + TF + Event + Message |
| Linha full_audit | `Ticket` (col. 2) | Time + Symbol + Price |

Regra de igualdade de tempo: comparar sempre em **horário do servidor (UTC+3)** — eventos gravam
servidor; broker history também usa servidor. Nunca misturar com horário local/UTC sem conversão.

---

## 3. REGRAS DE DEDUPLICAÇÃO

1. **full_audit.csv** pode conter linhas repetidas para o mesmo ticket (observado neste projeto;
   causa: múltiplos EAs/charts escrevendo + reaproveitamento de deal). Tratar como **duplicata
   justificada se ticket+time idênticos** → manter 1.
2. **forward_test_events.csv**: eventos `SYSTEM_START/FORWARD_TEST_START` repetidos por reanexação
   são esperados (um por chart/símbolo) → não são duplicatas.
3. **Broker**: deals com mesmo `order_id` em symbols diferentes **não** são duplicatas (ex. pares
   com `#`/`c`/`m` no mesmo instrumento — não aplicável ao conjunto atual, mas registrar).
4. Duplicata **não justificada** = mesmo ticket com valores divergentes (px/vol/profit) → **mismatch**.

---

## 4. VERIFICAÇÕES POR OPERAÇÃO (ciclo OPEN → CLOSE)

Para cada `position_id` da janela limpa (início 28/08 21:35 servidor):

| Passo | Campo | Origem S1 | Confere com S2/S3 | Tolerância |
|---|---|---|---|---|
| 1 | OPEN ticket | order_id (entry) | Ticket | exato |
| 2 | símbolo | symbol | Symbol | exato |
| 3 | volume | volume | Volume | exato |
| 4 | preço | price_open (deal in) | Price | exato / 1 ponto |
| 5 | SL/TP | stop_loss/take_profit | (evento) | exato |
| 6 | execução | filling/retcode | exec_result/retcode | sem erro |
| 7 | CLOSE ticket | order_id (exit) | Ticket | exato |
| 8 | motivo saída | reason (SL/TP/Expert) | Exit_Reason | exato |
| 9 | profit | profit (deal out) | Result/Profit | ± 0,01 (swap/commission à parte) |
| 10 | tempo | open_time/close_time | Time | ± 1 s |

**Posição órfã:** posição no broker sem linha em S2 OU sem evento OPEN em S3 → **blocker** na 20.8.

---

## 5. CRITÉRIOS DE SAÍDA (GATE 20.8)

- ❌ **missing:** trade no broker sem registro em S2/S3 → 0
- ❌ **duplicata não justificada:** > 0
- ❌ **mismatch:** campo divergente fora da tolerância → 0
- ❌ **posição órfã:** > 0
- ✅ Resultado: **0 / 0 / 0 / 0**

---

## 6. PROCEDIMENTO (checkpoints 24h / 72h / 7d / 30d)

1. Exportar deals do broker (magic 2026001, janela limpa) — via API MT5 (passivo, leitura).
2. Ler `full_audit.csv` e `forward_test_events.csv` com encodings corretos.
3. Normalizar horários para servidor (UTC+3) e aplicar dedup (§3).
4. Casar por position_id e aplicar tabela §4.
5. Emitir relatório: counts, divergências (com evidência), barra de gate.
6. Registrar no `FORWARD_WINDOW_TRACKER.md` (aba RECON).

---

## 7. PENDÊNCIAS CONHECIDAS PARA A 20.8 (não corrigir agora)

- `full_audit.csv` tem linhas duplicadas (dedup requerido).
- `audit_log.csv` (Common) é **legado** (Fase 9) e será aposentado; usar só `full_audit.csv`.
- `forward_test_trades.csv` (Common) está **vazio** → não participa da 20.8; candidato a remoção em v1.2.1.
- Encoding UTF-16 + `\r\r\n` no event stream: leitores devem usar `encoding='utf-16'` e limpar `\r`.