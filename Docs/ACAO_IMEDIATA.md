# AÇÃO IMEDIATA - Corretora Nova

**Status:** 🔴 Aguardando sua ação  
**Prioridade:** 🔥 CRÍTICA  
**Tempo estimado:** 5 minutos

---

## O QUE EU FIZ ✅

1. ✅ Adicionei logs de debug no código
2. ✅ Criei guia de troubleshooting completo
3. ✅ Documentei todo o projeto
4. ✅ Adicionei campo `EnableVerboseDebug` no Config
5. ✅ Adicionei logs detalhados no SymbolManager
6. ✅ Adicionei logs de inicialização no EA principal

---

## O QUE VOCÊ PRECISA FAZER AGORA 🔧

### PASSO 1: Identificar o símbolo correto (1 minuto)

1. Abra o **MetaTrader 5**
2. Pressione **Ctrl+M** (abre Market Watch)
3. Procure por **XAUUSD** ou **GOLD**
4. Clique com botão direito → **Specification**
5. Anote o **nome exato** do símbolo

**Exemplos de nomes possíveis:**
- `XAUUSD`
- `XAUUSDc`
- `XAUUSD.pro`
- `XAUUSDm`
- `GOLD`
- `XAU/USD`

---

### PASSO 2: Atualizar Config.mqh (2 minutos)

1. No MetaTrader, pressione **F4** (abre MetaEditor)
2. Navegue até: `MQL5/Experts/XAU_AI_PRO/Core/Config.mqh`
3. Vá para **linha 110-119**
4. Altere o primeiro símbolo para o nome correto da sua corretora

**EXEMPLO - Se sua corretora usar `XAUUSD`:**
```cpp
input string Symbols=
"XAUUSD,"  // ← Alterado de XAUUSDc para XAUUSD
"XAUUSDc,"
"BTCUSDc,"
"ETHUSDc,"
"EURUSDc,"
"GBPUSDc,"
"USDJPYc,"
"AUDUSDc,"
"USDCADc,"
"NZDUSDc";
```

**EXEMPLO - Se usar apenas XAUUSD:**
```cpp
input string Symbols="XAUUSD";
```

---

### PASSO 3: Compilar (30 segundos)

1. No MetaEditor, pressione **F7** (Compile)
2. Verifique se aparece: **"0 errors, 0 warnings"**
3. Se houver erros, me envie a mensagem

---

### PASSO 4: Testar no gráfico (1 minuto)

1. Volte para o MT5
2. Abra o gráfico do **símbolo correto** (ex: XAUUSD)
3. Arraste o **XAU_AI_PRO** do Navigator para o gráfico
4. Pressione **Ctrl+T** (abre aba Experts)
5. **LEIA AS MENSAGENS** na aba Experts

---

### PASSO 5: Me enviar o log (2 minutos)

**Me envie:**
1. ✅ Nome exato do símbolo (do Market Watch)
2. ✅ Screenshot da aba Experts (Ctrl+T) com as mensagens
3. ✅ Primeiras 30 linhas do arquivo `XAU_AI_PRO.log`
   - Local: `C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\XAU_AI_PRO\XAU_AI_PRO.log`

---

## O QUE PROCURAR NOS LOGS 🔍

### ✅ SUCESSO (bom):
```
========================================
  XAU_AI_PRO v1.10 - DEBUG MODE
========================================
Symbolo atual: XAUUSD
Conta: 123456789
Corretora: SUA_CORRETORA
Servidor: SEU_SERVIDOR
Saldo: 10000.00
========================================

=== INICIALIZANDO SYMBOL MANAGER ===
Simbolos configurados: 1
=== SYMBOL MANAGER INICIALIZADO ===
Total de ativos: 1
  Ativo [0]: XAUUSD
XAU_AI_PRO iniciado
```

### ❌ ERRO (me envie):
```
ERRO: Simbolo nao encontrado: XAUUSDc
ERRO INIT SYSTEM
Símbolo não encontrado: XAUUSDc
```

---

## CHECKLIST RÁPIDO ✓

- [ ] Identifiquei o nome correto do símbolo
- [ ] Atualizei o Config.mqh
- [ ] Compilei sem erros (F7)
- [ ] Arrastei EA para o gráfico correto
- [ ] Verifiquei a aba Experts (Ctrl+T)
- [ ] Li as mensagens de log
- [ ] Vou enviar os logs para você

---

## PRÓXIMOS PASSOS DEPOIS DE CORRIGIR 🚀

Depois que o robô aparecer no gráfico:

1. **Teste em DEMO por 1 semana**
2. **Monitore o log diariamente**
3. **Verifique se opera** (não precisa ter lucro ainda)
4. **Depois começamos a V1.0** (auditoria e melhorias)

---

## PRECISA DE AJUDA?

Me envie:
- Nome do símbolo
- Screenshot do Market Watch
- Screenshot da aba Experts
- Log do EA

**EU VOU CORRIGIR AUTOMATICAMENTE!** ⚡

---

**Tempo total:** 5 minutos  
**Dificuldade:** Fácil  
**Resultado:** Robô funcionando na nova corretora

**BOA SORTE!** 🎯
