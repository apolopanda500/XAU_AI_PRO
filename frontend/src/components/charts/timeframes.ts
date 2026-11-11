/*
  A JANELA DE TEMPOS, E ELA QUE O MT5 ACEITA (09/10/2026)
  =========================================================
  MEDIDO na XM (`my.xm.com/pt/symbol-info/BTCUSD`): a barra de baixo do grafico
  e `1H 1D 1W 1M 3M 1Y MAX`. Aqui eram sete botoes, de M1 a D1 — e a semana e o
  mes, que sao os periodos em que a maior parte das decisoes e tomada, nao
  estavam na tela.

  MEDIDO no MT5 desta maquina, conta 391773676 (XMGlobal-MT5 14):

      TIMEFRAME_W1  = 32769   ->  GOLD W1  = 5 barras
      TIMEFRAME_MN1 = 49153   ->  GOLD MN1 = 5 barras

  A lista vem do que o PRODUTOR aceita (`backend/mt5_gateway.py::_TIMEFRAME_MAP`),
  e nao de uma lista escrita aqui. Um botao de timeframe que o gateway recusa e o
  AGENTS.md §9 pelo avesso: controle que promete e nao entrega.

  `3M` e `1Y` NAO entraram, e a razao e a mesma do lado do gateway: o MT5 nao
  tem agregacao propria de trimestre nem de ano. Um `3M` seria soma de 12
  semanas feita na mao, e o preco viria de uma vela que o operador ve.
  `MAX` tambem nao: e um intervalo, nao um timeframe.

  POR QUE UM ARQUIVO PROPRIO (11/11/2026)
  ---------------------------------------
  O menu do botao direito passou a ter o bloco PERIODO, e o menu e filho do
  `PriceChart`. Importar a lista do proprio `PriceChart` criaria um circuito
  (PriceChart importa MenuGrafico que importa PriceChart); o `PriceChart`
  re-exporta daqui, entao os consumidores de sempre (`AcompanharModelos`) nao
  mudam de caminho e os dois lados leem a MESMA lista — o AGENTS.md §5.
*/
export const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN1'] as const;
export type ChartTimeframe = (typeof TIMEFRAMES)[number];
