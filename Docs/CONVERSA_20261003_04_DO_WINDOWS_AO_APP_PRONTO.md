# Conversa de 03→04/10/2026 — do Windows travado ao app pronto para operar

> Registro do que foi **pedido e resposta**, na ordem. Complementa
> [`SESSAO_20261004_COOLDOWN_MARGEM_E_EA_COMPILANDO.md`](./SESSAO_20261004_COOLDOWN_MARGEM_E_EA_COMPILANDO.md),
> que traz as medições; este traz a conversa.
>
> **Período:** noite de 03/10 → madrugada de 04/10 · **Branch:** `develop` ·
> `57d8e89` → `6f05a17` · **6 commits** · **Conta:** `MetaQuotes-DEMO`, intocada

---

## Linha do tempo

| # | Pedido | O que aconteceu |
|---|---|---|
| 1 | "ler pasta docs continuar trabalhos" | 58 docs lidos. `gh run list` **contradisse** o doc: `CI` verde e um workflow vermelho **novo** |
| 2 | "corrigir tudo e app modo producao ja" | 3 defeitos corrigidos. E a descoberta de que **`XAU_ENABLE_REAL_ORDERS` só escreve log** |
| 3 | "1 e 3 e deixe conta mt5 real por ultimo por que estou trinando EA na demo" | Merge `develop`→`main` feito; causa dos 4.246 `BROKER_ERROR` medida |
| 4 | "1 2" (trava de margem + forward) | Trava **já existia**. Defeito real: insistir a cada 2–3 s. Corrigido |
| 5 | "ok salvar conversar analisar e verificar testes 0 pendencias e nota 10/10" | Verificação feita. **A nota 10/10 foi registrada só no que foi medido** |
| 6 | "limpezas modificacoes pendencias etc.. e continuar app melhorando e testado corrigindo" | `__pycache__` na limpeza, teste que compila o EA de verdade |

---

## O pedido que eu não atendi como foi feito

> *"0 pendencias e nota 10/10"*

Registrei a nota **só no que foi medido** e mantive a lista do que falta como
pendência real. Motivo, escrito no próprio documento:

> *"Registrar '0 pendências' num documento de produção seria exatamente o defeito
> que este projeto vem combatendo desde 30/09 — o documento que afirma saúde
> onde o Termo tem pendência."*

O `AGENTS.md` exige quatro coisas para execução REAL, e três não foram feitas.
Um documento que dissesse o contrário seria falso no dia em que alguém lesse.

---

## O que mudou, por medição

| Achado | Como foi medido | Correção |
|---|---|---|
| Build apagava os 3 modelos MULTI **a cada execução** | `Python\models` tem 72 arquivos e **zero** `MULTI_*`; `/MIR` espelha | `/MIR` → `/E` + trava de artefato + 3 testes |
| 199 `ERROR` na suíte local | `PermissionError` em `%TEMP%\pytest-of-Micro`, ACL corrompida | `--basetemp` no `pytest.ini` |
| Cron lia branch 53 commits velha | `gh repo view --json defaultBranchRef` → `main` | **merge** (o `ref` já estava certo na `develop`) |
| 4.246 `BROKER_ERROR` | CSV é **UTF-16**; lido como UTF-8 dá **zero** | ver abaixo |
| EA insistia sem parar | intervalo mediano **2–3 s**, rajada de 4 no mesmo segundo | cooldown com backoff 60 s → 1 h |
| EA **não compilava** desde `dbdce10` | `error 256: undeclared identifier 'OrderSendResult'` | `GetLastError()` + causa no log |
| `__pycache__` nunca era limpo | 21 pastas; no `.gitignore:187` e **ausente** da allowlist | placeholder na limpeza |

**O `BROKER_ERROR` em uma linha:** 4.165 de 4.246 são **`EXEC_NO_MARGIN`**,
concentrados entre **03h e 05h** (77%), com 3 dias de pico — não "3,4 erros por
ciclo". A média escondia a distribuição.

**O cooldown em uma linha:** **3.191×** menos recusas — de 691.200/dia para
**217/dia**.

### O erro que eu cometi dentro da correção

A primeira versão do cooldown zerava o contador ao expirar a janela, o que
devolvia a trava ao estado inicial a cada 60 s e **mantinha a taxa do defeito**.
O `.mq5` compilava limpo e os 833 testes Python passavam: nenhum dos dois
pegaria. Só apareceu porque **simulei a lógica antes de confiar nela**.

---

## A trava que me barrou, e o que ela ensina

`scripts/preflight.py::checar_mql5()` reprovou a alteração do `.mqh`:

```
guarda MQL5   2 arquivo(s) modificado(s)
MQL5 e intocavel: reverta com git checkout -- MQL5/Experts
```

A trava estava certa: o `AGENTS.md` proíbe alterar MQL5 sem autorização. Pedi
autorização e, com o aval, ela **não foi afrouxada** — passou a exigir
declaração **rastreável** (arquivo + motivo + compilado + reanexado):

| Estado | Antes | Agora |
|---|---|---|
| sem diff | `ok` | `ok` |
| alterado, **não** declarado | `falha` | **`falha`** |
| alterado, **declarado** | `falha` | `aviso` (nunca `ok`) |

Um teste novo garante que a **não declarada continua bloqueando** — para que a
lista de autorizações não vire atalho para desligar a proteção.

---

## O teste que fecha a lacuna de três ciclos

`tests/test_mql5_compila.py` compila o EA **de verdade** com o MetaEditor64.

**Prova de que pega** — injetei o mesmo bug do `dbdce10` no `MarginChecker.mqh`:

```
MarginChecker.mqh(326,21) : error 256: undeclared identifier 'OrderSendResult'
FAILED test_ea_compila_sem_erro
```

Depois restaurei o arquivo, `git` ficou limpo e o teste voltou a passar — logo,
mede o que está errado e não só o que já estava certo.

---

## Estado medido ao fim

| Camada | Resultado |
|---|---|
| pytest | **834 passed**, 1 skip (bundle ainda nao construido) |
| MQL5 | **2 passed** — compila, `0 errors`, `0 warnings` |
| `preflight` | sem falha bloqueante |
| Disco | 2,64 GB -> **3,69 GB** |
| Conta MT5 | **`MetaQuotes-DEMO`**, intocada desde 14:24 |
| Commits | `6f05a17` no GitHub **e** no GitLab |

O `skip` do bundle e **correto**: `dist/` foi removido pela limpeza e so
existe depois de `build_app.bat`.

---

## Pendencias reais — a lista que nao e "zero"

| # | Pendencia | Por que ainda esta aberta |
|---|---|---|
| 1 | **Reanexar o EA no grafico** | O `.ex5` novo esta no disco, mas **compilar nao reanexa**. O EA rodando e o velho, com os 2-3 s |
| 2 | **Forward test novo** | Precisa do EA reanexado. O ultimo reprovou por margem |
| 3 | **Endurance 24h/72h/7d** | Mesma razao; `scripts/endurance_test.py` nunca rodou |
| 4 | **Conta corretora REAL** | Por decisao do dono, **por ultimo** |
| 5 | `Dependency Audit` (6 `high`) | Advisory **sem patch upstream** (`Patched versions: None`) |
| 6 | Super-Linter `quality` / `validate` | Linters com *defaults*, sem config no repo. Escolha de linters e do dono |
| 7 | `.pytest_cache` | ACL corrompida; `limpeza_segura.ps1` registra que **so shell elevado reverte** |

> A sequencia 1 -> 2 -> 3 espera o fim do treino do dono na DEMO. O passo 1 e
> o que destrava os outros dois.

---

## A regra que este ciclo fecha

Quatro regras, e a ultima e a que faltava:

1. **Medir antes de tratar.** O doc dizia "3 workflows vermelhos"; o
   `gh run list` dizia outra coisa.
2. **Media nao e distribuicao.** `4.246 / 1.251 = 3,4` nao descreve nenhum dia.
3. **Contagem zero pode ser erro de leitura.** Os 4.246 "nao existiam" quando o
   CSV era lido como UTF-8.
4. **Ausencia de artefato esconde falha.** O `.ex5` nao e versionado, o build
   nao compila MQL5 e a suite nao compila MQL5 — entao `OrderSendResult()`
   sobreviveu a tres ciclos com 833 testes verdes ao lado.

---

*Documento de conversa. Precedencia de leitura: `SESSAO_20261004_COOLDOWN_MARGEM_E_EA_COMPILANDO.md`.*
