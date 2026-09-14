# Roadmap de produção XAU AI PRO

1. ✅ **CONCLUÍDO** — Governança GitHub, branches, CI e releases. (commit `62faaa1`)
2. ✅ **CONCLUÍDO** — Fundação Tauri sem dependências de desenvolvimento no usuário. (commit `d13c0b8`; MSI/NSIS gerados e validados E2E na máquina)
3. ✅ **CONCLUÍDO** — Login local, onboarding e configuração em `%APPDATA%\XAU_AI_PRO`. (commit `38f853f`; PIN com PBKDF2 via Web Crypto, wizard de 4 passos, LockScreen, config canônica em Roaming com `XAU_AI_PRO_CONFIG`, comandos Tauri de auth, CI verde)
4. ✅ **CONCLUÍDO** — Interface PC com abas, temas, gráficos, performance e acessibilidade. (commit `7267014`; 10 abas nativas, 4 temas, design system próprio, CI verde)
5. ⬜ **PRÓXIMO** — Protocolo versionado entre React, Rust Core e EA MT5.
6. ⬜ Conexão MT5 demo, handshake, heartbeat e reconciliação.
7. ⬜ Risk Engine: lote, spread, drawdown, perda diária e kill switch.
8. ⬜ IA assistiva: sinais auditáveis, backtest, walk-forward e paper trading.
9. ⬜ Conectores de corretoras com sandbox, rate limit e reconciliação.
10. ⬜ Atualizações stable/beta/canary/emergency com rollback.
11. ⬜ Instalador assinado, documentação PT-BR/EN, suporte e observabilidade.

## Definition of Done

Uma release só é pública após passar CI, instalar em máquina limpa, iniciar o Core, conectar ao MT5 demo, respeitar risco, sobreviver a desconexão, preservar dados em atualização e gerar logs auditáveis.
