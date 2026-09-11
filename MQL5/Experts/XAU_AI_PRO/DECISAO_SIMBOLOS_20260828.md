# XAU_AI_PRO — DECISÃO DE GOVERNAÇA: CONJUNTO DE SÍMBOLOS (28/08/2026)

> Data/hora: 2026-08-28 18:35 UTC (15:35 local) | Autor do registro: MetaTrader Assistant
> Decisão do usuário (explícita): **NÃO remover símbolos — manter todos, acrescentar se necessário, e continuar os testes em demo.**

---

## 1. O QUE MUDA NO PLANO 20.5

O plano anterior previa fechar 5 charts (USDSEK, GBPUSD, USDCAD, USDJPY, USDCNH) para
voltar aos 6 oficiais. **Esta ação está CANCELADA por decisão do usuário.**

O conjunto ativo de forward passa a ser oficialmente **os 11 símbolos já anexados**:

| # | Símbolo | TF | EA (magic 2026001) |
|---|---|---|---|
| 1 | XAUUSD | M5 | anexado |
| 2 | EURUSD | M5 | anexado |
| 3 | USDBRL | M5 | anexado |
| 4 | NZDUSD | M5 | anexado |
| 5 | USDCHF | M5 | anexado |
| 6 | AUDUSD | M5 | anexado |
| 7 | USDSEK | M5 | anexado |
| 8 | GBPUSD | M5 | anexado |
| 9 | USDCAD | M5 | anexado |
| 10 | USDJPY | M5 | anexado |
| 11 | USDCNH | M5 | anexado |

Configuração de entrada observada (charts): Magic 2026001 · SL 300 pts · TP 600 pts ·
EMA 50/200 · RSI 14/45/55 · EnableNewsFilter=0 · EnableAIFilter=0 · EnableMultiSymbol=0
(cada chart opera o próprio símbolo) · lote 0.01.

---

## 2. QUALIFICAÇÃO DE RISCO DO CONJUNTO AMPLIADO

- **Mantido fora (regra vigente):** XAGUSD e índices (US30/US500/USTEC). Motivo: SL 300
  pontos fixo NÃO é normalizado por símbolo; XAG 0.01 lote = **−15,00/trade** (5 saídas =
  −75,00 = 79% do gross loss 24–28/08). Reativar **somente** após RiskEngine com
  normalização por símbolo validada (v1.3+).
- **Conjunto atual (11 símbolos):** todos FX + ouro, com perda máx. por trade no lote 0.01
  entre ~−1,5 e ~−3,0 USD. Aceitável para observação em demo, com monitoramento.
- **Novos símbolos:** se o usuário quiser acrescentar pares FX adicionais, pode; metais e
  índices seguem bloqueados até a normalização de risco.

---

## 3. MARCADOR DA JANELA LIMPA (CRÍTICO PARA O GATE FINANCEIRO)

- **Início oficial da janela limpa: 2026-08-28 21:35 horário do servidor (18:35 UTC).**
- Todo o histórico anterior (24–28/08; deals magic 2026001; PF 0,12 acumulado / 0,58 ex-XAG)
  pertence à janela **contaminada** (14 charts + XAGUSD) e NÃO conta para o gate.
- Métricas do gate (PF, Win Rate, Expectancy, Max DD, Sharpe) passam a ser calculadas
  **exclusivamente a partir deste marcador** e consolidadas por dia (DAY 01, DAY 02...).
- Posições abertas neste momento (3) seguem com SL/TP e serão resolvidas naturalmente:
  GBPUSD SELL #10263362670 · USDCHF BUY #10263362709 · USDCAD BUY #10263363321.
  Nenhuma ação manual; entram como evidência de execução da janela.

---

## 4. ESTADO DO ECOSSISTEMA (verificado 18:35 UTC)

| Componente | Evidência | Status |
|---|---|---|
| EA nos 11 charts | chart list (11 charts anexados) | ✅ ativo, operando |
| Algoritmos (botão) | `algo_trading_enabled=true` (system_status.json) | ✅ ON |
| Backend/Python | `dataset.csv` 173.162.556 B @18:35:05; `system_status.json` @18:35:10 | ✅ ativo |
| Eventos | `forward_test_events.csv` @18:29 (UTF-16, Module=EA, v1.2.0-RC1) | ✅ gravando |
| Telemetria ConnGuard | `forward_test_session.csv` @18:29 (Common) | ✅ gravando |
| Health | `system_status.json` → HEALTHY, algo ON, risco OPEN, IA NEUTRAL (conf 37,79) | ✅ |

---

## 5. PENDÊNCIAS REGISTRADAS (NÃO BLOQUEIAM A CONTINUIDADE)

1. **Reattach do ex5 fresco** (higiene de build): os charts podem estar rodando binário
   anterior em memória. Reanexar o `XAU_AI_PRO.ex5` compilado do baseline nos 11 charts é
   recomendado **quando conveniente** — NÃO remove símbolo nenhum. Sem isso, a janela segue
   válida, mas a 20.10 precisará de hash do ex5 == binário compilado.
2. **Hash do ex5** no manifesto está stale (165e73f6 vs 9303e383 do baseline 20.1);
   `RELEASE_MANIFEST.md` modificado. Será re-empacotado na 20.10 com hashes frescos.
3. **Duplicidades** em `full_audit.csv` e multiplexação de escrita entre 11 EAs → tratado na
   20.8 (reconciliação) como pendência de qualidade de evidência.
4. **Contratos:** `forward_test_events.csv` = fonte oficial de eventos;
   `forward_test_session.csv` = telemetria de saúde (ConnGuard); `forward_test_trades.csv`
   (Common) = legado **vazio** → candidato a descontinuação (v1.2.1), sem quebra de
   compatibilidade.

---

## 6. REGRAS DA FASE (inalteradas)

- **Congelamento do EA:** nenhuma alteração no núcleo (SignalCore/DecisionEngine/
  ValidationEngine/RiskEngine/ExecutionEngine) durante 20.5→20.11.
- **Sem otimização para maquiar PF:** gate financeiro depende de evidência estatística em
  janela limpa (PF ≥ 1,0), não de ajuste forçado.
- **Pipeline:** 20.5 (reattach + janela limpa) → 20.6 (endurance 24h/7d/30d) → 20.7
  (recovery) → 20.8 (reconciliação) → 20.10 (release) → 20.11 (production gate).

## 7. PRÓXIMOS PASSOS (a partir daqui)

1. Manter operação demo nos 11 símbolos, sem tocar em código.
2. Coletar telemetria contínua e registrar **DAY 01 = 28/08** (relatório diário automático:
   trades, win rate, PF, expectancy, max DD, AI accuracy, rejeições, uptime, recoveries).
3. Conferir o journal do MT5 periodicamente: sem "Falha ao copiar RSI", [PIPELINE] ativo.
4. Próximo marco: 20.6 Fase A (24h) — consolidação em 29/08 18:35 UTC.