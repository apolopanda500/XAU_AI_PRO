# 🔌 Ecossistema MCP do XAU AI PRO (pesquisa 2026)

## O que existe de terceiros (mapeamento)

| Servidor MCP | Foco | Limitação para nós |
|---|---|---|
| `aitrados/finance-trading-ai-agents-mcp` | agentes de finança multi-fonte | não fala com MT5 local |
| `triplom/financial-mcp-server` | dados de mercado (APIs públicas) | leitura apenas, sem execução |
| `razor-ai/tradingview-mcp` | TradingView (watchlist/gráficos) | amarrado ao TV, sem mesa própria |
| `Techie03/trade-mcp` | corretoras via API cloud | sem MT5 desktop, sem risk-gate local |
| `@modelcontextprotocol/server-github` | repos/code (já no nosso `.mcp.json`) | n/a |

**Conclusão:** nenhum MCP público opera um terminal **MT5 local** herdando
risk-gate + auditoria + emergency-stop. Por isso o projeto tem servidor próprio.

## Nosso servidor: `xau-trading` (backend/trading_mcp.py)

- **Ponte JSON-RPC 2.0 sobre stdio** (stdlib puro, zero dependências novas)
- **9 ferramentas**: health, account_summary, list_positions, get_quote,
  place_order, close_position, emergency_stop, emergency_resume, journal_tail
- **3 freios independentes**:
  1. Toda ordem nasce `execute=False` (dry-run: registra e valida, não envia à corretora)
  2. Execução real exige `execute=true` **e** env `XAU_MCP_TRADING=1` no servidor
  3. Emergency-stop do gateway corta tudo (independe do MCP)
- **request_id único monotônico** (itertools.count + time_ns): imune a dedupe do gateway
- **11 testes** (`tests/test_trading_mcp.py`) cobrindo freios, dry-run e protocolo

## Como ativar

Registro em `.mcp.json`:
```json
"xau-trading": {
  "command": ".venv/Scripts/python.exe",
  "args": ["-m", "backend.trading_mcp"],
  "env": { "XAU_MCP_GATEWAY": "http://127.0.0.1:9001" }
}
```

Uso com Claude/Codex (qualquer client MCP):
```
> tools/list            → 9 ferramentas disponíveis
> tools/call account_summary {}            → saldo/patrimônio da mesa
> tools/call list_positions {}             → posições + PnL por ticket
> tools/call place_order {"symbol":"XAUUSD","side":"buy","quantity":0.01}
  → dry-run (padrão): valida sem executar
```

Para HABILITAR execução real pela IA (decisão consciente do trader):
```powershell
$env:XAU_MCP_TRADING = "1"   # somente na sessão que roda o MCP
```

## Gráficos: escolha de mercado (pesquisa 2026)

`lightweight-charts` (TradingView, MIT, ~45kb) — consenso como a lib de
candlestick mais rápida para React; integrada via componente `PriceChart.tsx`.
Alternativas avaliadas: LightningChart (paga), Recharts (não é financeira).

## Roadmap MCP (produção)

- [ ] Token `XAU_MCP_TOKEN` no gateway remoto (mesma chave do app Android)
- [ ] Rate-limit por ferramenta no MCP (ex.: máx. 1 order/segundo)
- [ ] `prompts/` MCP (playbooks de análise: "revisar mesa", "auditar dia")
- [ ] Publicar o `xau-trading` como pacote pip para a comunidade
