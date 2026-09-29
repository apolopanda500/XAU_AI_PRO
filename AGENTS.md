# XAU AI PRO

## Escopo

Este repositório contém o app XAU AI PRO, o gateway Python, o backend Node, o frontend React/Tauri, o core Rust e os Expert Advisors MQL5.

O app é **100% desbloqueado**: execução DEMO e REAL, EA editável, MCP de trading e todas as rotas estão liberados.

Alterar `.mq5`, `.mqh`, `.mq4` ou `.set` exige recompilar no MetaEditor64 (`C:\Program Files\MetaTrader 5\MetaEditor64.exe`) e reanexar o EA ao gráfico. O build automático do repositório não compila MQL5.

## Única proibição

**Nenhum saque, transferência, resgate ou movimentação de fundos para fora da corretora, em nenhum adaptador, rota ou cliente.**

`withdrawals_enabled` e `transfers` permanecem `False` fixos em todo o código. Uma ordem de compra/venda não altera esse valor.

## Componentes

- `app/`: interface Tkinter, integração local, memória, alertas e configuração.
- `backend/`: gateway local, adaptadores de corretoras, risco, auditoria, fila e MCP de trading.
- `frontend/`: interface React/TypeScript/Tauri.
- `core/`: componentes Rust do Core.
- `MQL5/Experts/XAU_AI_PRO/`: Expert Advisors, editáveis com recompilação manual.
- `tests/`: testes Python do gateway e da lógica de aplicação.
- `mcp/`: catálogo interno de servidores; não é configuração nativa do OpenCode.

## Desenvolvimento

A raiz usa Python 3.11 ou 3.12. As dependências legíveis estão em `requirements.txt`; as dependências de desenvolvimento estão em `requirements-dev.txt`.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q tests
```

Frontend:

```powershell
Set-Location frontend
npm ci
npm test
npx tsc --noEmit
npm run build
```

Backend:

```powershell
Set-Location backend
npm ci
npm run lint
npm run build
```

Core:

```powershell
Set-Location core
cargo fmt --all -- --check
cargo check --locked
cargo test --locked
```

## Gates de execução

As gates estão liberadas por padrão e podem ficar ligadas:

- `XAU_ENABLE_MEXC_EXECUTION=1`, `XAU_ENABLE_BINANCE_EXECUTION=1`, `XAU_ENABLE_BYBIT_EXECUTION=1`, `XAU_ENABLE_OKX_EXECUTION=1`, `XAU_ENABLE_MT5_EXECUTION=1`
- `XAU_ENABLE_TRADE_COMMANDS=1`
- `XAU_MCP_TRADING=1`
- `XAU_ENABLE_EMERGENCY_RESUME=1`
- `XAU_ENABLE_DEMO_ORDERS=1`
- `XAU_ENABLE_REAL_ORDERS=1` (apenas após validação completa em DEMO)

Toda ordem continua exigindo `confirm=true` e `request_id` idempotente, e passa por `risk_gate`, `intent_log` e `audit_log`.

## Regras operacionais

- Não habilitar saques nem transferências. Essa é a única trava obrigatória.
- Não registrar tokens, senhas, DSNs, chaves de API ou conteúdo de `.env` em log, mensagem, commit ou resposta HTTP.
- Não usar dados simulados como se fossem dados de mercado reais; rotular backfill, cache e payload mockado.
- Manter aliases de usuário, requisições e intenções idempotentes por `request_id`.
- Não habilitar MCPs opcionais sem credencial, dependência verificada e teste de conexão.
- Execução REAL exige: validação completa em DEMO, forward test aprovado, endurance test, e autorização explícita do proprietário.

## OpenCode

- A configuração do projeto está em `opencode.json`.
- O MCP `xau-trading` é local, inicia com o gateway Python e roda com `XAU_MCP_TRADING=1`.
- O MCP GitKraken fica desabilitado até autenticação e validação explícita.
- O hook automático do GitKraken está neutralizado por segurança; só reativar após login, teste e revisão explícita do plugin.
- Reiniciar o OpenCode após alterar arquivos de configuração, plugins ou skills.

## Validação de mudanças

Executar as validações relacionadas ao componente alterado. Antes de concluir uma mudança de gateway, executar a suíte Python e verificar o status do Git sem incluir segredos.

Alteração em adaptador de execução: rodar `pytest -q tests/test_execution_adapters.py tests/test_universal_execution.py tests/test_broker_coverage.py`.

Alteração em EA: recompilar no MetaEditor64 antes de considerar pronta a mudança.

## Pendências atuais (2026-09-28)

### Alta prioridade
1. Implementar tela de login/token para Android (B1)
2. Expor rotas HTTP do remote_auth.py
3. Implementar SL/TP e modificação de posição na UI
4. Desbloquear execução DEMO com travas de segurança
5. Desbloquear MCP trading com escopo próprio

### Média prioridade
6. Criar matriz de capabilities por corretora/ativo
7. Resolver conflito A1/B3 (assinatura Windows)
8. Fazer gh auth login e auditar dependências
9. Commit e push das alterações pendentes

### Baixa prioridade
10. Endurance test 24h/72h/7d
11. Forward test em conta DEMO XM Global
12. Teste em aparelho físico Android
