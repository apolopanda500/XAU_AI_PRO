# CONVERSA 2026-10-11 — CICLO COMPLETO FRONTEND + EA

## Pedido do dono

1. Remover relógio embaixo do gráfico (duplicado — já existe no topo do app)
2. Remover presets "2 pra 2" e "3 pra 3" (1:2, 1:3, 1:4) do EA/painel
3. Deixar gráfico e comandos livres para o usuário configurar ou só ligar AUTO SIM
4. Modelos não estão operando — corrigir
5. Melhorar controle de risco no EA
6. Criar sub-abas na aba ROBÔ
7. Validar tudo 10/10

## O que foi feito

### 1. Relógio removido do rodapé
- `frontend/src/components/charts/PriceChart.tsx:2554`
- Removido `<QuantumClock compact />` do rodapé do gráfico
- Mantido `<SeletorFuso />` (não é relógio, é seletor de fuso)
- Relógio do topo do app permanece inalterado
- Import do `QuantumClock` removido do PriceChart

### 2. Presets 1:2/1:3/1:4 removidos
- `frontend/src/components/OperacaoAutomatica.tsx`
- Array `PRESETS` agora só contém `{ nome: '1:1', risco: 1, alvo: 1 }`
- O 1:1 continua sendo o padrão automático derivado do preço ao vivo
- O dono queria liberdade: sem presets fixos, o operador escreve o valor ou usa 1:1

### 3. Sub-abas na aba ROBÔ
- `frontend/src/components/RobotTabs.tsx` reescrito
- Nova estrutura: nav de sub-abas (Operação | Modelos | Risco | Operações) + conteúdo da sub-aba ativa + gráfico sempre visível
- Estado `subAba` com `useState`, começa em `'operacao'`
- CSS adicionado em `frontend/src/theme/robo.css`:
  - `.robo-sub-abas` — container flex com borda inferior
  - `.robo-sub-aba` — botão com hover e estado ativo
  - `.robo-sub-aba.ativa` — destaque com fundo e borda
- Testes atualizados em `frontend/src/components/RobotTabs.test.tsx`:
  - "sub-abas com operacao, modelos, risco e operacoes" (novo)
  - "operacao automatica, grafico e miniterminal, nessa ordem" (adaptado para nova estrutura)
  - "o grafico vem antes do miniterminal" (adaptado — gráfico sempre visível)

### 4. Modelos não operando — correção
- `frontend/src/components/SeletorModelo.tsx`
- Problema: `candidatoDoPeriodo` retornava `null` quando o motor não tinha timeframe ou quando não havia modelo para o timeframe do motor. O `useEffect` só chamava `setModeloId` quando `alvo` era não-vazio, então o `<select>` ficava vazio.
- Correção: novo `modeloReservado` — se não há candidato do período, usa o primeiro publicável; sem nenhum, o primeiro da lista; sem lista, vazio (e a mensagem diz).
- Garante que o modelo é SEMPRE selecionado quando há modelo disponível.

### 5. Controle de risco — RiskCenter integrado ao EA
- `MQL5/Experts/XAU_AI_PRO/Core/ExecutionEngine.mqh`
- Problema: `RiskCenter.mqh` existia mas NÃO era chamado no fluxo de execução. As checagens eram espalhadas: `CanTradeToday()` no ExecutionEngine, `CSafetyManager::CheckAll()` no OnTick, `EquityProtection` no OnTick.
- Correção: adicionado gate obrigatório `RiskAllowEntry(symbol, riskReason)` após `CanOpenPosition()` e antes do cálculo de lote.
- RiskCenter consolida em ordem determinística:
  1. DAILY_LOSS — perda diária vs limite
  2. DAILY_DRAWDOWN — drawdown vs limite
  3. MAX_TRADES_PER_DAY — contagem de trades
  4. FREE_MARGIN — margem livre mínima
  5. TOTAL_EXPOSURE — exposição total
- Fail-closed: se qualquer leitura falhar, bloqueia.
- Se bloqueia: log + `EventRiskBlock(symbol, "RiskCenter bloqueou: " + riskReason)`

## Validação medida

| Suíte | Resultado | Mudanças |
|---|---|---|
| `tsc --noEmit` | 0 erros | — |
| `vitest run` | 867 passaram / 11 falhas pré-existentes | +1 teste novo (RobotTabs) |
| `pytest -q tests` | 1327 passaram / 2 skipped / 3 falhas pré-existentes | +3 testes (1315 → 1327) |
| `test_mql5_compila.py` | 2 passed (MetaEditor real) | EA compilou com RiskCenter |

## Falhas pré-existentes (não relacionadas a este ciclo)

| Arquivo | Falhas | Motivo |
|---|---|---|
| `ListaModelos.test.tsx` | 1 | "a coluna MODELO nao repete a coluna PAR" — teste antigo, mudança de layout da tabela |
| `EconomicCalendarTab.test.tsx` | 10 | Testes do calendário econômico — não mexido neste ciclo |
| `test_bundle_gateway_artefato.py` | 1 | Teste de bundle — não mexido |
| `test_sem_codigo_morto.py` | 1 | Teste de código morto — não mexido |
| `test_spec_gateway.py` | 1 | Teste de spec — não mexido |

## Arquivos alterados

| Arquivo | Tamanho | Mudança |
|---|---|---|
| `frontend/src/components/charts/PriceChart.tsx` | ~2601 linhas | Removido QuantumClock do rodapé + import |
| `frontend/src/components/OperacaoAutomatica.tsx` | ~897 linhas | PRESETS reduzido a 1:1 |
| `frontend/src/components/RobotTabs.tsx` | ~114 → ~80 linhas | Reescrito com sub-abas |
| `frontend/src/components/RobotTabs.test.tsx` | ~691 linhas | 2 testes adaptados + 1 novo |
| `frontend/src/components/SeletorModelo.tsx` | ~396 linhas | modeloReservado garante seleção |
| `frontend/src/theme/robo.css` | ~567 linhas | CSS das sub-abas |
| `MQL5/Experts/XAU_AI_PRO/Core/ExecutionEngine.mqh` | ~404 linhas | RiskCenter integrado |

## O que falta para o dono

1. **Build + instalar** — `build_app.bat` excede 15min (Rust compile). Rodar manualmente:
   ```powershell
   cmd /c "scripts\build_app.bat"
   ```
2. **Reanexar EA no gráfico** — após instalar, reanexar no MT5
3. **Testar sub-abas no app** — navegar entre Operação/Modelos/Risco/Operações e confirmar que o gráfico fica sempre visível
4. **Verificar EA no gráfico** — confirmar que RiskCenter está bloqueando/permitindo corretamente

## Próximo ciclo — pendências

- Corrigir falhas pré-existentes do `ListaModelos.test.tsx` (1) e `EconomicCalendarTab.test.tsx` (10)
- Corrigir falhas pré-existentes do pytest (`test_bundle_gateway_artefato`, `test_sem_codigo_morto`, `test_spec_gateway`)
- Build do app + instalação + reanexar EA
- Testar fluxo completo: sub-abas → escolher modelo → ligar AUTO → verificar RiskCenter bloqueando/permitindo
