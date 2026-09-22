# XAU AI PRO — Decoupling MT5: Operar sem Terminal MT5

**Problema Principal:** O app depende do MT5 rodando para funcionar, mas deveria operar em outras corretoras independentemente.

---

## 🔍 Análise do Problema

### Dependência Atual do MT5

1. **Cotações de mercado** — Usam `/api/mt5/quotes` que consulta MT5
2. **Posições** — Usam `mt5.positions_get()` diretamente  
3. **Conta/Saldo** — Usam `mt5.account_info()`
4. **Estado do sistema** — Verifica se `terminal64.exe` está rodando
5. **EA Heartbeat** — Lê arquivo `XAU_AI_PRO_heartbeat.json` do MT5

### O que JÁ FUNCIONA sem MT5
✅ **Binance** — Cliente dedicado `backend/binance_client.py`  
✅ **MEXC** — Cliente dedicado `backend/mexc_client.py`  
✅ **Universal Overview** — `/api/universal/overview` já suporta sem MT5

### O que PRECISA ser corrigido

| Componente | Problema | Solução |
|------------|----------|---------|
| Market Quotes | Depende `/api/mt5/quotes` | Usar universal quotes |
| System Health | Verifica terminal64.exe | Status por broker |
| Frontend | Filtra por MT5 apenas | Multi-fonte |

---

## 🎯 Solução Proposta

### 1. Backend — Nova Rota Universal

```python
@app.get("/api/universal/quotes")
async def universal_quotes(symbols: str):
    """Quotes universais - tenta múltiplas fontes"""
    # Tenta MT5, Binance, MEXC até conseguir dados
    # Retorna com source indicado para cada quote
```

### 2. Frontend MarketTab — Fallback

```typescript
// Tenta MT5 primeiro, se offline usa Binance/MEXC
const fetchQuotes = async (symbols) => {
  try {
    // MT5
    const mt5Res = await fetch(`${MT5}/api/mt5/quotes...`);
    if (mt5Res.ok) return mt5Res.json();
  } catch {}
  
  // Fallback Binance
  try {
    const binanceRes = await fetch(`${API}/api/universal/quotes?broker=binance...`);
    if (binanceRes.ok) return binanceRes.json();
  } catch {}
  
  // Fallback MEXC
  ...
};
```

### 3. System Tab — Status por Broker

```tsx
<div className="sources-grid">
  <div className="source-item">
    <strong>MT5</strong>
    <span className={`chip ${mt5Connected ? 'ok' : 'warn'}`}>
      {mt5Connected ? 'Conectado' : 'Offline'}
    </span>
  </div>
  <div className="source-item">
    <strong>Binance</strong>
    <span className={`chip ${binanceConnected ? 'ok' : 'warn'}`}>
      {binanceConnected ? 'Conectado' : 'Offline'}
    </span>
  </div>
  <div className="source-item">
    <strong>MEXC</strong>
    <span className={`chip ${mexcConnected ? 'ok' : 'warn'}`}>
      {mexcConnected ? 'Conectado' : 'Offline'}
    </span>
  </div>
</div>
```

---

## ✅ Verificação

### Sem MT5 rodando:
- [ ] App carrega sem erro
- [ ] Binance dados aparecem  
- [ ] MEXC dados aparecem
- [ ] MarketTab funciona
- [ ] System Tab mostra status por broker

---

## 📋 Implementação

### Fase 1 (Hoje):
1. Modificar MarketTab para fallback universal
2. System Tab mostrar status por broker

### Fase 2 (Esta semana):
3. Nova rota `/api/universal/quotes` no backend
4. Modificar `_ensure_mt5()` para não erro

### Fase 3 (Próxima):
5. Cache SWR para quotes
6. Configuração de fontes pelo usuário
