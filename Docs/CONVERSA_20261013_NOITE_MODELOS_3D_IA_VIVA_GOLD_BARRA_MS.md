# Ciclo 13/10/2026 (noite) — lote do dono: modelos 3D, IA viva, GOLD, barra, ms

## Pedidos e destino

| # | Pedido | Feito |
|---|---|---|
| 1 | Modelos: tabela maior, compacta, icones, ocupar a sub-aba, cards 3D com efeitos | Grade ate 54vh, minmax 190px, tilt 3D + brilho no hover + arte por matiz do id + sigla tolerando plural (`cripto`→CRY). `prefers-reduced-motion` respeitado |
| 2 | IA no risco otimizada, motor inteligente, sempre viva | Auto-sugestao ao trocar de cenario com campos vazios (uma vez por par/periodo/corretora/mercado); nunca sobrescreve o digitado; Aplicar segue manual |
| 3 | Terminal usar todo o espaco | journal `max-height: min(46vh, 520px)` (era 300px) |
| 4 | ms fora da tela, corrigir medicao | A barra mostrava o ms da MELHOR medicao: com MEXC ativa e Binance mais rapida, o numero era o da Binance. Agora recebe a conta ativa e mostra o ms dela; sem conta, segue a melhor |
| 5 | Sem GOLD como ativo | GOLD (XM) via apelido do catalogo (`modelSymbol: XAUUSD`): aparece com modelos, conta como "com modelo", configura manda o simbolo do modelo |
| 6 | Barra inferior controlando tudo | Trocar o par na barra agora configura o motor (`{simbolo}`, merge) — antes so a tela mudava e o grafico seguia o motor (EURUSD na barra, BTCUSD no grafico). `blur` nao fecha a lista (senao o clique no timeframe morria) |
| 7 | Menos duplicatas, mais acao | `RobotMarketBar` perdeu o `window.prompt` de troca (terceiro controle do mesmo par); simbolo virou leitura, troca na barra inferior |

## Números

- Frontend: `tsc` limpo, **913/913 vitest (72 arquivos)**.
- Python: **1355 passed, 2 skipped**.
- Build 7/7 exit 0; NSIS 1.2.4; bridge hash-igual; preflight **tudo pronto**.

## Commits (origin/develop)

`38de6b8` (gold/apelido, barra configura par, ms da conta, cards 3D, IA viva).

## Aberto (dono do gráfico / próximo)

1. Fiar `PainelIndicadores` no gráfico + barra lateral de ferramentas + fileira Desfazer/Refazer (arquivos de chart congelados).
2. Bollinger + Estocástico com desenho.
3. Stale TP/SL ao trocar aba/período + re-anexo do EA.
4. "Menos duplicates" dentro da área do gráfico (timeframes/candles) — dono do gráfico.

## Nota de ferramenta (13/10)

Append via `Add-Content` do PowerShell corrompe não-ASCII (ç/ã/í viram
U+FFFD, em-dash vira 0x97). Teste com seletor corrompido falha como se o
componente estivesse quebrado — parecia defeito de produto e era encoding do
teste. Regra: teste novo com acento usa `\uXXXX` ou as ferramentas de
escrita; conferir bytes (`decode('utf-8')`) antes de caçar defeito no
componente.
