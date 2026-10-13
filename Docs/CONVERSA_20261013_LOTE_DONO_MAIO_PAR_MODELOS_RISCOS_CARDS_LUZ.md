# Ciclo 13/10/2026 — lote do dono: mouse livre, pares via modelos, IA sugere riscos, cards, luz legível

Resposta ao lote do dono (fuso cortado, seletor com "NENHUM PAR", IA sugere
riscos, cards por modelo, claro sem letras, tabela/Controle, espaço vazio,
utilidade das ferramentas).

## O que foi feito (medido)

| # | Item | Prova |
|---|---|---|
| 1 | Mouse livre no gráfico e no indicador | `CrosshairMode.Normal` em `PriceChart.tsx` + `GraficoIndicador.tsx`; trava no duble (`CrosshairMode` medido) |
| 2 | Fuso abre para cima sem espaço abaixo | `paraCima` em `SeletorFuso.tsx` + `fuso.css`; 61 testes RobotTabs+Fuso |
| 3 | Pares vindos dos MODELOS (nada fixo) | `SeletorModelo.tsx` lê `/api/ai/modelos`, placeholder sem troca automática; sem conta salva = vazio + recusa |
| 4 | IA sugere riscos, operador aplica | `sugerir_limites` (`auto_engine.py`) + `POST /api/auto/sugerir-limites` + botão no `OperacaoAutomatica`; 79 testes Python |
| 5 | Um card por modelo (capa + mini + estado) | `ListaModelos.tsx` + `ModelCover.tsx` (nome = `label ?? id`) + `robo.css`; 16 testes |
| 6 | Claro legível | Sobreposição `[data-theme='light']` (chip.neutral, strategy-rule-grid, ajuda do histórico); `light_legivel.test.ts` |
| 7 | Dubles espelham `LIMITE_VELAS_GRAFICO=1000` | `AcompanharModelos.grafico.test.tsx` + `AcompanharModelos.test.tsx` — sem ele, 14 testes quebravam (gráfico mostrava mercado sem nenhum pedido registrado) |
| 8 | Bomba-relógio do calendário desarmada | `useEconomicData.test.ts`: "futuro" era `2026-10-13T12:00` fixo e virou passado hoje; agora +2 dias relativo |

## Números

- Frontend: `tsc` limpo, **892/892 vitest (69 arquivos)**.
- Python: **1355 passed, 2 skipped** (skips pré-existentes).
- Build 7/7 exit 0; NSIS 1.2.4 de 13/10 12:05; bridge instalada com hash igual ao fonte.
- Preflight `app-rodando`: 3/3 portas ocupadas, MQL5 intacto, versão 1.2.4 — **1 falha: disco 3,96 GB < 4,0 GB** (ambiental, fora do repo; app no ar).

## Commits (origin/develop)

`dffec2c` (mouse/fuso/pares/IA) → `20623b6` (cards) → `84a2886` (luz/dubles/calendário).

## O que NÃO foi feito (aberto, precisa do dono)

1. **Tabela embaixo + linha "Controle"** — sem a captura não dá para saber qual tabela/linha é; não mexi para não quebrar o que está funcionando.
2. **Espaço vazio de ~40%** — idem: preciso saber em qual aba/painel ele aparece.
3. **"Qual desses itens tem utilidade?"** — preciso da lista de ferramentas (nomes na tela) para auditar uma por uma contra o código.
4. **Stale TP/SL ao trocar aba/período + re-anexo do EA** — seguem abertos do ciclo anterior.
