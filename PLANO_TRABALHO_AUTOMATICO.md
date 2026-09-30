# XAU AI PRO — Plano de Trabalho Automatico

**Data:** 2026-09-29 13:50 BRT · **Versao:** 1.2.4 · **Branch:** `develop`
**Status:** auditoria concluida; correcoes aplicadas; build pendente

> Este plano substitui o de 2026-09-29 00:00. O ciclo anterior focava em
> correcoes de tela. A auditoria de 2026-09-29 encontrou defeitos de maior
> gravidade no catalogo de IA e no backtester, e eles foram corrigidos primeiro.

---

## Estado das fases

| Fase | Escopo | Estado |
|---|---|---|
| 1 | Catalogo de modelos: governanca restaurada | **concluida** |
| 2 | Backtester fiel ao modelo publicado | **concluida** |
| 3 | Teste que exige trade_count real | **concluida** |
| 4 | Limpeza da raiz | **concluida** |
| 5 | Infra de mercado real (switch OFF) | **em andamento** |
| 6 | Ciclo de build completo | **pendente** |
| 7 | Instalacao e teste como usuario normal | **pendente** |
| 8 | Documentacao e handoff | **em andamento** |

Detalhe tecnico em `Docs/AUDITORIA_20260929.md`.

---

## Fase 1 — Catalogo de modelos (CONCLUIDA)

- [x] Causa raiz identificada: dois escritores disputam `*.meta.json`
- [x] `pipeline.py` protegido com `preservar_governanca()`
- [x] 6 metadados regenerados com `scripts/treinar_ia.py`
- [x] Backup em `Python/models/_backup_legado_20260929/`
- [x] `tests/test_governanca_modelos.py` (8 testes)
- [x] `scripts/auditar_governanca_modelos.py`

**Prova:** `36/36` metadados integros, `25` publicaveis, `11` reprovados.

---

## Fase 2 — Backtester fiel ao modelo (CONCLUIDA)

- [x] `_decisao_do_modelo()` carrega o `.pkl` publicado
- [x] `decision_source` / `measured` / `reason` no resultado
- [x] Warm-up offset publicado (`warmup_offset`)
- [x] Endpoint passa `symbol` e `timeframe`
- [x] Sem modelo, zero trades com motivo — nunca inventa sinal

---

## Fase 3 — Teste do backtest (CONCLUIDA)

- [x] `tests/test_backtest.py` de 4 para 11 testes
- [x] `trade_count` e `win_rate_pct` verificados
- [x] "Modelo medido e nao operou" != "nao ha modelo"

---

## Fase 4 — Limpeza (CONCLUIDA)

- [x] `frontend/dist` removido (artefato de build)
- [x] Logs de trabalho em `Temp/` removidos
- [x] `MQL5/`, `Models/`, `Data/`, `Logs/` preservados

**Fora do alcance do script:** `.pytest_cache/` tem ACL corrompida e causa
`warning: could not open directory` no `git status`. A remocao exige PowerShell
como administrador:

```powershell
Remove-Item -Recurse -Force .\.pytest_cache
```

---

## Fase 5 — Infra de mercado real (EM ANDAMENTO)

Regra: o interruptor fica **desligado**. O codigo e a ferramenta ficam prontos;
quem liga e o proprietario, depois que os testes passarem sozinhos.

- [x] Decisao do proprietario registrada: preparar, nao ativar
- [ ] `XAU_ENABLE_REAL_ORDERS` movido do `main.rs` para o ambiente, padrao `0`
- [ ] Script de validacao de prontidao para mercado real
- [ ] Endurance automatizado (24h / 72h / 7d) com relatorio
- [ ] Registro de forward test em DEMO

**Pre-requisitos que hoje nao existem:** forward test aprovado, endurance test,
e credencial real (a conta atual e `MetaQuotes-DEMO`).

---

## Fase 6 — Ciclo de build (PENDENTE)

```powershell
cd core
cargo test --locked
cargo build --release --locked
Copy-Item "target\release\xau-ai-pro-core.exe" "..\frontend\src-tauri\core\" -Force
cd ..

.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean mt5-gateway.spec
Remove-Item -Recurse -Force "frontend\src-tauri\bridge"
Copy-Item -Recurse "dist\mt5-gateway" "frontend\src-tauri\bridge" -Force

cd frontend
npm run build
npm run tauri build
cd ..

.\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean launcher.spec
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "installer\installer.iss"
```

**Regra que ja custou tempo:** mudou Python, tem que recompilar o
`mt5-gateway.exe`. Rodar so `tauri build` deixa o app instalado no codigo velho.

---

## Fase 7 — Teste como usuario normal (PENDENTE)

- [ ] Instalar pelo **MSI** (o NSIS sai com 0 e nao substitui o exe)
- [ ] Abrir pelo atalho, nao pelo script
- [ ] Conferir as 6 abas renderizando
- [ ] Conferir dados em tempo real
- [ ] Botoes de ordem, sem auto-click
- [ ] Configuracao de corretoras (MT5, Binance, MEXC, Bybit, OKX)

---

## Verificacao rapida

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests -p no:cacheprovider
.\.venv\Scripts\python.exe scripts\auditar_governanca_modelos.py
Set-Location frontend; npx tsc --noEmit; npm test; Set-Location ..
Set-Location core; cargo test --locked; Set-Location ..
```

---

## Regras que continuam valendo

1. `MQL5/Experts` intocado — `scripts/agentes.ps1` barra o commit.
2. `withdrawals_enabled = False` e `transfers = False` em todo o codigo.
3. Nunca commitar `.env`, token ou senha.
4. Nao usar `Python/auto_retrain.py` para publicar modelo: use
   `scripts/treinar_ia.py`.
5. Saque e transferencia continuam bloqueados. Ponto.


---

## Fase 1: Correções da Aba Robô (Prioridade 1)

### 1.1 Reorganizar sub-abas
- [ ] Sub-aba "Sinal" → Modelo e previsão (RobotModelPanel)
- [ ] Sub-aba "Automação" → Operação automática (AutoEnginePanel) + Risco (RiskTab) + Guardian (GuardianManager)
- [ ] Sub-aba "Mesa" → Comandos manuais (OrderPanel)
- [ ] Sub-aba "EA" → Expert Advisors (EAPanel)
- [ ] Sub-aba "Copiloto" → IA com robô (CopilotPanel)

### 1.2 Adicionar comandos manuais na sub-aba "Mesa"
- [ ] Botões de compra/venda manuais
- [ ] Seleção de ativo
- [ ] Volume, SL, TP
- [ ] Fechar posição
- [ ] Break-even, Trailing, Proteção

### 1.3 Adicionar automação na sub-aba "Automação"
- [ ] Botão Ligar/Desligar motor
- [ ] Seleção de ativo (não só XAUUSD)
- [ ] Seleção de timeframe
- [ ] Seleção de modelo treinado
- [ ] Limites de risco
- [ ] Status do motor

### 1.4 Adicionar IA com robô na sub-aba "Copiloto"
- [ ] Conversa com IA
- [ ] Análise de código do EA
- [ ] Sugestões de melhoria

---

## Fase 2: Correções da Aba Calendários (Prioridade 2)

### 2.1 Separar dias
- [ ] Agrupar eventos por dia
- [ ] Mostrar data por extenso
- [ ] Badge "Hoje", "Amanhã", "Ontem"

### 2.2 Nível de notícias econômicas
- [ ] Separar por impacto (Alto, Médio, Baixo)
- [ ] Cores diferentes para cada nível
- [ ] Filtro por impacto

### 2.3 Tabelas melhores
- [ ] Alinhar colunas
- [ ] Melhor espaçamento
- [ ] Resumo por dia

---

## Fase 3: Correções da Aba Configuração (Prioridade 3)

### 3.1 Adicionar outras corretoras
- [ ] Lista de corretoras disponíveis (MT5, Binance, MEXC, Bybit, OKX)
- [ ] Formulário para adicionar credenciais
- [ ] Salvar configurações
- [ ] Testar conexão

---

## Fase 4: Correções da Operação Automática (Prioridade 4)

### 4.1 Adicionar botões
- [ ] Ligar motor
- [ ] Desligar motor
- [ ] Aplicar configuração
- [ ] Rodar ciclo manual

### 4.2 Adicionar opções de ativos
- [ ] Lista de ativos com modelo treinado
- [ ] Seleção de timeframe
- [ ] Mostrar apenas ativos com modelo

---

## Fase 5: Build e Testes (Prioridade 5)

### 5.1 Build completo
- [ ] Core Rust
- [ ] Gateway Python
- [ ] Frontend
- [ ] Tauri
- [ ] Launcher
- [ ] Instaladores

### 5.2 Testes
- [ ] Testes Python
- [ ] Testes frontend
- [ ] Testes Rust
- [ ] Testar app

### 5.3 Commit e push
- [ ] Commit das alterações
- [ ] Push para GitHub e GitLab

---

## Fase 6: Documentação (Prioridade 6)

### 6.1 Atualizar handoff
- [ ] Data e hora
- [ ] Estado atual
- [ ] Pendências
- [ ] Próximos passos

---

## Status da Execução

| Fase | Status | Início | Fim |
|---|---|---|---|
| Fase 1 | Em execução | 2026-09-29 00:00 | - |
| Fase 2 | Pendente | - | - |
| Fase 3 | Pendente | - | - |
| Fase 4 | Pendente | - | - |
| Fase 5 | Pendente | - | - |
| Fase 6 | Pendente | - | - |

---

## Notas

- O PC vai ficar ligado e trabalhando automaticamente
- Cada fase será concluída antes de iniciar a próxima
- O progresso será registrado neste arquivo
- Ao final, o app estará 100% corrigido e pronto para uso
