# 🎯 Bem-vindo ao XAU_AI_PRO

**Sistema de Trading Quantitativo com IA para XAU/USD (Gold)**

---

## 📋 O que é o XAU_AI_PRO?

O **XAU_AI_PRO** é um robô de trading automatizado para MetaTrader 5 que utiliza:

- **Inteligência Artificial** (Machine Learning) para prever movimentos de preço
- **Análise Técnica** (ATR, ADX, RSI, EMA)
- **Gestão de Risco** avançada (stop loss, take profit, break even)
- **Filtros Inteligentes** (spread, sessão, tendência, volatilidade)

**Objetivo:** Operar XAU/USD (Gold) de forma automatizada e lucrativa.

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────┐
│          META TRADER 5 (MT5)            │
│  ┌───────────────────────────────────┐  │
│  │   XAU_AI_PRO EA (MQL5)           │  │
│  │   - Indicadores Técnicos          │  │
│  │   - Filtros de Mercado            │  │
│  │   - Gestão de Risco               │  │
│  │   - Execução de Ordens            │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
           ↓ dataset.csv ↑ prediction.json
┌─────────────────────────────────────────┐
│       PYTHON AI BACKEND                 │
│  ┌───────────────────────────────────┐  │
│  │   - Carrega dados históricos      │  │
│  │   - Treina modelo ML              │  │
│  │   - Gera predições                │  │
│  │   - Salva prediction.json         │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

---

## 📁 Estrutura do Projeto

```
C:\Users\Micro\Downloads\XAU_AI_PRO\
├── MQL5/Files/Data/          # Dataset e predictions
├── Python/                   # Backend IA
├── Models/                   # Modelos treinados
├── Dataset/                  # Datasets
├── Logs/                     # Logs Python
├── Backups/                  # Backups
├── Reports/                  # Relatórios
└── Docs/                     # 📚 DOCUMENTAÇÃO
    ├── ACAO_IMEDIATA.md      # ⭐ LEIA ESTE PRIMEIRO!
    ├── ROADMAP_V1.0.md
    ├── REFERENCE_NOTES.md
    ├── TROUBLESHOOTING_NEW_BROKER.md
    └── STATUS_ATUAL.md
```

---

## 🚀 Começando Rápido

### Problema Atual: Nova Corretora

**Sintoma:** EA não aparece no gráfico e não abre operações

**Causa:** Você mudou de corretora e o símbolo mudou (ex: `XAUUSDc` → `XAUUSD`)

**Solução:** Siga o guia `ACAO_IMEDIATA.md` (5 minutos)

---

## 📚 Documentação

### Arquivos Essenciais

1. **`Docs/ACAO_IMEDIATA.md`** ⭐
   - Guia passo a passo para resolver o problema da corretora
   - **LEIA ESTE PRIMEIRO!**

2. **`Docs/ROADMAP_V1.0.md`**
   - Roadmap completo do projeto (V1.0 a V5.0)

3. **`RESUMO_EXECUTIVO.md`**
   - Resumo completo do projeto

---

## ⚡ Ação Imediata

**LEIA AGORA:** `Docs/ACAO_IMEDIATA.md`

Você está a **5 minutos** de ter o robô funcionando na nova corretora!

---

**Versão:** 1.10  
**Idioma:** Português (Brasil) 🇧🇷  
**Última atualização:** 30/07/2026
