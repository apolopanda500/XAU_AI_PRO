# Mapeamento 10/10 — XAU AI PRO

Cada camada só marca 10/10 quando **todos** os critérios abaixo forem verificados
por comando, não por impressão. A verificação é o comando indicado na coluna
"Como provar". Data de montagem: 2026-09-28. Última verificação: 2026-09-28 14:35.

Regra geral que vale para todas as camadas:

- nenhum `.mq4/.mq5/.mqh/.set` alterado;
- nenhum segredo (chave, token, DSN, conteúdo de `.env`) no repositório;
- `git status` limpo de arquivos temporários (`_tmp*`, `_t.py`, logs de treino).

---

## 1. Gateway (backend Python)

| Critério | Como provar | Resultado |
|---|---|---|
| Suíte inteira verde | `python -m pytest -q tests` | **590 passed** |
| Sem rota `/api/demo/` restante | grep em `backend/*.py`, `frontend/src`, `scripts` | **0** |
| Sem nome de comando `demo/*` restante | grep `'demo/` / `"demo/` em `backend/*.py` | **0** |
| Env var legada só em fallback | toda ocorrência de `XAU_ENABLE_DEMO_ORDERS` também cita `XAU_ENABLE_TRADE_COMMANDS` | **0 ocorrência órfã** |
| Travas de execução presentes | `XAU_MCP_TRADING`, `XAU_ENABLE_TRADE_COMMANDS`, `XAU_ENABLE_EMERGENCY_RESUME` | **presentes** |
| Gatilho por corretora | `XAU_ENABLE_{MEXC,BINANCE,BYBIT,OKX,MT5}_EXECUTION` em `universal_router.EXECUTION_GATES` | **5 gates** |
| Sem vocabulário de recusa por tipo de conta | grep `indisponíveis nesta versão`, `somente prévia`, `ordens REAIS indispon`, `conta DEMO confirmada` | **0** |
| Ordem real não é recusada | `test_rejection_matrix`, `test_real_usa_as_mesmas_travas_do_trade` | **verde** |

**Estado: 10/10.**

---

## 2. Frontend

| Critério | Como provar | Resultado |
|---|---|---|
| TypeScript sem erro | `npx tsc --noEmit` | **exit 0** |
| Testes verdes | `npm test` | **191 passed (20 arquivos)** |
| Build de produção | `npm run build` | **exit 0** |
| Tom de chip usado tem regra em CSS | `pytest tests/test_interface_surface.py` | **0 tom órfão** |
| Rótulo de carregamento usa `…` | idem (allowlist dos órfãos de M4) | **0 com `...`** |
| Nenhuma classe sem estilo | idem | **0 `empty-state`** |
| Sem `demo-order-panel`/`DemoOrderPanel` | grep em `frontend/src` | **0** |
| Sem ids `demo-*` no card de ordem | grep `demo-side|demo-volume|demo-sl|demo-tp|demo-kind|demo-price` | **0** (renomeados para `xau-*`) |
| Card de modelos cobre os 9 símbolos | `/api/ai/trained` → agrupamento `porSimbolo` | **9 blocos, 36 chips** |

Card redesenhado com identidade XAU: selo dourado `XAU AI PRO`, `.xau-symbol`,
chips `.is-real`/`.is-demo` com ponto pulsante, escudo `.xau-guard`, botões
compra/venda com seta. Inventário de modelos agrupado por símbolo com
`<optgroup>` no seletor e chips clicáveis que selecionam o artefato.

Aba Robô reorganizada em sub-abas (**Modelo & Sinal | Operação | Ordem |
Ativos | Copiloto**), todos os painéis montados e só escondidos por `hidden`
(para não perder estado), Mini Terminal sempre no fim. Histórico virou a fonte
única do `useHistorico` e monta o Analytics nas mesmas classes do período do
filtro, sem hook duplicado. Vocabulário de chip (`.ok`, `.warn`, `.danger`,
`.neutral`, `.primary`, `.mt5`) centralizado em `theme/global.css` — `.neutral`
e `.mt5` saíram de `theme/history.css`, que era importado só pelo Histórico.
Carregamento usa `…` em todo o app; guarda automática em
`tests/test_interface_surface.py` (o frontend não tem `@types/node`, e o
pipeline entrega CSS vazio ao Vitest, então a verificação é em Python).

**Estado: 10/10.**

---

## 3. Modelos / IA

| Critério | Como provar | Resultado |
|---|---|---|
| Inventário sem órfão (meta sem `.pkl`) | conferir `Python/models` | **0 órfãos, 0 publicados sem artefato** |
| Todos os símbolos do dataset treinados | 9 símbolos × 4 timeframes | **36 modelos = 9 × 4** |
| Cobertura por símbolo | `listar_modelos()` agrupado | AUDUSD/BTCUSD/ETHUSD/EURUSD/GBPUSD/NZDUSD/USDCAD/USDJPY/XAUUSD — **4 cada** |
| Reprovados mantidos com motivo | `publicable=false` + `reason` | **11 reprovados com motivo** |
| Inferência usa o modelo do ativo pedido | `_carregar(symbol, timeframe)` em `inferir` | **corrigido** |
| Catálogo cobre todos os símbolos | `listar_modelos()` ≠ glob `XAUUSD_*` | **meta.json como fonte** |
| Modelos públicos | `publicable && pklPresent` | **25** |

**Estado: 10/10.**

---

## 4. Rust / Core

| Critério | Como provar | Resultado |
|---|---|---|
| Formatação | `cargo fmt --all -- --check` | **exit 0** |
| Compila sem erro | `cargo check --locked` | **exit 0** (1 aviso `dead_code` pré-existente em `MT5Bridge`) |
| Testes | `cargo test --locked` | **38 passed** |

**Estado: 10/10.**

---

## 5. Tauri

| Critério | Como provar | Resultado |
|---|---|---|
| `tauri.conf.json` compila | `npm run tauri build` | **exit 0, 2 bundles** |
| `identifier`, `productName`, `version` corretos | ler JSON | `com.xau-ai-pro.desktop` / `XAU AI PRO` / **1.2.4** |
| `frontendDist` aponta para `dist` | ler JSON | `../dist` |
| `beforeBuildCommand` | ler JSON | `npm run build` |

**Estado: 10/10.**

---

## 6. Versão / Projeto

| Critério | Como provar | Resultado |
|---|---|---|
| Mesma versão em todos os manifestos | `python scripts/sync_version.py --check` | **Todos alinhados (8 alvos)** |
| Bug do sincronizador corrigido | `pyproject.toml` tem `[tool.poetry]` E `[project]` | **`_patch_toml` agora substitui todas as ocorrências** |
| Pontos manuais alinhados | grep `1.2.3` | só comentários históricos, `parse_version("1.2.3")` (teste) e scripts de auditoria |
| Build id coerente | `GATEWAY_BUILD` / `EXPECTED_GATEWAY_BUILD` | `xau-ai-pro-1.2.4-universal-20260928` |

Alvos do `sync_version.py`: `VERSION`, `pyproject.toml`, `backend/package.json`,
`frontend/package.json`, `frontend/src-tauri/Cargo.toml`,
`frontend/src-tauri/tauri.conf.json`, `core/Cargo.toml`, `frontend/src/version.ts`.
Pontos fora do script (manuais): `fastapi_gateway.py`, `mt5_gateway.py`,
`okx_client.py`, `trading_mcp.py`, `main.rs`, `main.tsx`, `app/*`,
`app/data/config.json`, `tests/test_universal_router_dispatch.py`.

**Estado: 10/10.**

---

## 7. Empacotamento / Instalador

| Critério | Como provar | Resultado |
|---|---|---|
| EXE gerado e atualizado | `frontend/src-tauri/target/release/XAU AI PRO.exe` | **13.605.376 bytes — 09-28 14:30:50** |
| NSIS (`-setup.exe`) gerado | `bundle/nsis/` | **`XAU AI PRO_1.2.4_x64-setup.exe` — 212.819.524 bytes — 14:30:50** |
| MSI gerado | `bundle/msi/` | **`XAU AI PRO_1.2.4_x64_en-US.msi` — 327.721.664 bytes — 14:20:43** |
| Artefatos do mesmo build | mesma execução de `scripts/build_app.bat` | **sim** (MSI antes, NSIS depois — sequencial do bundler) |
| Instaladores 1.2.3 anteriores removidos | `bundle/**/*1.2.3*` | **0** (216 KB / 152 KB não continham nem o exe de 13 MB) |

**Estado: 10/10.**

---

## 8. Modelos dentro do bundle

| Critério | Como provar | Resultado |
|---|---|---|
| `Python/models/*.pkl` incluídos no instalador | contar no `main.wxs` do WiX | **36 `.pkl` + 36 `.meta.json` = 72** |
| Gateway congelado incluído | contar no `main.wxs` | **`mt5-gateway.exe` + 5137 arquivos de `bridge/_internal`** |
| Core incluído | contar no `main.wxs` | **`xau-ai-pro-core.exe`** |
| Total de arquivos no MSI | contar `<File Id` | **5208** |
| Caminho instalado bate com o resolver | `<DirectoryRef Id="INSTALLDIR">` → `Python` → `models` | **`<instalacao>\Python\models` = candidato 4 de `_resolver_modelos()`** |
| Gap de build corrigido | `scripts/build_app.bat` | **etapa 6 agora faz `robocopy /MIR` de `Python/models`** |
| Sem `.env` nem chave dentro do bundle | grep `.env` no `main.wxs` | **0** |

O `build_app.bat` nunca sincronizou `Python/models`; `frontend/src-tauri/Python/models`
estava congelado com só XAUUSD (5 arquivos / 6,9 MB). Com a etapa nova o
estágio tem os 72 arquivos / 342,6 MB e o instalador os carrega.

**Estado: 10/10.** Prova ao vivo executada em 2026-09-28 14:35: `msiexec /i …
/qn /norestart /L*V` devolveu **exit 0** com `Product: XAU AI PRO -- Installation
completed successfully` no log; `C:\Program Files\XAU AI PRO\XAU AI PRO.exe`
passou a ter o timestamp do build atual, `bridge\mt5-gateway.exe` o do PyInstaller
desta execução, e o app subiu sozinho no ar (UI, gateway `127.0.0.1:9001`
respondendo, core iniciado). O NSIS `/S` saiu com 0 mas **não** substituiu o exe —
instalar pelo MSI.

---

## 9. Segurança

| Critério | Como provar | Resultado |
|---|---|---|
| `.env` fora do git | `git check-ignore .env` | **`.gitignore:71:.env*`** |
| `.env` fora do git (rastreado) | `git ls-files \| grep ^\.env` | **só `.env.example`** |
| `.env` fora do bundle | grep `.env` no `main.wxs` | **0** |
| Sem segredo em `git status` | varredura do status | **0** |
| Permissões do `opencode.json` negam `.env` e MQL5 | ler JSON | **presentes** |
| Execução real exige etapa separada | env flags obrigatórias | `XAU_MCP_TRADING`, `XAU_ENABLE_TRADE_COMMANDS`, `XAU_ENABLE_<BROKER>_EXECUTION` |
| Kill switch testado | `test_emergencia_e_real_bloqueados` | **verde** |
| PyInstaller não embute `.env` | `mt5-gateway.spec` | **sem `datas` de `.env`** |

**Estado: 10/10.**

---

## 10. Repositório

| Critério | Como provar | Resultado |
|---|---|---|
| Sem temporários no `git status` | `git status --porcelain` | **0 entradas `_tmp`/`_t.py`/`_treino`/`Temp`** |
| Temporários ignorados | `git check-ignore _treino Temp` | **`Temp/` (L41), `_treino/` (adicionado)** |
| Sem segredos no diff | varredura de padrões | **0** |
| Não rastreados são só código/docs novos | `git status` | `Docs/ESTADO_E_PENDENCIAS.md`, `Docs/MAPEAMENTO_10_10.md`, `ErrorBoundary.tsx`, `OrderPanel.tsx`, `copilot-table.css`, `RobotTabs.tsx`, `RobotTabs.test.tsx`, `RobotModelPanel.test.tsx`, `SystemHealthOnly.test.tsx`, `HistoryTab.test.tsx`, `robot-subtabs.css`, `tests/test_interface_surface.py` |
| MQL5 intocado | AGENTS.md | **nenhum `.mq4/.mq5/.mqh/.set` alterado** |

**Estado: 10/10.**

---

## Comandos de verificação (uma passada só)

```powershell
.\.venv\Scripts\python.exe scripts\sync_version.py --check
.\.venv\Scripts\python.exe -m pytest -q tests
Set-Location frontend; npx tsc --noEmit; npm test; npm run build; Set-Location ..
Set-Location backend; npm run lint; npm run build; Set-Location ..
Set-Location core; cargo fmt --all -- --check; cargo check --locked; cargo test --locked; Set-Location ..
scripts\build_app.bat
```

---

## Sequência de execução

| # | Etapa | Estado |
|---|---|---|
| 1 | Bump 1.2.4 em todos os manifestos | **feito** |
| 2 | Rebuild total limpo (rust → tauri → bundles) | **feito** |
| 3 | Modelos no bundle + verificação do `_resolver_modelos` | **feito** |
| 4 | Card de modelos com os 9 símbolos na UI | **feito** |
| 5 | Grep de vocabulário residual | **feito — 0** |
| 6 | Varredura de segurança (`.env`, segredos) | **feito — 0** |
| 7 | Relatório final 10/10 camada por camada | **este documento** |
| 8 | Lote 1–2: seletor de Ativo do card, CSS do Copiloto, Analytics unificado ao Histórico | **feito — 169 testes** |
| 9 | Lote 3–4: Sistema com cache/Atualizar, sub-abas do Robô, `.dense-grid` nos dois grids | **feito — 178 testes** |
| 10 | Lote 5: `…`, estados vazios, vocabulário de chip + guarda em `test_interface_surface.py` | **feito — 178 testes / 590 pytest** |
| 11 | Lote 6: gate final, `build_app.bat` (7 etapas), MSI instalado e app no ar | **feito — 2 bundles** |
| 12 | Rodada de UI: Calendário com dias em ordem + 4 sub-abas do Robô + ativo/período no automático + motor visível no Mini Terminal | **feito — 191 testes / 590 pytest** (gate verde, build **pende de aprovação**) |

---

## Pendências que exigem credencial ou conta (fora do código)

1. **Chaves da MEXC e da Binance** — os adaptadores já existem e já respeitam
   `XAU_ENABLE_MEXC_EXECUTION` / `XAU_ENABLE_BINANCE_EXECUTION`, mas param em
   `EXECUTION_NOT_IMPLEMENTED` porque o envio HTTP real ainda não foi escrito.
   Gravar as chaves num arquivo é proibido pelas regras operacionais; elas
   entram por variável de ambiente na máquina do operador.
2. **MT5 conta real** — `trade_mode` real é aceito (a recusa por tipo de conta
   foi removida), mas a validação ao vivo precisa de uma conta conectada.
3. ~~**Instalação do MSI 1.2.4 numa máquina**~~ — **concluído** em 2026-09-28
   14:35 (instalação silenciosa, log `Installation completed successfully`, app
   no ar). Ver item 8.
4. **Backtest, forward test e revisão de limites de risco** antes de qualquer
   execução com dinheiro real (`XAU_MCP_TRADING` segue `0`).
