# Ciclo 13/10/2026 (tarde) — 36 capturas, plano sem MT5, refinamentos

O dono avaliou o instalado: gráfico 10/10. Pediu: barra de ferramentas,
lista de indicadores como a de modelos, mais indicadores, e reportou que
**planos não carregam sem o MT5 aberto** (visto nas imagens).

## 1. Causa do "plano não carrega sem MT5" (achado do ciclo)

Sintoma (12:12, MT5 fechado): Plano = "Assinatura indisponível: Failed to
fetch" + journal "Spot/Futuros indisponível: Failed to fetch" — enquanto o
gráfico lia candles na mesma janela.

Causa (código, não MT5): **dez módulos congelavam `apiBase()` num
`const API` no topo** (`queries.ts:34` e mais nove), avaliado no `import` —
antes de o bootstrap resolver a porta. Com a base congelada na 9001 padrão,
e o gateway em 9011, o `fetch` batia em soquete sem dono. E na 9001 escuta o
`terminal64` do MT5 — por isso o sintoma dependia do MT5: fechado, conexão
recusada; aberto, outra resposta. Medido: `terminal64` (PID 6852) em
`LISTENING` na 9001 com o app fechado.

Corretivo: os dez resolvem `apiBase()` **por chamada**. Nenhum `const API`
resta. Trava: `portas.test.ts` conta 0 congelamentos (era 9) e nomeia quem
voltar a congelar. Bônus: o regex antigo media `const dadosApi` (falso
positivo) — agora casa o padrão exato do defeito.

## 2. Refinamentos das capturas

| # | Captura | Feito |
|---|---|---|
| Modelo H1 escolhido, gráfico M1, "escolha o timeframe" (12:21) | `SeletorModelo.escolherModelo` configura par+período via `/api/auto/config`, igual ao card; recusa aparece no campo. 3 testes novos |
| Cards com texto colidindo + `train_date` ISO cru (12:15) | mini de 1 coluna com reticências; `diaDoTreino()` (só o dia); grade até `54vh`; 3 testes |
| Risco: campos pareciam texto no escuro (12:15) | `.robo-limites-grade input` com fundo/borda das vars dos 2 temas; `robo_limites.test.ts` |
| "lista com botão igual dos modelos para indicadores" | `PainelIndicadores.tsx` novo (3 itens com Liga/Desliga + roteiro em texto) + 3 testes. **Fiação no gráfico é do dono do gráfico** (arquivos de chart congelados p/ outro agente) |
| IA sugere limites funcionando (12:54, "Limites aplicados ao motor") | confirmado nas capturas, sem mudança |
| Calendário com sigla triplicada ("GB R GB [GB]") | **não mexido**: desenho do dono do calendário; anotado |
| Gráfico vazio com eixos (12:13) | não reproduzido; anotado para verificar |

## 3. Números

- Frontend: `tsc` limpo, **903/903 vitest (72 arquivos)**.
- Python: **1355 passed, 2 skipped**.
- Build 7/7 exit 0; NSIS 1.2.4; bridge instalada hash-igual; app no ar.
- Preflight `app-rodando`: **tudo pronto** (disco 9,21 GB após limpeza).

## 4. Commits (origin/develop)

`dc551a1` (base por chamada) → `252f370` (modelo configura + cards + risco + painel).

## 5. Aberto (próximo)

1. Fiar `PainelIndicadores` no gráfico + barra lateral de ferramentas + remover fileira Desfazer/Refazer (dono do gráfico).
2. Bollinger + Estocástico: cálculo, desenho e testes (dono do gráfico).
3. Stale TP/SL ao trocar aba/período + re-anexo do EA (ciclo anterior).
4. Verificar gráfico vazio com eixos (12:13).
