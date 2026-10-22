# STATUS ATUAL DO PROJETO

**Data:** 22/10/2026
**Versão:** 1.2.4
**Status:** baterias de simulação **fixadas por medição**, CI verde, **deploy
instalado e no ar**. Pendências são **ação do dono** (ver ABERTO).

---

## LEIA PRIMEIRO

**→ [`Docs/CONVERSA_20261022_BATERIAS_FIXADAS_CI_VERDE_E_DEPLOY.md`](CONVERSA_20261022_BATERIAS_FIXADAS_CI_VERDE_E_DEPLOY.md)**

Diz o que mudou, o que foi medido e o que ficou aberto. Este arquivo é o resumo.

---

## OS NÚMEROS (medidos em 22/10/2026)

| | |
|---|---|
| `pytest -q` | **1482 passed, 2 skipped** (262,55 s) |
| `scripts/medir_artefato_gateway.py` | **exit 0** — o `.exe` instalável medido de verdade |
| `vitest run` | **916 passed** (72 arquivos) |
| `tsc --noEmit` | **exit 0** |
| backend `npm run lint` | **exit 0** |
| `pytest -q tests/test_mql5_compila.py` | **2 passed** (MetaEditor invocado) |
| Workflows do push em `main` | **8/8 verdes** (`ad45e74`) |
| preflight `--etapa app-rodando` | **exit 0** (1 aviso: disco 5,95 GB) |
| `validar_prontidao_real.py` | **5/6** — só `credencial de conta real` |
| branch | `develop` = `main` = `8e24ad4` |
| arquivos pendentes no git | **0** |
| app no ar | app 1764 · gateway 9011 · core 9002/9003 |
| ponte/core instalados vs build | **IGUAIS por hash** |

Os 2 `skip` restantes são `PAINEL` vazio em `test_nomes_de_campo_entre_paredes`
— decisão do dono de 08/10/2026, com dois testes explícitos dizendo o estado
medido. Não mascaram erro.

---

## O QUE FOI FEITO NO CICLO DE 22/10

| item | antes | agora |
|---|---|---|
| Baterias de simulação | só passavam onde existia `.env` (CI Linux via 200/404 onde esperava 401) | **fixture própria**: token, rate limit e dublô de terminal fixados |
| Lista de rotas nos testes | escrita a mao, com 5 rotas que não existem | **lida do FastAPI app** + testes contra lista vazia |
| Dublô de `MetaTrader5` | vazio → `AttributeError` → **500** em `/api/assets` | `tests/_dublo_mt5.py` devolve `None` (terminal sem sessão, o estado real) |
| MCP de trading | porta 9001 enquanto o gateway está em 9011 → `gateway inacessivel` | **segue `XAU_GATEWAY_PORT`**; prova viva: **401 fail-closed** |
| Artefato congelado | só o fonte era medido; o `.exe` já saiu do ar com entry point errado | **bateria do `.exe`** (fail-closed, saque/transferência `False`, `gateway_build`, dry-run) |
| CI em `main` | `ci` ✗ e `Validacao e Empacotamento` ✗ | **8/8 ✓** |
| Deploy | ponte e core antigos (core divergia por 1.024 bytes) | instalado por NSIS e **conferido por hash** |
| Disco | 1,34 GB (preflight reprovava) | **5,95 GB** |

---

## ABERTO (ação do dono, não do ciclo)

1. **Credencial de conta real**: quando existir, `XAU_ACCOUNT_KIND=real`.
   Hoje a conta é `MetaQuotes-DEMO` e o script de prontidão reprova nesse item.
2. **MCP de trading e o token de sessão**: porta corrigida, mas o gateway usa
   token aleatório por execução (`main.rs:715`) e o token do `.env` devolve
   **401** (fail-closed correto). Expor o token ao MCP degrada a segurança —
   decisão do dono.
3. **Backup da instalação anterior**: `Temp\instalacao_anterior_20261022`
   (949 MB). Apagar depois de confirmar o app novo no ar?
4. **EA no gráfico**: se for operar por EA, reanexar — `.mq5` não foi tocado
   neste ciclo, então não houve recompilação.
5. **Fechamento espontâneo do app** em sessão longa: medido em 10/10, sem log.

---

**Um documento antigo neste `Docs/` não está desatualizado por estar no fim da
lista — e sim por ser de um ciclo anterior. O `command` vence o número; o
documento mais recente manda.** Ver
`CONVERSA_20261022_BATERIAS_FIXADAS_CI_VERDE_E_DEPLOY.md`.
