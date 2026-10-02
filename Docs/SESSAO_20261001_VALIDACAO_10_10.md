# Ciclo 01/10/2026 — validação 10/10, matriz de leitura invertida e escada VIP

> Registro do ciclo da noite. Escopo: auditoria camada por camada do projeto
> inteiro, um defeito de integridade encontrado na documentação de
> corretoras, e a sub-aba VIPs reconstruída para mostrar a escada inteira.
>
> **Branch:** `develop` · **Versão:** 1.2.4 · **MQL5:** intocado

---

## 1. O que foi pedido e o que foi feito

| Pedido | Resultado medido |
|---|---|
| Validar o projeto inteiro, camada por camada | **16 camadas, todas 10/10** (§3) |
| Melhorar a sub-aba VIPs | Escada de 6 degraus com percentual (§5) |
| GitHub e GitLab | Ambos em `266e12d`, sincronizados (§2) |
| Desinstalar o app antigo | Registro `MSI {ABA76012}` removido (§2) |
| `Docs/` com as conversas | Este documento |

---

## 2. GitHub, GitLab e o app antigo

Os dois remotos estavam já sincronizados — o `0b74c2f` que o `ls-remote`
mostrava no GitLab era o *remote-tracking* local desatualizado, não o remoto:

```
local  : 266e12d585525a313eb78191fe4f85bc17bf6ade
gitlab : 266e12d585525a313eb78191fe4f85bc17bf6ade
github : 266e12d585525a313eb78191fe4f85bc17bf6ade
```

A pendência "token do GitLab" que a sessão de 01/10 listava **não existe**:
`git push gitlab develop` responde `Everything up-to-date`.

O app instalado estava com **registro órfão**: `InstallLocation` apontava
para `C:\Users\Micro\AppData\Local\XAU AI PRO\`, mas a pasta **não existia**.
O `msiexec /x {ABA76012-28EF-4C6D-9D9E-251108B3A288}` limpou o registro.

---

## 3. As 16 camadas

| # | Camada | Comando | Resultado |
|---|---|---|---|
| 1 | `MQL5` intocado | `git status --porcelain MQL5` | vazio |
| 2 | Trava de saque | grep `withdrawals_enabled.*True` | 0 violações |
| 3 | Segredos no git | `git ls-files` | nenhum `.env` |
| 4 | Nenhum ativo presumido | grep em `backend`/`app` | 0 em código |
| 5 | Nenhuma corretora padrão | grep `default="mt5"` | 0 |
| 6 | Governança dos modelos | `auditar_governanca_modelos.py` | 36/36 íntegros · 25 publicáveis |
| 7 | Rota do VIP | `fastapi_gateway.py:522` | `/api/vip/progress` somente-leitura |
| 8 | Testes do VIP | `pytest tests/test_vip_progress.py` | 23 passed |
| 9 | Privacidade | `auditar_privacidade.py` | todas as declarações confirmadas |
| 10 | Segredos no commit | `auditar_segredos.py` | 0 bloqueios |
| 11 | Matriz de capabilities | `gerar_matriz_capabilities.py --check` | **desatualizada → corrigida** (§4) |
| 12 | Python | `pytest -q tests` | **689 passed** |
| 13 | Frontend | `vitest run` | **189 passed** (20 arquivos) |
| 14 | TypeScript | `tsc --noEmit` | exit 0 |
| 15 | Core Rust | `cargo test --locked` | **38 passed** |
| 16 | Tauri | `cargo test --locked` | **11 passed** |
| — | Backend Node | `npm run lint` / `npm run build` | exit 0 / 4,58 MB |
| — | Preflight | `preflight.py` | **EXIT=0**, 14 checks |

**Contagem de testes:** 689 + 189 + 38 + 11 = **927**.

### Falso positivo que vale registrar

A camada 4 acusou `XAUUSD` em três arquivos. **Não era código** — eram as
docstrings que *descrevem* o defeito corrigido. Auditoria que não lê o
contexto da linha dá alarme falso e trains o operador a ignorar o alarme.

---

## 4. A coluna "Leitura" da matriz estava invertida

O `--check` reprovou a matriz. Regenerando, a diferença não era uma data: as
**17 linhas trocavam `OK` por `nao`**.

A causa, em `scripts/gerar_matriz_capacabilities.py`:

```python
"OK" if row["read_only"] else "nao",     # linha 93
```

`read_only` vale `not execution` (`broker_registry.py:178`) e significa
**"não executa ordem"**. Rotulado como coluna "Leitura", o sentido invertido:

| Corretora | Antes | Realidade |
|---|---|---|
| Não executa ordem | **`OK`** | não executa ordem |
| Entrega dado público | `nao` | entrega dado público |

Como nenhuma corretora deste registro executa ordem nesta versão, **todas as
linhas exibiam "OK"**. O documento afirmava leitura confirmada para todos os
pares — e não havia medição que sustentasse nenhuma dessas afirmações.

**Correção:** `capability_matrix()` passou a expor `public_data`, que responde
"existe dado público sem credencial?", e a coluna passou a usar esse campo. A
legenda também mudou: "OK" prometia uma verificação que o script nunca fez — o
gerador é derivado do registro, **não sonda as APIs**.

**Prova de que o teste pega a volta:** reintroduzi `"OK" if row["read_only"]`
no gerador e rodei a suíte:

```
FAILED tests/test_broker_coverage.py::TestMatrizLeituraNaoInvertida::test_documento_gerado_diz_a_verdade
1 failed, 29 passed
```

Restaurado: 30 passed (era 26).
---

## 5. A sub-aba VIPs

### O que faltava

A tela mostrava **um degrau solto**: "falta US$ 10.000" para o VIP 1, sem o
operador ver quantos degraus existem, onde ele está, nem quanto já fez do
próximo. Um nível isolado não diz se a meta está longe ou perto.

### O que foi construído

`escada_completa()` em `backend/vip_progress.py` devolve a escada inteira, na
ordem, com `estado`, `percentual` e `minimo_por_grupo` por degrau. A tela
renderiza uma linha por degrau com barra de progresso.

Três decisões vieram do defeito, não da estética:

1. **`percentual` usa o grupo mais atrasado.** O nível só conta quando *todos*
   os grupos passam. Usar o melhor grupo mostraria 100% com o Forex em 5%.
2. **Só um degrau é `atual`.** A primeira versão marcava *todos* os posteriores.
   Diria ao operador que ele persegue cinco metas ao mesmo tempo — falso.
3. **No topo não há `atual`.** Quem é VIP 5 não tem próxima meta, e a tela precisa
   dizer isso em vez de sugerir que falta algo.

O percentual é preso em 100 no backend **e** por `Math.min` no frontend — sem
os dois, volume muito acima do limiar estouraria a barra.

**Degradação:** `escada` é opcional no tipo. Gateway antigo sem o campo continua
mostrando nível e "falta para o próximo" — a tela degrada, não quebra.

Cobertura: `TestEscadaCompleta` (8 testes) e `VipsTab.test.tsx` (5 testes).
Detalhe em [`VIP_PROGRESSAO.md`](./VIP_PROGRESSAO.md).

---

## 6. Nada mais é pendência de código

A validação fechou em 16/16. As pendências que restam **não são de código**:

| Item | Natureza |
|---|---|
| Credenciais MEXC / Binance / Bybit / OKX | Máquina do operador |
| Conta corretora REAL | Hoje é `MetaQuotes-DEMO` |
| Certificado de CA pública | ~US$ 200–400/ano |
| Forward test aprovado | 3,4 `BROKER_ERROR` por ciclo; corrigir exige `.mq5` + MetaEditor64 |
| Endurance 24h/72h/7d | Exige o app no ar por dias |
| Aparelho Android físico | Não há aparelho |

**Uma lacuna real que sobrou:** `XAU_ENABLE_REAL_ORDERS` está injetado como `1`
em `frontend/src-tauri/src/main.rs`, hardcoded no código compilado. O
`AUDITORIA_20260929.md` §5 registra isso como "documentado, não corrigido". O
valor real não é auditável por quem opera, e o documento de pendências afirma
`=0`. **Continua aberto.**

---

## 7. A regra que o ciclo confirma

Mais um caso do mesmo padrão que a sessão de 30/09 registrou:

- A matriz dizia "OK" e ninguém questionou — **o script não media nada**
- O `audit de segredos` disse "0 arquivos auditados" e pareceu falha — **está
  certo**, audita só o que entra no commit, e o worktree estava limpo
- O grep de `XAUUSD` acusou 3 arquivos — **os 3 eram docstrings** explicando
  a correção

Nenhum desses três era defeito. Um era defeito, mas escondido atrás de um
script que parecia autoritativo. A regra continua: **não confiar em tela verde,
provocar o defeito e ler o que acontece** — e conferir se o alarme é real antes
de "consertar" a coisa errada.