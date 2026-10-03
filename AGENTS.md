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

O cache de build do Rust vive **fora** do disco do código, em
`Temp\cargo-target` (definido por `scripts\build_app.bat`). Em 30/09/2026 o
`target` dentro do repositório chegou a 3,9 GB e o `cargo check` falhou duas
vezes com *Espaço insuficiente no disco* antes de qualquer teste. `Temp/` já
está no `.gitignore` e na allowlist de `scripts\limpeza_segura.ps1`.

## Nenhum ativo e nenhuma corretora são fixos

Duas regras do dono, ambas verificadas por teste:

- **Nenhum símbolo pode ser presumido.** Símbolo vazio é **recusa com
  motivo**, nunca um ativo padrão. A regra já estava escrita em
  `app/market_symbols.py` (`return ""  # sem ativo fixo`).
- **Nenhuma corretora pode ser caminho exclusivo.** MT5 é uma entrada entre
  nove em `backend/broker_registry.py`, não o padrão. Escolher uma corretora
  na tela tem de ser a corretora que realmente opera.

Trava: `tests/test_ai_inference.py::TestNenhumAtivoPresumido` e
`tests/test_auto_engine.py::TestRoteamentoPorCorretora`.

O que **não** viola a regra: tabelas de mapeamento (`app/market_data.py`),
o `Literal` de `backend/universal_contracts.py` (é a lista de suportadas) e o
`broker_registry` (é o catálogo). Ver `docs/LEVANTAMENTO_20260930.md` §4.

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

## Pendencias atuais (verificado em 30/09/2026)

A lista anterior (12 itens, de 28/09) foi **substituida**: todos ja foram
resolvidos ou sao de credencial. O estado real, medido por comando:

### Fechado nesta sessao (30/09/2026)

| Item | Prova |
|---|---|
| Nenhum ativo presumido | `TestNenhumAtivoPresumido` - 4 verdes |
| Nenhuma corretora como padrao | `TestRoteamentoPorCorretora` - 4 verdes |
| Motor multi-corretora | `_loop` usa `UniversalRouter` + `market_access` |
| MT5 no mesmo fluxo de conexao | `test_connection_contract` - 6 verdes |
| Nome real do modelo na tela | `Floresta_XAUUSD_H1`, lido do `.meta.json` |
| Supervisor de processos (Tauri) | `cargo test` - 11 verdes |
| Build Rust linkando | `.cargo/config.toml` com `/PDB:NONE` |
| Ambiente com espaco | 0,87 GB -> 17 GB |

### Pendente de CREDENCIAL (nao e codigo)

1. **Chaves de MEXC, Binance, Bybit e OKX** na maquina do operador. Os 4
   adaptadores tem envio HTTP real (`mexc_client.py:135`, `okx_client.py:143`,
   `binance_client.py:128`, `bybit_client.py:140`) e **59 testes verdes**.
   Sem chave a resposta e `EXECUTION_NO_CREDENTIALS` e nada e enviado - correto.
2. **Conta corretora REAL** - `XAU_ACCOUNT_KIND=real`. Hoje e
   `MetaQuotes-DEMO`.
3. **Certificado de CA publica** - os artefatos 1.2.4 tem certificado
   autoassinado; o Windows mostra `UnknownError`. Custo ~$200-400/ano.

### Pendente de EXECUCAO (exige o app no ar)

4. **Endurance 24h/72h/7d** - `scripts/endurance_test.py` existe, nao executado.
5. **Aprovacao do forward test** - a janela existe e e real (14.265 eventos,
   26 dias, 1.251 starts, 269 aberturas), **mas nao passa**: 4.246
   `BROKER_ERROR` = 3,4 erro de broker por ciclo. Ver
   `Docs/MAPEAMENTO_10_10_VERIFICADO_20260930.md`.
6. **Teste em aparelho fisico Android** - nao ha aparelho.
7. **`git push` dos lockfiles** - `gh auth` JA ESTA AUTENTICADO
   (`apolopanda500`, escopo `repo`). O GitHub reporta **81 alertas do
   Dependabot** (5 critical, 31 high) que NAO refletem o codigo instalado:
   `npm audit` local da **0 vulnerabilidades** em frontend e backend. O
   `chromadb` (4 critical) nao esta instalado nem importado; `tar` (1 critical)
   da `(empty)` no `npm ls`. Os alertas fecham quando os lockfiles forem
   enviados - nao ha vulnerabilidade a corrigir no codigo.

### Regra de limpeza

Antes de `git status` travar: `.\scripts\limpeza_segura.ps1 -Apply -DebugCache`.
A ACL do `target\debug` se corrompe a cada build; o script ja corrige.