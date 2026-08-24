# XAU_AI_PRO - Notas de Referência

**Última atualização:** 30/07/2026  
**Versão:** 1.10

---

## Problema Reportado em 30/07/2026

### ❌ Sintoma
- Mudou de corretora
- EA não abre operações
- EA não aparece no gráfico

### 🔍 Diagnóstico Provável
1. **Símbolo diferente** - Corretoras usam nomes variados:
   - XAUUSD
   - XAUUSDc (com sufixo)
   - XAUUSD.pro
   - XAU/USD
   
2. **Magic Number** - Pode estar em uso por outro robô

3. **Configurações de lote** - Mínimo diferente na nova corretora

4. **Permissões de automação** - Algumas corretoras bloqueiam EAs

5. **Timezone/Servidor** - Horário do servidor diferente

### ✅ Solução Imediata
Verificar arquivo `Config.mqh` e comparar com símbolo da corretora.

---

## Histórico do Projeto

### 23/07/2026 - Discussão de Roadmap
- Definiu roadmap V1.0 a V5.0
- Discutiu integrações: Data Analytics, Investment Banking, OpenAI, Vercel
- Decidiu usar VS Code Stable (não Insiders)
- Ferramentas essenciais: GitHub, Figma, CoinGecko, Binance, Vercel

### 23/07/2026 - Ferramentas de IA
- VS Code Stable recomendado como principal
- Stack: ChatGPT Plus, GitHub Copilot, Cline, Ollama
- Extensões: Python, Pylance, GitLens, Error Lens, Docker, Jupyter

### 23/07/2026 - Início V1.0
- Plano de auditoria completo
- Problemas identificados:
  - Drawdown muito alto
  - Python não trata múltiplos símbolos corretamente
  - IA não influencia entradas suficientemente

---

## Estrutura de Pastas (Downloads)

```
C:\Users\Micro\Downloads\XAU_AI_PRO\
├── MQL5/Files/Data/
│   ├── dataset.csv          # Dataset para treinamento
│   └── prediction.json      # Última predição da IA
├── Python/
│   ├── main.py              # CLI (train/predict)
│   ├── train.py             # Treina RandomForest
│   ├── predict.py           # Gera predições
│   ├── model.pkl            # Modelo treinado (193KB)
│   └── ai/
│       ├── predict_model.py # Carrega modelo
│       └── predict_engine.py# Constrói resultado
├── Models/                  # Modelos salvos
├── Dataset/                 # Datasets adicionais
├── Logs/                    # Logs Python
├── Backups/                 # Backups
└── Docs/                    # Documentação
```

---

## Arquivos Importantes

### MQL5 (Produção)
- **EA:** `C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\XAU_AI_PRO\XAU_AI_PRO.mq5`
- **Log:** `XAU_AI_PRO.log`
- **Prediction:** `prediction.json`

### Python (Downloads)
- **Main:** `C:\Users\Micro\Downloads\XAU_AI_PRO\Python\main.py`
- **Train:** `train.py`
- **Predict:** `predict.py`
- **Model:** `model.pkl`

---

## Última Predição (30/07/2026)

```json
{
    "symbol": "XAUUSDc",
    "signal": "SELL",
    "price": 4077.934,
    "buy": 17.0,
    "sell": 83.0,
    "score": 83.0
}
```

**Observação:** Símbolo é `XAUUSDc` (com sufixo 'c')

---

## Checklist V1.0

### Fase 1: Corretora
- [ ] Verificar nome do símbolo na corretora
- [ ] Verificar Magic Number
- [ ] Verificar configurações de lote
- [ ] Verificar permissões de automação
- [ ] Testar em conta demo primeiro

### Fase 2: Auditoria
- [ ] Revisar Config.mqh
- [ ] Revisar SignalCore.mqh
- [ ] Revisar DecisionEngine.mqh
- [ ] Revisar ValidationEngine.mqh
- [ ] Revisar ExecutionEngine.mqh
- [ ] Revisar RiskEngine.mqh
- [ ] Revisar PositionManager.mqh
- [ ] Revisar AIEngine.mqh
- [ ] Revisar AIConnector.mqh
- [ ] Revisar DataLogger.mqh

### Fase 3: Risk Management
- [ ] Implementar stop loss obrigatório
- [ ] Implementar take profit dinâmico
- [ ] Limitar perda diária
- [ ] Limitar drawdown
- [ ] Gestão de position sizing

### Fase 4: IA
- [ ] Melhorar features
- [ ] Testar diferentes algoritmos
- [ ] Aumentar influência da IA na decisão
- [ ] Validar modelo periodicamente

### Fase 5: Testes
- [ ] Backtest completo
- [ ] Forward test (demo)
- [ ] Análise de métricas
- [ ] Otimização de parâmetros

---

## Métricas Alvo (V1.0)

- **Win Rate:** > 50%
- **Profit Factor:** > 1.5
- **Drawdown Máximo:** < 15%
- **Expectancy:** Positiva
- **Sharpe Ratio:** > 1.0
- **SQN:** > 2.0

---

## Decisões Tomadas

1. **Metodologia:** Revisar em blocos, não arquivo por arquivo
2. **VS Code:** Usar Stable (não Insiders)
3. **Python:** 3.12.x com venv
4. **IA:** RandomForest baseline (melhorar depois)
5. **Estrutura:** Manter modular, não criar arquivo monolito

---

## Links Úteis

- Projeto: `C:\Users\Micro\Downloads\XAU_AI_PRO\`
- Produção: `C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\XAU_AI_PRO\`
- Docs: `C:\Users\Micro\Downloads\XAU_AI_PRO\Docs\`

---

## Contato e Suporte

- GitHub: (adicionar link)
- Documentação: `/Docs`
- Issues: Usar GitHub Issues
