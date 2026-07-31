# Troubleshooting - Mudança de Corretora

**Problema:** EA não aparece no gráfico e não abre operações após mudar de corretora

---

## Diagnóstico Rápido

### 1. Verifique o nome do símbolo na nova corretora

**No MetaTrader 5:**
1. Abra o **Market Watch** (Ctrl+M)
2. Procure por XAUUSD ou GOLD
3. Clique com botão direito → **Specification**
4. Anote o **nome exato** do símbolo

**Nomes comuns:**
- `XAUUSD` (padrão)
- `XAUUSDc` (com sufixo 'c')
- `XAUUSD.pro`
- `XAUUSDm` (micro)
- `GOLD`
- `XAU/USD`

### 2. Atualize o Config.mqh

Edite: `MQL5/Experts/XAU_AI_PRO/Core/Config.mqh`

**Linha 110-119:** Altere a lista de símbolos para o nome correto da sua corretora:

```cpp
input string Symbols=
"XAUUSDc,"     // ← Altere aqui para o nome correto
"BTCUSDc,"     // ← Ou remova se não usar
"ETHUSDc,"     // ← Ou remova se não usar
"EURUSDc,"     // ← Ou remova se não usar
"GBPUSDc,"     // ← Ou remova se não usar
"USDJPYc,"     // ← Ou remova se não usar
"AUDUSDc,"     // ← Ou remova se não usar
"USDCADc,"     // ← Ou remova se não usar
"NZDUSDc";     // ← Ou remova se não usar
```

**Exemplo se sua corretora usar `XAUUSD`:**
```cpp
input string Symbols="XAUUSD";
```

### 3. Verifique o Magic Number

**Linha 8 do Config.mqh:**
```cpp
input long MagicNumber = 2026001;
```

- Se você já usou este Magic Number antes, mude para outro valor
- Verifique se não há outro robô rodando com o mesmo Magic

### 4. Verifique configurações de lote

**Linha 15 do Config.mqh:**
```cpp
input double LotSize = 0.01;
```

- Verifique o lote mínimo da sua corretora
- Algumas corretoras exigem 0.1 ou 1.0 como mínimo

### 5. Verifique permissões de automação

Algumas corretoras bloqueiam EAs. Verifique:
- ✅ AutoTrading está habilitado (botão no MT5)
- ✅ A corretora permite EAs
- ✅ Você tem permissão para operar o ativo

---

## Solução Avançada: Debug Logs

Vou adicionar logs detalhados para você ver exatamente o que está acontecendo.

### Passo 1: Habilite debug mode

No Config.mqh, linha 103:
```cpp
input bool DebugTradeDecision = true;  // ← Já está true
```

### Passo 2: Verifique o log

**Arquivo:** `XAU_AI_PRO.log` (na pasta do EA)

**Procure por:**
```
Broker Symbol: XAUUSDc -> [NOME_ENCONTRADO]
ATIVO REGISTRADO: [NOME_ENCONTRADO]
```

Se não aparecer nada, o símbolo não está sendo encontrado.

---

## Checklist de Verificação

- [ ] Símbolo correto identificado no Market Watch
- [ ] Config.mqh atualizado com o nome correto
- [ ] Magic Number único (não usado por outro robô)
- [ ] LoteSize >= mínimo da corretora
- [ ] AutoTrading habilitado no MT5
- [ ] Corretora permite EAs
- [ ] Conta demo ativa (testar primeiro!)
- [ ] Log do EA sem erros críticos

---

## Teste Rápido

1. **Compile o EA** (F7 no MetaEditor)
2. **Arraste para o gráfico** do símbolo correto
3. **Verifique a aba Experts** do MT5 (Ctrl+T)
4. **Procure por mensagens de erro** em vermelho

**Mensagens esperadas (sucesso):**
```
XAU_AI_PRO iniciado
ATIVO REGISTRADO: XAUUSD
Broker Symbol: XAUUSDc -> XAUUSD
```

**Mensagens de erro (problema):**
```
Símbolo não encontrado: XAUUSDc
ERRO INIT SYSTEM
```

---

## Ações Imediatas

1. **Me envie:**
   - Nome exato do símbolo no Market Watch
   - Screenshot do Market Watch
   - Primeiras 50 linhas do XAU_AI_PRO.log

2. **Eu vou:**
   - Ajustar o Config.mqh automaticamente
   - Adicionar logs de debug
   - Corrigir o SymbolManager se necessário

---

## Após Corrigir

Depois que o robô aparecer no gráfico:

1. Teste em **conta DEMO** por pelo menos 1 semana
2. Monitore o log diariamente
3. Verifique se as operações estão sendo abertas
4. Confira se o magic number está correto no histórico

**NÃO opere em conta real até validar em demo!**
