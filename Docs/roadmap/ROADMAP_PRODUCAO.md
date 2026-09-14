# Roadmap de produção XAU AI PRO

1. ✅ **CONCLUÍDO** — Governança GitHub, branches, CI e releases. (commit `62faaa1`)
2. ✅ **CONCLUÍDO** — Fundação Tauri sem dependências de desenvolvimento no usuário. (commit `d13c0b8`; MSI/NSIS gerados e validados E2E na máquina)
3. ✅ **CONCLUÍDO** — Login local, onboarding e configuração em `%APPDATA%\XAU_AI_PRO`. (commit `38f853f`; PIN com PBKDF2 via Web Crypto, wizard de 4 passos, LockScreen, config canônica em Roaming com `XAU_AI_PRO_CONFIG`, comandos Tauri de auth, CI verde)
4. ✅ **CONCLUÍDO** — Interface PC com abas, temas, gráficos, performance e acessibilidade. (commit `7267014`; 10 abas nativas, 4 temas, design system próprio, CI verde)
5. ✅ **CONCLUÍDO** — Protocolo versionado entre React, Rust Core e EA MT5. (commits `50e721e` + `e3a2770`; handshake Hello, heartbeat, erros tipados, request_id, contrato TS + include MQL5, CI verde)
6. ✅ **CONCLUÍDO** — Conexão MT5 demo, handshake, heartbeat e reconciliação. (commit `7c5160d`; módulo `mt5session` con estado online/stale, HTTP del EA `eahttp`, enrutamiento de órdenes WS al EA en línea, CoreBridge.mqh con hello+heartbeat)
7. ✅ **CONCLUÍDO** — Risk Engine: lote, spread, drawdown, perda diária e kill switch. (módulo `risk` com `RiskEngine` integrado ao roteamento WS de PlaceOrder, endpoints `/api/risk/kill` e `/api/risk/status` no HTTP do EA, contadores diários com roll à meia-noite, 5 testes unitários; CI verde)
8. ⬜ **PRÓXIMO** — IA assistiva: sinais auditáveis, backtest, walk-forward e paper trading.
9. ⬜ Conectores de corretoras com sandbox, rate limit e reconciliação.
10. ⬜ Atualizações stable/beta/canary/emergency com rollback.
11. ⬜ Instalador assinado, documentação PT-BR/EN, suporte e observabilidade.

## Definition of Done

Uma release só é pública após passar CI, instalar em máquina limpa, iniciar o Core, conectar ao MT5 demo, respeitar risco, sobreviver a desconexão, preservar dados em atualização e gerar logs auditáveis.
