# MCP & Configuração do Cline — Registro da Sessão

> **Data**: 09/08/2026 · **Projeto**: XAU_AI_PRO (trading XAUUSD — Ouro)
> **Objetivo**: Configurar MCP servers integrando dados de mercado e MetaTrader 5 ao Cline.

---

## 1. Resumo do que foi feito nesta sessão

1. **Instalado o Bybit MCP** (pacote oficial `bybit-official-trading-server@2.1.16`) no Claude Code (`.claude.json`) e Cursor (`mcp.json`) — 372 tools.
2. **Análise completa das configurações do Cline no Windows** — `.cline\`, `.clinerules\` e `globalStorage` do VS Code.
3. **Correção**: `ccxt-mcp-server.py` estava em encoding legado (cp1252) → convertido para **UTF-8** (o Python não conseguia abrir o arquivo).
4. **Ajuste de segurança**: `executeAllCommands: false` no `autoApprovalSettings` (agora só comandos seguros).
5. **Registrados os servidores financeiros**: `ccxt`, `coingecko`, `fmp`.
6. **Integração MetaTrader 5**: instalado `mt5-mcp` (pip) — leitura de posições/dados/indicadores do EA XAU_AI_PRO + `mql5-ea-mcp` (docs MQL5).
7. **Kit de produtividade**: adicionados `context7`, `fetch`, `playwright`, `git`, `skillselion` (`add-mcp` instalado globalmente).
8. **Limpeza**: removido `filesystem` duplicado; `puppeteer` desativado (usar `playwright`).

---

## 2. Caminhos importantes

| Item | Caminho |
|---|---|
| EA XAU_AI_PRO (MT5) | `C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Experts\XAU_AI_PRO` |
| Workspace principal | `C:\Users\Micro\Downloads\XAU_AI_PRO` |
| Config MCP real do Cline | `C:\Users\Micro\AppData\Roaming\Code\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json` |
| Config MCP Claude Code | `C:\Users\Micro\.claude.json` |
| Config MCP Cursor | `C:\Users\Micro\.cursor\mcp.json` |
| Serv MCP Python financeiros | `C:\Users\Micro\.clinerules\mcp-servers\` |
| Regras/idioma global Cline | `C:\Users\Micro\.cline\rules\00-idioma-portugues.md` |
| Estado global Cline | `C:\Users\Micro\.cline\data\globalState.json` |

---

## 3. Stack MCP final do Cline (16 servidores — 15 ativos)

### Ativos
| Nome | Comando | Uso |
|---|---|---|
| `mt5` | `mt5-mcp` | MetaTrader 5 (posições, mercado, indicadores, EA logs) — read-only |
| `mql5-ea` | `npx -y mql5-ea-mcp@1.4.1` | Documentação MQL5 + diagnóstico de erros de compilação |
| `ccxt` | `python ...\ccxt-mcp-server.py` | Cripto multi-exchange (5 tools) |
| `coingecko` | `python ...\coingecko-mcp-server.py` | Cripto dados CoinGecko (9 tools) |
| `fmp` | `python ...\fmp-mcp-server.py` | Ações/ETFs via Financial Modeling Prep (10 tools) — requer `FMP_API_KEY` |
| `context7` | `npx -y @upstash/context7-mcp` | Docs de bibliotecas por versão |
| `fetch` | `mcp-server-fetch` | Busca/leitura web (Python) |
| `playwright` | `npx -y @playwright/mcp` | Automação de browser/testes |
| `git` | `python -m mcp_server_git` | Git integrado |
| `skillselion` | `npx -y skillselion-mcp` | Catálogo de skills/MCPs |
| `sequential-thinking` | npx | Raciocínio sequencial |
| `memory` | npx | Memória de grafo de conhecimento |
| `filesystem` | npx (raiz XAU_AI_PRO) | Acesso a arquivos |
| `time` | `python -m mcp_server_time` | Hora/fuso |
| `sqlite` | `python -m mcp_server_sqlite --db-path ...\trading.db` | Banco local |

### Desativado
| Nome | Motivo |
|---|---|
| `puppeteer` | Substituído pelo `playwright` |

---

## 4. Pendências / Chaves a configurar (variáveis de ambiente — nunca hardcode)

- [ ] `FMP_API_KEY` → para o servidor `fmp`
- [ ] `ALPHAVANTAGE_API_KEY` → se usar o MCP Alpha Vantage
- [ ] `BYBIT_API_KEY` / `BYBIT_API_SECRET` → para trading via Bybit (ou `BYBIT_TESTNET=true` em testnet)
- [ ] `SYNAPSE_LICENSE_KEY` → apenas se comprar o synapse-mt5 (US$49, Gumroad) — alternativa open-source `mt5-mcp` já instalada
- [ ] Ativar trading no `mt5` (`MT5_MCP_TRADING_ENABLED=true`) — **só em conta demo**

---

## 5. Recomendações de segurança

- Auto-approve: `executeAllCommands: false` (já aplicado) ✅
- Habilitar trading do MT5 somente em **conta demo**
- Bybit: usar permissões read-only + allowlist de IP + sem saque
- Os servidores financeiros trabalham em modo **read-only** por padrão

---

## 6. Regra global de idioma

Todas as respostas/comentários/documentação em **Português (Brasil)** — regra permanente (`00-idioma-portugues.md`).

---

## 7. Próximos passos sugeridos

1. Reiniciar VS Code/Cline para carregar os 16 MCPs.
2. Configurar `FMP_API_KEY` no ambiente.
3. Testar consultas: "*mostre posições do MT5*", "*RSI do XAUUSD*", "*docs do pandas*".
4. Se travar/consumir muito contexto: desativar MCPs pouco usados (`disabled: true`).