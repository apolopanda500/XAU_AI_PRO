# Padrões de plataformas analisados

## Ideias aproveitáveis

| Referência | Padrão | Aplicação no XAU AI PRO |
|---|---|---|
| MT5 | Market Watch + gráfico + painel inferior | Mercado mantém watchlist; Robô concentra execução; Testador usa Diário, Resultados e Agentes |
| MT5 | Tester multiagente e otimização | Fase posterior: endpoint seguro para iniciar, parar e acompanhar agentes |
| cTrader | Active Symbol Panel | Robô mostra ativo, sessão, detalhes, spread, volume, margem e comandos no mesmo contexto |
| cTrader | Trade Watch | Inventário mostra posições, ordens pendentes, proteção, margem e P/L em uma grade única |
| TradingView | Watchlist com colunas configuráveis e alertas | Mercado usa ícone, preço, variação, spread, volume, fonte e atualização; alertas só após endpoint real |
| EMS desktop | Grades densas e múltiplos painéis | Painel usa inventário, diagnóstico e estado sem duplicar tabelas em outras abas |

## Regras de implementação

- Copiar organização e hierarquia visual, não marca, código ou identidade proprietária.
- Cada botão precisa apontar para endpoint existente; se não existir, fica ausente ou explicitamente bloqueado.
- Cada número precisa ter origem MT5, EA, Gateway ou sensor real.
- O Robô é a área de execução; Mercado é pesquisa; Histórico é reconciliação; Testador é análise.
- Conta DEMO e REAL devem ser classificadas pelo MT5 antes de liberar qualquer comando.

## Próximos endpoints úteis

- `GET /api/inventory`: já implementado; posição, ordens, exposição e heartbeat.
- `GET /api/capabilities`: já implementado; capacidades reais do Gateway.
- `GET /api/journal`: já implementado; linhas do Journal MT5.
- `GET /api/mt5/order-check`: validar ordem sem enviar.
- `GET /api/tester/status`: acompanhar teste real do MT5.
- `POST /api/tester/start` e `/stop`: somente após contrato de segurança e confirmação DEMO.
- `GET /api/alerts`: somente quando houver motor persistente de alertas.

## Referências

- MetaTrader 5 Strategy Optimization: https://www.metatrader5.com/en/terminal/help/algotrading/strategy_optimization
- MetaTrader Python positions: https://www.mql5.com/en/docs/python_metatrader5/mt5positionsget_py
- MetaTrader Python orders: https://www.mql5.com/en/docs/python_metatrader5/mt5ordersget_py
- cTrader layouts e Active Symbol Panel: https://help.ctrader.com/ctrader/interface/basics-and-layouts/
- cTrader cBots: https://help.ctrader.com/cbots/
- TradingView watchlist alerts: https://www.tradingview.com/support/solutions/43000739708-watchlist-alerts-your-trading-edge/
