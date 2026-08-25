# ============================================================
# XAU_AI_PRO v1.2.0 — ETAPA 20.5 — ROTEIRO DE REANEXACAO
# (Forward Demo)
# Data: 2026-08-25
# ============================================================

## POR QUE REANEXAR?
O .ex5 foi recompilado em 25/08 14:25 (reversao do SignalCore).
O EA anexado nos 6 graficos ainda roda a versao ANTIGA em memoria.
Reanexar forca o carregamento do novo .ex5 (hash 9303e383...).

## PASSO A PASSO (por grafico)

### 1. Remover o EA antigo
- Em cada grafico (XAUUSD, EURUSD, USDBRL, AUDUSD, NZDUSD, USDCHF):
  - Clique direito no grafico > "Expert Advisors" > "Remover"
  - (ou arraste o EA para fora do grafico)

### 2. Reanexar o EA novo
- Navegador > Experts > XAU_AI_PRO > XAU_AI_PRO.ex5
- Arraste para o grafico OU duplo clique > OK

### 3. Conferir os inputs (importante - NAO alterar risco/estrategia)
- Confirmar que ficaram IGUAIS aos anteriores:
  - MagicNumber = 2026001
  - FastEMA = 50, SlowEMA = 200, RSIPeriod = 14
  - RSIPullbackBuy = 45.0, RSIPullbackSell = 55.0
  - StopLossPoints = 300, TakeProfitPoints = 600
  - AutoTrade = (qualquer valor - nao bloqueia desde v1.2.1)
  - EnableNewsFilter = 0, EnableAIFilter = 0, UseRiskManagement = 0
    (config atual de validacao; NAO mudar agora)

### 4. Verificar o botao ALGORITMOS
- Barra de ferramentas > botao "Algoritmos" deve estar VERDE
- (ja confirmado: experts_trade_allowed = true)

### 5. Confirmar que o novo .ex5 carregou
- Aba "Experts" do Terminal (Journal):
  - Deve aparecer o log de OnInit do EA novo
  - NAO deve aparecer "Falha ao copiar RSI"
  - Deve aparecer [PIPELINE] e sinais quando houver condicao

## CHECKLIST DE VALIDACAO (apos reanexar)
[ ] 6 graficos com XAU_AI_PRO novo
[ ] Sem "Falha ao copiar RSI" no log
[ ] [PIPELINE] INICIO/PROCESSANDO aparecendo
[ ] Botao Algoritmos verde
[ ] Nenhuma posicao aberta sem intencao (demo)
[ ] ForwardHeartbeat (se EnableForwardLog=1) ativo

## CRITERIO DE PARADA
Se aparecer QUALQUER um destes, pare e reporte:
- "SIGNAL ERROR: Falha ao copiar RSI" (regressao)
- "ALGO TRADING OFF" (botao desligado)
- Erros de OnInit/OnDeinit
- Handles invalidos repetidos

## NOTA
Depois da reanexacao, avisar o assistente para iniciar o
monitoramento do forward (heartbeat, eventos, reconciliacao).