# Registro de autoria — 25/10/2026

Regra 11 do AGENTS.md: com dois agentes no mesmo working tree, cada arquivo tem
dono registrado, com caminho e tamanho do diff. Sem isto, o proximo ciclo nao
sabe o que pode tocar.

## Ciclo 25/10/2026 — catálogo MCP (agente 1)

Revisao do catalogo `mcp/servers/` e correcoes A1–A8, todas com teste proprio
e prova negativa. Suite medida: **1558 passed, 2 skipped, 318.17s**.

| Arquivo | Diff | O que |
|---|---|---|
| `app/integrations_client.py` | 230 linhas | loader: pasta como unica fonte (A1), campos mortos fora (A2), ping sem ramos inalcancaveis (A3), `defeitos=` com motivo (A4), endpoint do gateway pelo ambiente (A7) |
| `tests/test_app_core.py` | 235 linhas | travas A1–A4, A7 + provas negativas |
| `tests/test_mcp_status.py` | 71 linhas | trava A8 (header `Authorization`) com e sem token |
| `app/tabs/integrations.py` | 30 linhas | campo `DATABASE_URL` removido, etiqueta de defeitos do catalogo |
| `app/mcp_tools.py` | 26 linhas | A8: header de autorizacao do conector, fonte `token_gateway` |
| `Docs/ANALISE_ESTRUTURA_20260918.md` | 7 linhas | L12 marcado FECHADO com medicao; registry marcado como removido |
| `mcp/servers/mt5_gateway.json` | 5 linhas | A2: `needs_api_key`, `api_key_env`, `id` fora |
| `mcp/servers/tradingview.json` | 5 linhas | A2: idem |
| `mcp/servers/registry.json` | −6 linhas | A1: deletado — fonte de nada |
| `mcp/servers/test_sequential_thinking.py` | −99 linhas | A6: movido (existe em `scripts/testar_sequential_thinking.py`) |

## Fora deste commit

- `package.json` e `package-lock.json` — `canvas` (devDependency de build),
  **nao commitados** (decisao do dono: sao de build). Nao sao deste agente.
- `backend/risk_gate.py`, `tests/test_risk_gate.py`,
  `tests/test_rejection_matrix.py`, `Docs/STATUS_ATUAL.md` — outro agente,
  ja commitados por ele em `1519755 fix(risk_gate)` e pushados.
