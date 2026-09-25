# XAU AI PRO

## Escopo

Este repositório contém o app XAU AI PRO, o gateway Python, o backend Node, o frontend React/Tauri e o core Rust.

Os Expert Advisors e arquivos MQL5 são intocáveis. Não criar, editar, mover, excluir, formatar, gerar ou sobrescrever arquivos `.mq4`, `.mq5`, `.mqh`, `.set` ouanything dentro de `MQL5/Experts`.

## Componentes

- `app/`: interface Tkinter, integração local, memória, alertas e configuração.
- `backend/`: gateway local, adaptadores de corretoras, risco, auditoria, fila e MCP de trading.
- `frontend/`: interface React/TypeScript/Tauri.
- `core/`: componentes Rust do Core.
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

## Regras operacionais

- Usar paper/demo até concluir backtest, forward test e validação de risco.
- Manter `XAU_MCP_TRADING=0` e `XAU_ENABLE_EMERGENCY_RESUME=0`; execução real exige uma etapa posterior explícita e separada.
- Não Enables saques, transferências ou acesso a credenciais.
- Não registrar tokens, senhas, DSNs, chaves de API ou conteúdo de `.env`.
- Não habilitar MCPs opcionais sem credencial, dependência verificada e teste de conexão.
- Não usar dados simulados como se fossem dados de mercado reais.
- Manter aliases de usuário, requisições e intenções idempotentes.

## OpenCode

- A configuração do projeto está em `opencode.json`.
- O MCP `xau-trading` é local e inicia com o gateway Python; ele preserva dry-run e as travas de risco.
- O MCP GitKraken fica desabilitado até autenticação e validação explícita.
- O hook automático do GitKraken está neutralizado por segurança; só reativar após login, teste e revisão explícita do plugin.
- Reiniciar o OpenCode após alterar arquivos de configuração, plugins ou skills.

## Validação de mudanças

Executar apenas as validações relacionadas ao componente alterado. Antes de concluir uma mudança de gateway, executar a suíte Python e verificar o status do Git sem incluir segredos. Não declarar prontidão para mercado real sem conta demo, testes de rejeição, auditoria, kill switch e revisão dos limites de risco.
