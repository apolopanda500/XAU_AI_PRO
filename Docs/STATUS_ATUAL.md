# STATUS ATUAL DO PROJETO

**Data:** 07/10/2026
**Versão:** 1.2.4
**Status:** código validado (pytest 1271 · vitest 731 · tsc limpo) — **aguardando build**

---

## LEIA PRIMEIRO

**→ [`Docs/PASSAGEM_20261007_PRIMEIROS_PASSOS.md`](PASSAGEM_20261007_PRIMEIROS_PASSOS.md)**

Esse arquivo diz o que fazer, o que medir e o que está aberto. Este aqui é o
resumo.

---

## OS NÚMEROS

| | |
|---|---|
| `pytest` | **1271 verdes** |
| `vitest` | **731 verdes**, 51 arquivos |
| `tsc --noEmit` | **limpo** |
| `git status` | **0 pendentes** |
| `preflight --etapa app-rodando` | 2 avisos, **nenhuma falha bloqueante** |

## COMMITS DESTA SESSÃO

```
dc484d7  ouro: o nome da corretora e o nome do modelo agora se encontram
c352d14  docs: a conta fecha, e o erro foi meu de metodo — nao dinheiro faltando
ed2c125  grafico e ticket: o que o app instalado mostrou e o CSS que mentia o motivo
c578f10  docs: o instalador novo medido, e o motor que perdeu 2,94 na conta
96a684e  margem: o requisito que o painel recusou por engano, e a alavancagem da conta
48754ed  grafico: as pontas, a paleta, a trava e o Ctrl+Z; historico: a tela para de descartar a busca
```

## O QUE FOI CORRIGIDO NESTA SESSÃO

| item | antes | agora |
|---|---|---|
| `PriceChart.tsx` **zerado** (19.157 bytes de `0x00`) | `tsc` despejava milhares de erro | restaurado do **source map** do `dist` |
| `.git/index` **zerado** | `git status` recusava com `bad signature` | reconstruído com `git read-tree` |
| Gráfico vazio (`Identidade de mercado inválida`) | não carregava com o motor desligado | mercado da ficha + período do modelo |
| Campo SL espremido a ~10 px | rótulo em coluna de 1 caractere | `minmax(280px, …)` no grid |
| Histórico descartava a busca ao trocar o filtro | filtro novo com dados do filtro antigo | token de requisição |
| Histórico não dizia quando o MT5 está fechado | "Nenhum registro no período" | "Sem leitura: o MetaTrader 5 está sem sessão" |
| Requisito de margem ausente | recusado como "número inventado" | `0,85 USD`, conferido com a conta |
| Ouro não abria | `GOLD` na corretora ≠ `XAUUSD` no modelo | `model_symbol` casa os dois |
| Pontas, paleta, trava, `Ctrl + Z` | 19 testes reprovando | **0** |

## O PRÓXIMO PASSO

**Build.** O app instalado é **anterior a quatro correções** — testar agora
mostra o gráfico vazio. `build_app.bat`, ~8 min. Os passos estão em
`PASSAGEM_20261007_PRIMEIROS_PASSOS.md` §3.

## O QUE ESTÁ ABERTO

1. **A conta real opera com o app desligado** — 8 posições, 4 perdas de ~1,50,
   todas `[sl …]`, stop de 0,23% a 1000:1. Não é do app: é o EA do MT5, que
   roda fora dele.
2. **Forward e endurance rodaram em código de 23/09**, não no de hoje
   (endurance: 923 operações, PF 0,48, Sharpe −9,31).
3. **Indicadores com busca** — `rsi` → 3 resultados, como a XM.

## A RECONCILIAÇÃO DO SALDO FECHA

```
soma dos 19 deals   = +9,56
balance             =  3,94
credit              =  5,62
balance + credit    =  9,56   ← bate
```

Movimentações negativas: **nenhuma**. `Retirada: 0,00` no MT5.

---

**Um documento antigo neste `Docs/` não está desatualizado por estar no fim da
lista — e sim por ser de um ciclo anterior. O `command` vence o número; o
documento mais recente manda.** Ver `PASSAGEM_20261007_PRIMEIROS_PASSOS.md` §9.