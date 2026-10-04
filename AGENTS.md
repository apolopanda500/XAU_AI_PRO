# XAU AI PRO

## Escopo

Este repositório contém o app XAU AI PRO, o gateway Python, o backend Node, o frontend React/Tauri, o core Rust e os Expert Advisors MQL5.

O app é **100% desbloqueado**: execução DEMO e REAL, EA editável, MCP de trading e todas as rotas estão liberados.

Alterar `.mq5`, `.mqh`, `.mq4` ou `.set` **exige recompilar no MetaEditor64** (`C:\Program Files\MetaTrader 5\MetaEditor64.exe`) e **reanexar o EA ao gráfico**. Compilar não reanexa: o `.ex5` novo só entra em vigor quando o EA é trocado no gráfico.

**Nenhum workflow compila MQL5.** Verificado em 04/10/2026: existem runners `windows-latest` em `build-installer.yml`, `ci.yml` e `xau-ai-pro-validation.yml`, e **nenhum** invoca o MetaEditor. O `.ex5` também não é versionado (`.gitignore:37`, `MQL5/Experts/*/*.ex5`), então o artefato que prova a compilação não existe no repositório — por decisão.

A consequência é medida e precisa estar explícita: **um `.mq5` quebrado passa o CI inteiro.**

```
Core\ExecutionEngine.mqh(278) : error 256: undeclared identifier 'OrderSendResult'
```

Essa linha entrou no commit `dbdce10` e sobreviveu a **três ciclos** com 842 testes Python verdes ao lado — porque a suíte Python roda contra o fonte, e `mq5`/`mqh` não são módulos.

O que fecha essa lacuna, e é obrigatório antes de considerar uma mudança de EA pronta:

```powershell
python -m pytest tests/test_mql5_compila.py
```

Esse teste invoca o `MetaEditor64` de verdade e reprova em qualquer erro de compilação. Ele **pula** quando o MetaEditor não está disponível (CI em Linux) — nunca `xfail`, porque um `skip` que mascarasse erro seria o mesmo defeito que ele existe para pegar.

Guarda de alteração: `scripts/preflight.py::checar_mql5()` reprova qualquer diff em `MQL5/Experts` que não esteja declarado em `AUTORIZACOES_MQL5`. Alteração declarada dá `aviso`, nunca `ok`, porque compilar e reanexar são passos fora do repositório.

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
vezes com _Espaço insuficiente no disco_ antes de qualquer teste. `Temp/` já
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

## Pendencias atuais (verificado em 04/10/2026)

O estado abaixo foi medido por comando nesta sessao, nao herdado de
relatorio anterior. Onde a leitura antiga estava errada, esta marcado.

### Fechado (prova por comando)

| Item                                   | Prova                                                                                           |
| -------------------------------------- | ----------------------------------------------------------------------------------------------- |
| Nenhum ativo presumido                 | `TestNenhumAtivoPresumido` - 4 verdes                                                           |
| Nenhuma corretora como padrao          | `TestRoteamentoPorCorretora` - 4 verdes                                                         |
| Motor multi-corretora                  | `_loop` usa `UniversalRouter` + `market_access`                                                 |
| MT5 no mesmo fluxo de conexao          | `test_connection_contract` - 6 verdes                                                           |
| Nome real do modelo na tela            | lido do `.meta.json`                                                                            |
| Supervisor de processos (Tauri)        | `cargo test`                                                                                    |
| Build Rust linkando                    | `.cargo/config.toml` com `/PDB:NONE`                                                            |
| **Lockfiles versionados**              | `git ls-files` traz `frontend/package-lock.json` e `backend/package-lock.json`                  |
| **EA compila e tem trava de artefato** | `tests/test_mql5_compila.py`; MetaEditor `0 errors, 0 warnings`                                 |
| **Cron agendado**                      | `develop` foi mergeado em `main` (`46fd23b`); o YAML com `ref: develop` chegou a branch default |
| **Empacotamento no CI**                | passo "Preparar pasta de modelos" em `xau-ai-pro-validation.yml`                                |
| **Estilo com configuracao real**       | `.prettierrc.json` medido em checkout limpo; 202 arquivos formatados                            |

O item 7 da lista anterior ("`git push` dos lockfiles") esta **resolvido**: os dois
lockfiles estao versionados. O item 5 do `npm audit`NAO esta resolvido — ver abaixo.

### Pendente de CREDENCIAL (nao e codigo)

1. **Chaves de MEXC, Binance, Bybit e OKX** na maquina do operador. Os 4
   adaptadores tem envio HTTP real e testes verdes. Sem chave a resposta e
   `EXECUTION_NO_CREDENTIALS` e nada e enviado - correto.
2. **Conta corretora REAL** - hoje `MetaQuotes-Demo`, confirmado pelo heartbeat
   em disco (`%APPDATA%\MetaQuotes\Terminal\Common\Files\XAU_AI_PRO_heartbeat.json`).
   **Ultimo item da fila**, por decisao do dono: ele treina EA na DEMO.
3. **Certificado de CA publica** - artefados 1.2.4 tem certificado autoassinado.
   Custo ~$200-400/ano.

### Pendente de EXECUCAO (exige o app no ar)

4. **Reanexar o EA no grafico** - o `.ex5` do terminal ja tem o cooldown de
   margem, mas compilar NAO reanexa. O EA rodando continua sendo o antigo.
   **Este e o que destrava os dois proximos.**
5. **Forward test novo** - o anterior reprovou por margem. Causa raiz medida:
   4.165 de 4.246 `EXEC_NO_MARGIN`, concentrados entre **03h e 05h** (77%),
   com 3 dias de pico (938 / 801 / 1.452 / 918). Nao sao "3,4 erros por ciclo".
   A trava de margem JA EXISTIA e funcionava; o defeito era insistir depois de
   recusado. Corrigido com cooldown por simbolo, backoff 60 s -> 1 h
   (reducao medida de 3.191x). **Falta medir de novo.**
6. **Endurance 24h/72h/7d** - `scripts/endurance_test.py` existe, nao executado.
   Depende de 4 e 5.
7. **Teste em aparelho fisico Android** - nao ha aparelho.

### Pendente de TERCEIROS (nao ha o que fazer no codigo)

8. **6 vulnerabilidades `high` no backend, sem patch upstream.**
   Cadeia: `workflow -> @workflow/nest -> @swc/cli -> @xhmikosr/bin-wrapper
-> @xhmikosr/downloader -> got -> cacheable-request -> http-cache-semantics`.

   Medido em 04/10/2026:
   - `npm audit fix --dry-run` -> **nao altera nada**, as 6 continuam
   - `npm view http-cache-semantics version` -> `4.2.0`, que **e** a instalada

   O advisory (GHSA-ch52-4w7c-c8xp) diz `Patched versions: None`. **Nao existe
   versao corrigida.** O job `Dependency Audit` roda `npm audit --audit-level=high`
   e falha ate a Vercel publicar.

   A cadeia esta em `workflow`, importado so por `backend/workflows/index.mjs`
   (rotas da Vercel). O app desktop roda `backend/server-desktop.cjs`, que e
   express puro e nao toca essa cadeia.

9. **Super-Linter `quality` - 30 linters, 2 causas distintas.**
   - **11 linters do Prettier** estao desligados no workflow (`YAML_PRETTIER:
false` e companhia) desde um ciclo anterior, com o comentario de que
     religar so para pintar o CI seria esconder defeito. A configuracao
     `.prettierrc.json` + `.prettierignore` **agora existe**, entao o caminho
     para religar esta aberto - e e decisao do dono.
   - **19 outros** (`PYTHON_RUFF`, `PYTHON_MYPY`, `GITLEAKS`, `TRIVY`,
     `CHECKOV`, `SQLFLUFF`...) rodam com defaults, sem config no repo.
     O projeto tem `.pylintrc` e `.gitleaks.toml`, e nao tem `ruff.toml`,
     `setup.cfg`, `.flake8`, `mypy.ini` nem `.editorconfig`.

### Regra de limpeza

Antes de `git status` travar: `.\scripts\limpeza_segura.ps1 -Apply -DebugCache`.
A ACL do `target\debug` se corrompe a cada build; o script ja corrige.

Nao apagar nada com build ou teste no ar. Ja custou um ciclo: remover a pasta
do `--basetemp` com o `pytest` rodando produziu 6 `ERROR` que nao eram falha de
codigo.
