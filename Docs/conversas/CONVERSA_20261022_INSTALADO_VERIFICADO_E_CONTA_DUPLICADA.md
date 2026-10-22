# Ciclo 22/10/2026 (noite) — instalado verificado, conta duplicada e deploy

## Pedido

Executar o app instalado, testar a conta DEMO varias vezes, rodar as baterias
de simulacao real, descobrir e validar tudo, commitar, push e deploy.

## Numeros medidos (antes → depois)

| Medida | Antes | Depois |
|---|---|---|
| Arquivos da ponte instalada | **87** (de 5.211 do build) | **5.211** |
| Hash da ponte instalada | `62E5B00E…` (build antigo) | `6000ADA0…` = build |
| Hash do core instalado | `C2ED35AB…` (build antigo) | `9D796360…` = build |
| `Docs/version.json` no pacote | **ausente** | presente |
| Gateway instalado ao subir | **exit 1** (`FileNotFoundError`) | pronto antes do Core |
| Linhas MT5 no overview | **3 conectadas** (XMGlobal mostrando conta da MetaQuotes) | **2 conectadas** (XMGlobal `offline`) |
| `pytest -q tests` | 1.497 passed | **1.499 passed, 2 skipped** (201,62 s) |
| Baterias de simulacao (3 arquivos) | — | **74 passed × 3 rodadas** |
| Conta DEMO via gateway | — | **5 rodadas**, login `113568614` `MetaQuotes-Demo` |
| `vitest run` | 921 | **921 passed** (72 arquivos) |
| `tsc --noEmit` / backend lint | 0 | **0 / 0** |
| `cargo test --locked` | — | **38 passed** |
| `test_mql5_compila.py` | — | **2 passed** |
| `medir_artefato_gateway.py` (dist e instalado) | — | **exit 0** nos dois |
| `preflight --etapa app-rodando` | 3 portas livres | **exit 0** |
| `validar_prontidao_real.py` | — | **5/6** (so credencial real) |
| App no ar | — | app 7048/12824 · gateway `11776`/`4456` (9011) · core 9002/9003 |

## Defeito 1 — a ponte instalada tinha 87 dos 5.211 arquivos

O app abria, mas nao subia gateway nem core. O log dizia:

```
bridge MT5 criado (pid 12664) com ordens reais DESLIGADAS
bridge MT5 nao respondeu com identidade esperada
```

Medido no `.exe` instalado, executado no terminal:

```
FileNotFoundError: ...\_internal\setuptools\_vendor\jaraco\text\Lorem ipsum.txt
[PYI-12372:ERROR] Failed to execute script 'pyi_rth_pkgres'
```

O `.exe` instalado era do build anterior (`62E5B00E…`) e o `_internal` tinha
sido parcialmente atualizado (15:29) — a pasta instalada ficou com **87**
arquivos, contra **5.211** do build (`6000ADA0…`). Reinstalar por cima, com a
mesma versao 1.2.4, deixa esse estado misto (AGENTS §7: o NSIS nao sobrescreve
arquivo de mesma versao).

**Correcao medida:** remover `bridge`, `core` e `XAU AI PRO.exe` antes de
instalar; instalador `/S` exit 0; ponte e core conferidos por **hash igual**;
`version.json` e `Lorem ipsum.txt` presentes; log do app:
`bridge MT5 autenticado e pronto antes do Core` / `core autenticado`.

**Guarda reutilizavel (sem codigo novo):**

```powershell
.\.venv\Scripts\python.exe scripts\medir_artefato_gateway.py --exe "$env:LOCALAPPDATA\XAU AI PRO\bridge\mt5-gateway.exe"
```

Sem isso, o defeito e invisivel: o teste de artefato media so `dist/`.

## Defeito 2 — duas conexoes MT5, uma delas mostrando a conta da outra

O store tinha `... @ XMGlobal-MT5 14` e `... @ MetaQuotes-Demo` ativas. O
overview mostrava as **duas** como `conectada`, com o **mesmo** login
`113568614` (`MetaQuotes-Demo`):

```
mt5:forex:Henrique Carvalho @ XMGlobal-MT5 14   | conectada | 113568614 MetaQuotes-Demo
mt5:forex:Henrique Carvalho @ MetaQuotes-Demo   | conectada | 113568614 MetaQuotes-Demo
```

A sessao MT5 e **uma**. `_universal_overview` usava `_payload()` para toda
conexao `mt5`, ignorando o `id`. Correcao: a conexao cujo `id` nao termina em
`"<name> @ <server>"` da sessao atual vira `offline`, com motivo
`conta nao e a sessao atual do terminal`, e **sem** account. Prova negativa:
`connected == 1` no teste e `connected == 2` (MEXC + a conta real) ao vivo.

## Baterias executadas

- `tests/test_simulation_real_full.py`, `tests/test_simulacao_ciclo_vida_real.py`,
  `tests/test_simulation_load.py`: **74 passed** em cada uma das **3** rodadas.
- Harness ao vivo (gateway fonte, porta efemera, MT5 DEMO): **5 rodadas** com
  conta, posicoes, overview, quote/quotes, simbolos, 401 sem token, 401 com
  token errado e ordem `execute=false` em `stage=validated`.
- Conta medida: `113568614` / `MetaQuotes-Demo`, saldo ~10.007 USD, 12.270
  simbolos, XAUUSD bid/ask lidos, `withdrawals/transfers = False`.

## Nota operacional medida

Com o `terminal64.exe` fechado, o gateway **nao abre** o terminal (por
desenho) e toda leitura MT5 volta indisponivel. Medido: `mt5.initialize()`
direto abre o terminal, mas `_ensure_mt5` recusa quando nao ha sessao — e
fail-closed correto. Para testar a conta DEMO, o terminal precisa estar aberto
antes.

## O que falta (acao do dono)

1. **Credencial de conta real** — `XAU_ACCOUNT_KIND=real` so quando existir.
   A prontidao segue **5/6** e diz "nao operar com dinheiro real".
2. **Conexao XMGlobal antiga** continua gravada como ativa. Hoje ela aparece
   `offline`; remover a conexao e decisao do dono (dado dele).
3. **Token de sessao e o MCP**: o gateway recusa o token do `.env` com 401
   (fail-closed). O harness usa um gateway proprio com token conhecido.
4. **Disco**: apos o build e a instalacao o preflight passa com 5,34 GB; o
   cache `Temp\cargo-target\release\deps` pode voltar a crescer.
