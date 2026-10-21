# Ciclo 21/10/2026 — segurança zerada, validação 100% e manutenção verde

## Pedidos e destino

| # | Pedido | Feito |
|---|---|---|
| 1 | "Corrigir tudo: 34 alertas Dependabot, 2 CodeQL, CI e o problema de manutenção" | Alertas **34 → 0** em ambos os scanners; CI 100% verde em `main` e `develop`; issue #31 fechada |
| 2 | "Deploy 10/10 com testes e simulação real" | Suíte local inteira verde + gateway real exercitado em porta isolada; push em `develop` e `main`; workflows verdes |
| 3 | "Salvar conversas e documentos" | Este documento, `INDICE.md` e `STATUS_ATUAL.md` atualizados |

## Números (medidos, antes → depois)

| Medida | Antes | Depois |
|---|---|---|
| Alertas Dependabot abertos | 34 | **0** |
| Alertas Code Scanning abertos | 2 (#69, #70) | **0** |
| Deployments Vercel | 789 | **0** (GitHub App desinstalado pelo dono) |
| `pytest -q` | 1355 passed, 2 skipped | **1360 passed, 2 skipped** (+5 novos) |
| `vitest run` | 913 | **916 passed** (72 arquivos) |
| `tsc --noEmit` | 0 | **0** |
| `cargo fmt/check/test/clippy` | 0 | **0** |
| Backend `npm run lint` | sem job próprio | **exit 0** |
| Workflow `XAU AI PRO - validação universal` | ✗ em todo push | **✓** |
| `Manutencao Automatica Segura` | ✗ todo dia desde 15/10 | **✓** (run `39537706085`) |
| Preflight | — | **0 falhas**, 1 aviso (disco 4,35 GB) |

## O que estava quebrado — e como foi medido

### 1. Dependabot 34 → 0

Versões fixadas: `uv==0.13.4`, `aiohttp==3.14.5`, `certifi==2026.10.19`,
`follow-redirects@1.16.1`, `vite@8.3.4`, `Pillow==13.0.0`.

O `Pillow 13` só sobe se o `streamlit` sair: ele exige `pillow<13`. Dono escolheu
**remover o Streamlit do runtime**. O dashboard web já estava fora do EXE
(`launcher.spec`), então a remoção não tirou função de ninguém — o
`Python/launcher.py` já trata o import em `try/except` e degrada com aviso.

`pip check` limpo depois das trocas.

**Dependabot só fecha quando o fix chega na branch DEFAULT.** Foi por isso que
os números caíram 34 → 18 no push de `develop` e 18 → 0 depois do push em
`main`. Merge `develop → main` (`d076ba9`) resolveu o conflito de lockfile do
`uv` mantendo `0.13.4`.

### 2. CodeQL #69 e #70

- **#70** (linha 1133, `backend/fastapi_gateway.py`): o arquivo tinha **três
  definições** da mesma rota universal; só a primeira registrada respondia, e as
  outras duas referenciavam `connection_store`/`broker_registry`, que **não
  existem** naquele módulo. Eram código morto — 204 linhas removidas.
- **#69** (linha 522, `backend/auto_engine.py`): `MotorAuto.ligar()` devolvia
  `{exc}` cru no motivo, expondo detalhe interno. Agora o motivo nomeia o par e
  os mercados aceitos, lidos de `get_broker(self.broker).markets`.

Prova negativa em `tests/test_rotas_universais_e_motivo_seguro.py` (5 testes):
`test_motivo_nao_ecoa_excecao` reprova se o texto da exceção reaparecer e
`test_gateway_nao_registra_a_mesma_rota_duas_vezes` reprova rota duplicada.

### 3. `validação universal` vermelho em todo push

O job `quality` usava `super-linter`, que rodava sem `node_modules` (228 erros
ESLint "Can't resolve 'vitest/config'"), tinha flags inexistentes no v8
(`*_PRETTIER: false`) e gerava summary de 6 MB contra o limite de 1 MB.

Substituído pelas ferramentas **do projeto**: no backend `npm ci && npm run
lint`; no frontend `npm ci && npx tsc --noEmit && npm test`. Runner
`windows-latest` (as suítes usam caminhos e binários de Windows).

### 4. Manutenção vermelha desde 15/10 (issue #31)

Causa: `tests/test_ai_inference.py` reprovava em checkout **sem os modelos**
(`.pkl`/`.meta.json` são gitignored). O runner baixava o código, não achava
catálogo e falhava em 8 testes — o workflow entendia como defeito de manutenção
e abria/comentava issue todo dia.

Correção: os três grupos de teste pulam **com motivo medido** quando
`ai.MODELOS_DIR` não tem nenhum `*.meta.json`; com catálogo presente, rodam.
Prova negativa local: com catálogo, os mesmos testes passam.

## Simulação real do gateway (porta 9099, processo próprio)

Autenticado com token descartável; `XAU_MCP_TRADING=0` e rate limit desligado
para não mascarar resposta com 429:

| Chamada | Resultado |
|---|---|
| `/api/health` sem token | **401** (fail-closed) |
| `/api/health` com token | 200 |
| `/api/capabilities` | 200, `withdrawals_enabled=false`, `transfers_enabled=false` |
| `/api/ai/models` | 200, catálogo lido |
| `/api/universal/overview` | 200, conexão **mexc real** |
| `/api/universal/account` sem par | **422** (par obrigatório) |
| `/api/universal/account?broker=mt5&market=metals` | 503 sem corpo vazando stack |
| `/api/universal/order` com `request_id`+`account_id`, `execute=false` | `{"ok":true,"accepted":true,"stage":"validated"}` — sem efeito |
| `/api/trade/order` sem `confirm` | **403** |

Nenhuma ordem real foi enviada: `execute=true` exige `XAU_MCP_TRADING=1` e as
gates de corretora, fora da simulação por decisão do projeto.

## Commits (origin/develop e origin/main)

- `e69b3d2` — certifi 2026.10.19
- `d076ba9` — merge `main` ↔ `develop` (conflito uv → 0.13.4)
- `7f648d2` — workflow Rust roda dentro de `core/`
- `57f11dd` — Streamlit fora do runtime; Pillow 13.0.0
- `29243c9` — rotas universal mortas removidas, motivo sem exceção crua,
  `quality` com as ferramentas do projeto, +5 testes

Estado final dos workflows do `29243c9`:

| Workflow | `main` | `develop` |
|---|---|---|
| CI | ✓ | ✓ |
| Security Checks | ✓ | ✓ |
| Pylint | ✓ | ✓ |
| Rust | ✓ | — |
| Validacao e Empacotamento | ✓ | ✓ |
| XAU AI PRO - validação universal | ✓ | ✓ |
| CodeQL | ✓ | ✓ |
| Manutencao Automatica Segura | ✓ (dispatch) | ✓ (dispatch) |

## O que NÃO foi feito, e por quê

1. **Ordem real** — as gates (`XAU_ENABLE_*`, `XAU_MCP_TRADING`) estão
   desligadas; a simulação valida o caminho até `stage=validated`, que é o
   contrato do dry-run. Ligar gate é decisão do dono.
2. **MQL5** — nenhum `.mq5`/`.mqh` foi tocado neste ciclo, então não houve
   recompilação nem reanexo. A validação de MQL5 do preflight segue como aviso.
3. **Aviso de disco** — 4,35 GB livres; o build Android exige mais. Não é
   bloqueante para o build Windows.

## Notas de ferramenta (custaram tempo, ficam registradas)

- **`Set-Content -Encoding UTF8` no PowerShell 5.1 grava BOM.** Corrompeu
  `requirements-lock.txt` e o `pyproject.toml` numa edição; o sintoma foi
  "arquivo inválido" no install, não no conteúdo. Correção:
  `[System.IO.File]::WriteAllText($p, $t, New-Object System.Text.UTF8Encoding($false))`
  ou a ferramenta de edição do agente.
- **Trocar de branch atualiza mtime mas não conteúdo.** O teste de bundle
  reprovou comparando hash da ponte por **data**; a build foi refeita e o hash
  voltou a bater. Medir por hash, nunca por mtime.
- **Teste com seletor acentuado**: `Add-Content` do PowerShell corrompe não-ASCII
  (U+FFFD / 0x97) e o teste falha como se o componente estivesse quebrado. Já
  registrado no ciclo de 13/10; vale para qualquer append em doc/JSX.

## Aberto (ação do dono)

1. Ligar execução real quando quiser operar: `XAU_MCP_TRADING=1` + gate da
   corretora + `confirm=true`.
2. Reanexar o EA ao gráfico se for operar por ele (o `.ex5` do terminal é mais
   antigo que o do repo; `ea_deploy.py` existe mas não foi executado).
3. Liberar espaço em disco antes de build Android (4,35 GB livres).
