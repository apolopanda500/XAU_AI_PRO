# XAU_AI_PRO — Roadmap

## Visão Geral

O XAU_AI_PRO é um sistema de trading automatizado para MetaTrader 5 que combina análise técnica tradicional (EMA, RSI, ADX, ATR, padrões de candle) com previsões de IA geradas por um pipeline Python RandomForest. O roadmap é dividido em versões temáticas, cada uma focando em uma dimensão de maturidade do sistema.

---

## V1.0 — Estabilidade e Lucratividade ✅ (CONCLUÍDA)

**Status:** Commit `0ef122e8` — *V1.0: Multi-símbolo, IA efetiva, gestão de risco, dataset melhorado*

### Problemas Resolvidos

| # | Problema | Solução |
|---|---|---|
| 1 | Filtro hardcoded de XAUUSD no Python | Removido — suporta todos os símbolos |
| 2 | IA não influenciava decisões | Aumentado de 30% → 50% do score; AI Veto; GetCombinedSignal |
| 3 | Vazamento de memória | Handle release garantido em todos os caminos |
| 4 | Gestão de risco insuficiente | EquityProtection, BreakEven ATR, Trailing robusto, daily loss limit |
| 5 | Multi-símbolo no MQL5 | Todos indicadores/filtros aceitam símbolo |

### Métricas Alvo (V1.0)

- [x] Win Rate > 50%
- [x] Profit Factor > 1.5
- [x] Drawdown < 15%
- [x] Commit V1.0 realizado e pushado para GitHub
- [x] Branch `develop` criada

### ETAPAS V1.0

- [x] **ETAPA 1** — Auditoria completa dos módulos Core, AI, Filters, Indicators, Management
- [x] **ETAPA 2** — Multi-símbolo + IA + Dataset (Python + MQL5)
- [x] **ETAPA 3** — Gestão de risco (BreakEven ATR, EquityProtection, PositionManager, RiskEngine)
- [x] **ETAPA 4** — IA efetiva (AI Veto, GetCombinedSignal, GetAILotMultiplier, LogAIFeedback)
- [x] **ETAPA 5** — Registro no GitHub (push, branch develop, docs, issue V1.1)

---

## V1.1 — Performance e Proteção de Capital

**Status:** Planejamento (issue aberta no GitHub)

### Objetivo

Otimizar a performance do pipeline de machine learning e fortalecer os mecanismos de proteção de capital.

### Tarefas

- [ ] Otimização da engenharia de features no Python (vetorização, cache)
- [ ] Fine-tuning do RandomForest (grid search / Bayesian optimization)
- [ ] Proteção de capital baseada em volatilidade (position sizing dinâmico)
- [ ] Monitoramento de drawdown em tempo real com alertas
- [ ] Estratégia de saída antecipada (take-profit dinâmico baseado em IA)

---

## V2.0 — Data Analytics

- Análise completa de trades (per-trade, per-symbol, per-strategy)
- Métricas avançadas: Sharpe, SQN, Expectancy, Calmar
- Detecção automática de estratégias ruins
- Dashboards analíticos interativos
- Stack: pandas, NumPy, DuckDB/PostgreSQL, Plotly

---

## V3.0 — XAU AI Studio

- Aplicativo Windows desktop (PySide6)
- Interface unificada para configuração, treinamento e monitoramento
- Backtests avançados com múltiplas estratégias
- Monitoramento em tempo real do EA no MT5

---

## V4.0 — Portal Web

- Dashboard web hospedado (Vercel)
- API pública RESTful
- Painel do usuário com histórico de trades
- Documentação online interativa

---

## V5.0 — Ecossistema Completo

- Agentes de IA especializados (entry, exit, risk, news)
- Automação avançada de pipeline MLOps
- Suporte a múltiplos usuários e contas
- Serviços em nuvem (Azure Container Apps)

---

## Stack Tecnológico

### Essencial (V1.0)

| Ferramenta | Versão | Uso |
|---|---|---|
| VS Code Stable | — | IDE principal |
| GitHub Copilot | — | Autocompletar |
| Cline | — | Edição e refatoração |
| Git | — | Controle de versão |
| Python | 3.12+ | Pipeline de ML |
| MetaTrader 5 | — | Execução de trades |
| scikit-learn | — | Modelo RandomForest |
| pandas / NumPy | — | Processamento de dados |

### Futuro (V2.0+)

| Ferramenta | Uso |
|---|---|
| FastAPI | API REST |
| PostgreSQL / DuckDB | Armazenamento analítico |
| Plotly / Dash | Visualização |
| PySide6 | Interface desktop |
| Vercel | Hospedagem web |

---

## Ferramentas Recomendadas para Desenvolvimento

- **VS Code Stable** — IDE principal (⭐⭐⭐⭐⭐)
- **ChatGPT Plus** — Arquiteto principal (⭐⭐⭐⭐⭐)
- **GitHub Copilot** — Autocompletar (⭐⭐⭐⭐⭐)
- **Cline** — Edição e refatoração (⭐⭐⭐⭐⭐)
- **Ollama** — Modelos locais (⭐⭐⭐⭐☆)

### Extensões VS Code

- Python
- Pylance
- GitHub Copilot
- Cline
- GitLens
- Error Lens
- Docker
- Jupyter
