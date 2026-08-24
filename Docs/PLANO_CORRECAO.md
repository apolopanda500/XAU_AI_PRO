# PLANO DE CORREÇÃO - V1.0

**Data:** 30/07/2026  
**Objetivo:** Corrigir problemas críticos que impedem lucratividade  
**Status:** 🔴 Em andamento

---

## 🎯 ESTRATÉGIA

Vou corrigir os módulos em ordem de criticidade:

1. **ExecutionEngine** - Adicionar SL/TP (SEM proteção = SEM lucro)
2. **DecisionEngine** - Score dinâmico (IA precisa influenciar)
3. **AIEngine** - Carregar prediction.json (IA real)
4. **RiskEngine** - Considerar drawdown (gestão de risco)
5. **SignalCore** - Fix memory leak (estabilidade)

Depois:
6. PositionManager - Reduzir trailing stop
7. Config - Ajustar parâmetros
8. BreakEven - Reduzir trigger

---

## 📋 ORDEM DE CORREÇÃO

### PASSO 1: ExecutionEngine (CRÍTICO)
**Arquivo:** Core/ExecutionEngine.mqh  
**Mudança:** Adicionar SL/TP na abertura de ordens  
**Risco:** Baixo (mudança direta)  
**Impacto:** ALTO - Proteção de capital

### PASSO 2: DecisionEngine (CRÍTICO)
**Arquivo:** Core/DecisionEngine.mqh  
**Mudança:** Score dinâmico baseado em indicadores  
**Risco:** Médio (mudança de lógica)  
**Impacto:** ALTO - Qualidade das decisões

### PASSO 3: AIEngine (CRÍTICO)
**Arquivo:** AI/AIEngine.mqh  
**Mudança:** Carregar prediction.json do Python  
**Risco:** Médio (nova dependência)  
**Impacto:** ALTO - IA passa a funcionar

### PASSO 4: RiskEngine (CRÍTICO)
**Arquivo:** Core/RiskEngine.mqh  
**Mudança:** Considerar drawdown no cálculo de lote  
**Risco:** Baixo (ajuste de cálculo)  
**Impacto:** ALTO - Reduz perdas em sequência

### PASSO 5: SignalCore (CRÍTICO)
**Arquivo:** Core/SignalCore.mqh  
**Mudança:** Liberar handles corretamente  
**Risco:** Baixo (fix de bug)  
**Impacto:** MÉDIO - Estabilidade

### PASSO 6: PositionManager (GRAVE)
**Arquivo:** Core/PositionManager.mqh  
**Mudança:** Reduzir trailing stop de 2.0 para 1.2  
**Risco:** Baixo (ajuste de parâmetro)  
**Impacto:** ALTO - Protege lucros

### PASSO 7: Config (GRAVE)
**Arquivo:** Core/Config.mqh  
**Mudança:** Ajustar BreakEvenTrigger, PartialTrigger  
**Risco:** Baixo (ajuste de parâmetros)  
**Impacto:** MÉDIO - Melhora gestão

---

## ⚠️ RISCOS E CONTINGÊNCIAS

### Risco 1: SL/TP muito apertados
**Mitigação:** Testar em DEMO primeiro, ajustar gradualmente

### Risco 2: Score dinâmico muito restritivo
**Mitigação:** Ajustar pesos, monitorar win rate

### Risco 3: prediction.json não encontrado
**Mitigação:** Fallback para score hardcoded

### Risco 4: Drawdown muito agressivo
**Mitigação:** Ajustar percentuais gradualmente

---

## 📊 CRITÉRIOS DE SUCESSO

### Após Correções:
- [ ] EA compila sem erros
- [ ] SL/TP são aplicados corretamente
- [ ] Score varia entre 0-100 baseado em dados reais
- [ ] prediction.json é carregado quando disponível
- [ ] Lote diminui em drawdown > 5%
- [ ] Handles são liberados corretamente
- [ ] Trailing stop funciona com ATR 1.2
- [ ] BreakEven ativa em 80 pontos

### Teste em DEMO (1 semana):
- [ ] Win Rate > 45%
- [ ] Drawdown < 20%
- [ ] Profit Factor > 1.2
- [ ] IA influencia pelo menos 30% das decisões

---

## 🚀 COMEÇANDO CORREÇÕES

**Agora vou aplicar as correções uma por uma.**

Cada correção será:
1. Aplicada no código MQL5
2. Testada (compilação)
3. Documentada

**Aguarde...**

---

**Status:** 🔴 Correções em andamento  
**Próximo:** ExecutionEngine - Adicionar SL/TP
