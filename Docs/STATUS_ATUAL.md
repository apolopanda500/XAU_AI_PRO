# STATUS ATUAL DO PROJETO

**Data:** 21/10/2026
**Versão:** 1.2.4
**Status:** segurança zerada e validação **100%** — CI, CodeQL, Dependabot,
manutenção e simulação real do gateway verdes. Pendências são **ação do dono**
(ver ABERTO).

---

## LEIA PRIMEIRO

**→ [`Docs/CONVERSA_20261021_SEGURANCA_ZERADA_VALIDACAO_100.md`](CONVERSA_20261021_SEGURANCA_ZERADA_VALIDACAO_100.md)**

Diz o que mudou, o que foi medido e o que ficou aberto. Este arquivo é o resumo.

---

## OS NÚMEROS (medidos em 21/10/2026)

| | |
|---|---|
| alertas Dependabot abertos | **0** (eram 34) |
| alertas Code Scanning abertos | **0** (eram 2: #69/#70) |
| deployments Vercel | **0** |
| `pytest -q` | **1360 passed, 2 skipped** |
| `vitest run` | **916 passed** (72 arquivos) |
| `tsc --noEmit` | **exit 0** |
| `cargo fmt/check/test/clippy --locked` | **exit 0** |
| backend `npm run lint` | **exit 0** |
| build do frontend | **ok** |
| preflight | **0 falhas**, 1 aviso (disco 4,35 GB) |
| branch | `develop` = `main` = `29243c9` |
| arquivos pendentes no git | **0** |

Workflows do `29243c9`: CI, Security, Pylint, Rust, Validação, `XAU AI PRO -
validação universal` e CodeQL **verdes** em `main`; os mesmos (menos Rust, que
só roda em `main`) **verdes** em `develop`. `Manutencao Automatica Segura`
verde no run `39537706085`; issue #31 fechada.

---

## O QUE FOI FEITO NO CICLO DE 21/10

| item | antes | agora |
|---|---|---|
| Dependabot | 34 alertas | **0** (`uv`, `aiohttp`, `certifi`, `vite`, `follow-redirects`, `Pillow 13`) |
| Streamlit no runtime | exigia `pillow<13` | **removido** (dashboard web já estava fora do EXE; launcher degrada com aviso) |
| CodeQL #70 | rota universal duplicada com `connection_store` inexistente | **204 linhas mortas removidas** |
| CodeQL #69 | motivo ecoava `{exc}` | motivo nomeia o par e os mercados aceitos |
| `validação universal` | ✗ em todo push (Super-Linter sem `node_modules`) | **✓** com ESLint/tsc/vitest do projeto |
| Manutenção | ✗ diária desde 15/10 | **✓**; testes de catálogo pulam com motivo sem modelos |

---

## SIMULAÇÃO REAL (porta 9099)

Sem token → **401**; health/capabilities/models/overview → **200**;
`withdrawals_enabled=false`, `transfers_enabled=false`; `universal/account` sem
par → **422**; `mt5/metals` → 503 sem vazar stack; ordem `execute=false` →
`accepted/validated` **sem efeito**; `trade/order` sem `confirm` → **403**.

---

## O QUE ESTÁ ABERTO (ação do dono, não do ciclo)

1. **Operar de verdade**: ligar `XAU_MCP_TRADING=1`, a gate da corretora e
   enviar com `confirm=true`. Nada foi enviado neste ciclo.
2. **Reanexar o EA ao gráfico** se for operar por ele: o `.ex5` do terminal é
   mais antigo que o do repo; `backend/ea_deploy.py` existe mas não foi
   executado (exige `XAU_ALLOW_EA_DEPLOY=1`).
3. **Disco**: 4,35 GB livres; build Android exige mais espaço.
4. **Fechamento espontâneo do app** em sessão longa: medido em 10/10, sem log
   nem stack; se repetir, rodar com o console aberto.

---

**Um documento antigo neste `Docs/` não está desatualizado por estar no fim da
lista — e sim por ser de um ciclo anterior. O `command` vence o número; o
documento mais recente manda.** Ver
`CONVERSA_20261021_SEGURANCA_ZERADA_VALIDACAO_100.md`.
