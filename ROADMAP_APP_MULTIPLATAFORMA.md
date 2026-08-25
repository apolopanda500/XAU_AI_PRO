# XAU_AI_PRO — Roadmap App Multiplataforma (PC + Android)

Data: 25/08/2026 · Status: PLANEJAMENTO (pos-endurance 20.3)

## 1. VISÃO
Aplicativo cliente do XAU_AI_PRO para **Android e PC**, oferecendo
monitoramento em tempo real e controle remoto do robô que opera no
MetaTrader 5.

## 2. RESTRIÇÃO FUNDAMENTAL
O EA (.ex5) roda EXCLUSIVAMENTE em MT5 Windows desktop. O app NAO porta
o robô — ele e CLIENTE de uma API na nuvem alimentada pelo EA.

Producao recomendada: VPS Windows 24h rodando MT5 (barato, ~US$10-30/mes).

## 3. ARQUITETURA ALVO
```
[PC/VPS Windows: MT5 + EA] --push HTTP--> [API Cloud] <--HTTPS-- [Apps]
      |                                     - FastAPI (existente)     Android
      |-- forward_test_events.csv           - DB (Postgres/Turso)     PC/Desktop
      |-- prediction_*.json                 - JWT auth                iOS (futuro)
      v                                     - Sentry (existente)
[Sentry bridge (existente)]                 - CI/CD (GitHub Actions, ja temos)
```

## 4. STACK RECOMENDADA
| Camada | Escolha principal | Alternativas |
|---|---|---|
| App unico multiplataforma | **Flutter (Dart)** -> Android + Windows (+iOS futuro) | Tauri v2 (Rust+Web); React Native; PWA |
| API | FastAPI existente (Backend/api.py) adaptado p/ nuvem | — |
| DB | Turso/Supabase (serverless-friendly) | Postgres Railway |
| Push | Firebase Cloud Messaging | OneSignal |
| Auth | JWT + refresh (endpoints /login ja esbocados na api.py) | Supabase Auth |
| Deploy API | Vercel (leitura) ou Railway/Fly (processos longos) | — |
| Observabilidade | Sentry (ja integrado) | — |

Nota: Streamlit (App/app.py) fica como painel LOCAL/dev, nao vai para lojas.

## 5. FASES
- **F0 (atual): Endurance 20.3 + gate economico (PF>1)** — sem robo validado,
  app nao tem valor. NAO antecipar.
- **F1 — API cloud minima**: adapter do api.py sem dependencias locais;
  ingestao POST /telemetry (EA empurra snapshot); DB externo; JWT.
- **F2 — MVP Flutter read-only**: login, dashboard (equity/DD/P-L),
  posicoes abertas, ultimos sinais, historico de trades.
- **F3 — Controles + Push**: toggle AutoTrade, ajuste de RiskPercent,
  FCM push (trade opened/closed, DD alert, circuit breaker).
- **F4 — Publicacao**: Play Store (conta dev US$25) + instalador Windows
  (MSIX/exe assinado).

## 6. TELAS (MVP)
1. Login/Biometria local
2. Dashboard: equity, saldo, DD diario vs limite, status SAFE/CircuitBreaker
3. Posicoes: simbolo, lado, volume, SL/TP, P/L flutuante
4. Sinais: ultimos DECISION APPROVED/BLOCKED + score IA
5. Historico: trades fechados + win rate
6. Config: toggles (AutoTrade, NewsFilter), thresholds de notificacao

## 7. SEGURANCA
- Nunca expor conta/MagicNumber sem JWT
- Controles de escrita exigem acao dupla no app + audit log server-side
- DSN/keys apenas em env vars (padrao .env ja adotado)
- Rate limit + HTTPS obrigatorio (Vercel/Railway provem)

## 8. DEPENDENCIAS DO ROADMAP ATUAL
- Conclusao endurance 20.3 (24h->30d)
- Gate economico: PF > 1 e drawdown aceitavel (CHECKLIST_GATE_2011.md)
- v1.2.2-opt aplicada apos 24h (f891f71 pronto)
