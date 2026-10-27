import { useCallback, useEffect, useRef, useState } from 'react';
import { GraficoIndicador } from './GraficoIndicador';
import { bollingerValores, smaValores, vwapValores } from '../../lib/indicadores';
import MenuGrafico, { type AcaoDoMenu } from './MenuGrafico';
import PainelIndicadores, { type IndicadorId } from '../PainelIndicadores';
import '../../theme/market.css';
import '../../theme/mt5-terminal.css';
import '../../theme/menu-grafico.css';
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type LineData,
  type UTCTimestamp,
  ColorType,
  CrosshairMode,
} from 'lightweight-charts';
import { clsPnl } from '../../lib/format';
import {
  getCandles,
  LIMITE_VELAS_GRAFICO,
  type MarketBroker,
  type MarketCandle,
  type MarketKind,
} from '../../lib/marketApi';
import {
  historicoVazio,
  registrar,
  desfazer as desfazerPasso,
  refazer as refazerPasso,
  podeDesfazer,
  podeRefazer,
  rotuloDesfazer,
  rotuloRefazer,
  type Historico,
} from '../../lib/historicoGrafico';
import type { LinhaOrdem } from '../../lib/ordemGrafico';

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
  semanas feita na mao, e o preco viria de uma vela que o operador nao ve.
  `MAX` tambem nao: e um intervalo, nao um timeframe.
*/
export const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN1'] as const;
export type ChartTimeframe = (typeof TIMEFRAMES)[number];

type PriceChartProps = {
  symbol?: string;
  broker?: MarketBroker;
  market?: MarketKind;
  height?: number;
  candles?: MarketCandle[];
  timeframe?: ChartTimeframe;
  onTimeframeChange?: (timeframe: ChartTimeframe) => void;
  loading?: boolean;
  error?: string;
  sourceLabel?: string;
  // Marcadores de sinal do modelo (BUY abaixo da barra, SELL acima).
  // Tempo em segundos (mesma base dos candles) e texto curto com a
  // confianca — o operador ve ONDE o modelo decidiu, nao so o numero.
  markers?: Array<{ time: number; signal: string; text?: string }>;
  // Linhas de preco (posicoes abertas: entrada, SL, TP). So leitura: o
  // grafico mostra onde esta protegido, nao edita a ordem por arrasto.
  // Com `ticket` + `kind` + `onMoveLine`, SL/TP viram arrastaveis estilo
  // MT5: soltar aplica na hora via /api/trade/modify-position.
  lines?: Array<{ price: number; color: string; title: string; ticket?: number | string; kind?: 'sl' | 'tp' | 'entrada' }>;
  onMoveLine?: (ticket: number | string, kind: 'sl' | 'tp', price: number) => void;
  // Medias moveis exponenciais 12/26 calculadas DOS candles reais exibidos.
  // Indicador derivavel, sem fonte externa: se faltar candle, some a linha.
  ema?: boolean;
  /**
   * RSI e MACD como paineis abaixo do preco.
   *
   * MEDIDO: lightweight-charts 4.2.3 nao tem pane (so na v5), entao cada um vira
   * um segundo canvas com o proprio eixo — o mesmo desenho do MT5. Ver
   * `GraficoIndicador.tsx`.
   *
   * `false` por padrao: indicador ligado sem pedido do dono e um numero que o
   * operador nao sabe ler. O dono ligou, e o grafico mostra.
   */
  rsi?: boolean;
  macd?: boolean;
  /** Chamado quando o operador liga/desliga um indicador pela tela. */
  onIndicadoresChange?: (estado: { rsi: boolean; macd: boolean; ema: boolean }) => void;
  /*
    AS LINHAS DA ORDEM (06/10/2026, revisto em 08/10/2026)
    =====================================================
    MEDIDO nas capturas da XM: o clique ARMAVA a ordem e nao enviava. O envio e
    o botao `Colocar ordem a <preco>`, no painel.

    EM 08/10/2026 O DONO MANDOU REMOVER O CAMINHO DE 1-CLIQUE, e mediu que ele
    continuava: `AcompanharModelos.tsx:536` passa `modoOrdem` ligado, entao
    qualquer clique virava preco de entrada. Ver o bloco no efeito do clique.

    `modoOrdem` agora liga SO as linhas e o `x` que apaga stop e alvo. Nao liga
    mais preco de entrada: esse vem do ultimo fechamento, no pai.
  */
  modoOrdem?: boolean;
  /** As tres linhas da ordem armada, com o rotulo em dinheiro da XM. */
  ordem?: LinhaOrdem[];
  /** Soltar uma linha arrastada: o preco vai cru, quem arredonda e o pai. */
  onMoverLinhaOrdem?: (papel: LinhaOrdem['papel'], preco: number) => void;
  /** O `x` da linha: apaga stop ou alvo. `entrada` nao apaga. */
  onRemoverLinha?: (papel: LinhaOrdem['papel']) => void;
  /**
   * COMPRAR ou VENDER pelo menu do botao direito (09/10/2026).
   *
   * NAO envia ordem. Recebe o lado e o PRECO onde o operador clicou, e quem
   * decide o que fazer com isso e o pai — que ȩ dono do botao `Colocar ordem` e
   * da tela que mostra tudoo que vai sair.
   *
   * MEDIDO (08/10/2026 19:35, conta real 391773676): dois cliques no grafico
   * criaram tres linhas de ordem montadas a um clique do envio. O dono mandou
   * remover, e o menu direito e o MESMO perigo por outro caminho: se ele criasse
   * linha, seria o 1-clique que foi removido.
   */
  onOperarNoMenu?: (lado: 'compra' | 'venda', preco: number | null) => void;
  /**
   * O preco escolhido no menu, para stop ou alvo.
   *
   * Tambem NAO cria linha: devolve o numero para a mesa, que ȩ onde o operador
   * confirma o que vai ser enviado.
   */
  onEscolherPreco?: (papel: 'sl' | 'tp', preco: number | null) => void;
};

/** Os tres desenhos de preco que o lightweight-charts 4.2.3 sabe fazer. */
export type TipoGrafico = 'candles' | 'linha' | 'area';

/**
 * O que o operador muda no grafico e que vale um passo de desfazer.
 *
 * A COTAÇÃO NAO ENTRA. Um passo por tick tornaria o desfazer inutil: o operador
 * voltaria a um estado e o proximo tick criaria outro passo por cima. Ver
 * `lib/historicoGrafico.ts`.
 */
export type EstadoGrafico = {
  tipo: TipoGrafico;
  timeframe: ChartTimeframe;
  rsi: boolean;
  macd: boolean;
  ema: boolean;
  /** Overlays calculados dos candles exibidos. Opcionais: passos antigos de
   *  desfazer continuam validos sem eles. */
  sma?: boolean;
  bollinger?: boolean;
  vwap?: boolean;
};

export function emaValores(fechamentos: number[], periodo: number): Array<number | null> {
  if (periodo < 2 || !fechamentos.length) return fechamentos.map(() => null);
  const k = 2 / (periodo + 1);
  const saida: Array<number | null> = [];
  let anterior: number | null = null;
  fechamentos.forEach((preco, i) => {
    if (i < periodo - 1) {
      saida.push(null);
    } else if (i === periodo - 1) {
      const soma = fechamentos.slice(0, periodo).reduce((s, v) => s + v, 0);
      anterior = soma / periodo;
      saida.push(anterior);
    } else {
      anterior = preco * k + (anterior ?? preco) * (1 - k);
      saida.push(anterior);
    }
  });
  return saida;
}

/*
  RSI E MACD (05/10/2026)
  =======================
  Sao calculados DOS CANDLES REAIS EXIBIDOS, como a EMA ja era. Nao ha fonte
  externa de indicador: se faltar candle, a saida e `null` e o ponto some do
  grafico. Um RSI "de Ornimanto" vindo de servidor remoto seria dado nao
  rotulado, que e exatamente o que a regra proibe.

  SAIDA ALINHADA POR INDICE
  -------------------------
  Cada funcao devolve um array do MESMO tamanho da entrada, com `null` nas
  posicoes em que ainda nao ha valor. Alinhar por indice e o que permite
  desenhar no mesmo eixo de tempo do preco: se devolvesse so os pontos validos,
  o indicador deslizaria em relacao aos candles.
*/

/**
 * RSI de Wilder. Devolve `null` ate completar `periodo` barras de variacao.
 *
 * `periodo` abaixo de 2 nao tem media movel e devolve tudo nulo — um RSI "de 1"
 * seria 100 para qualquer variacao e o graficο mentiria sistematicamente.
 */
export function rsiValores(fechamentos: number[], periodo = 14): Array<number | null> {
  if (periodo < 2 || fechamentos.length <= periodo) {
    return fechamentos.map(() => null);
  }
  const variacoes: number[] = [];
  for (let i = 1; i < fechamentos.length; i += 1) {
    variacoes.push(fechamentos[i] - fechamentos[i - 1]);
  }

  // Semente de Wilder: media SIMPLES das primeiras `periodo` variacoes.
  let ganho = 0;
  let perda = 0;
  for (let i = 0; i < periodo; i += 1) {
    const d = variacoes[i];
    if (d >= 0) ganho += d;
    else perda -= d;
  }
  ganho /= periodo;
  perda /= periodo;

  const saida: Array<number | null> = fechamentos.map(() => null);
  saida[periodo] = rsiDe(ganho, perda);
  for (let i = periodo; i < variacoes.length; i += 1) {
    const d = variacoes[i];
    ganho = (ganho * (periodo - 1) + (d > 0 ? d : 0)) / periodo;
    perda = (perda * (periodo - 1) + (d < 0 ? -d : 0)) / periodo;
    saida[i + 1] = rsiDe(ganho, perda);
  }
  return saida;
}

/** 100 quando nao houve perda; 0 quando nao houve ganho; 50 no impasse. */
function rsiDe(ganhoMedio: number, perdaMedia: number): number {
  if (perdaMedia === 0) return ganhoMedio === 0 ? 50 : 100;
  const rs = ganhoMedio / perdaMedia;
  return 100 - 100 / (1 + rs);
}

export type Macd = {
  macd: Array<number | null>;
  sinal: Array<number | null>;
  histograma: Array<number | null>;
};

/**
 * MACD (rapida 12, lenta 26, sinal 9), tudo em array alinhado por indice.
 *
 * O sinal e uma EMA do MACD, e so existe a partir do primeiro ponto do MACD —
 * por isso `histograma` e `null` ate la: um histograma calculado sobre um sinal
 * que ainda nao existe seria numero inventado.
 */
export function macdValores(
  fechamentos: number[],
  rapida = 12,
  lenta = 26,
  sinalPeriodo = 9,
): Macd {
  const vazio = fechamentos.map(() => null);
  if (
    rapida < 2 ||
    lenta <= rapida ||
    sinalPeriodo < 2 ||
    fechamentos.length < lenta + sinalPeriodo
  ) {
    return { macd: [...vazio], sinal: [...vazio], histograma: [...vazio] };
  }

  const emaRapida = emaValores(fechamentos, rapida);
  const emaLenta = emaValores(fechamentos, lenta);
  const macd: Array<number | null> = fechamentos.map((_, i) =>
    emaRapida[i] === null || emaLenta[i] === null ? null : (emaRapida[i] as number) - (emaLenta[i] as number),
  );

  const primeiro = macd.findIndex((v) => v !== null);
  const macdCheio = macd.slice(primeiro).map((v) => v as number);
  const sinalCheio = emaValores(macdCheio, sinalPeriodo);

  const sinal: Array<number | null> = [...vazio];
  const histograma: Array<number | null> = [...vazio];
  macdCheio.forEach((v, i) => {
    const s = sinalCheio[i];
    sinal[primeiro + i] = s;
    histograma[primeiro + i] = s === null ? null : v - s;
  });

  return { macd, sinal, histograma };
}

/*
  A COR DO FECHO, SEM O ERRO DE ARREDONDAMENTO (09/10/2026)
  =========================================================
  MEDIDO: `1.14069 - 1.13999` da `0.7000000000000002` em ponto flutuante, e um
  `clsPnl` que le valor positivo pinta a vela de alta quando ela BAIXOU. O
  cabecalho do grafico ficariapaintando verde em cima de um preco que caiu — e o
  operador nao olha para a cor, ele confia nela.

  O piso de 8 casas e o mesmo do `fmtPreco`: abaixo disso o numero deixa de
  ser ruido de binario e passa a ser o movimento do preco.
*/
function arredondarPnl(valor: number): number {
  if (!Number.isFinite(valor)) return 0;
  return Math.abs(valor) < 1e-8 ? 0 : valor;
}

function defaultMarket(broker: MarketBroker | '' | string): MarketKind | '' {
  // Corretora desconhecida ou vazia: sem palpite (11/10/2026, nada de MT5
  // fixo). `''` e "ainda nao medido", e `normalizeMarketSource` trata `''`
  // como fonte invalida — a consulta nao sai e a tela recusa com motivo.
  if (broker === 'mt5') return 'forex';
  if (!broker) return '';
  return 'crypto-spot';
}

/**
 * O preco com AS CASAS QUE O PROPRIO NUMERO TRAZ (09/10/2026)
 * ===========================================================
 * MEDIDO na conta 391773676, nos dois lados:
 *
 *     MT5  copy_rates EURUSD -> 1.14069   (5 casas)
 *     MT5  copy_rates BTCUSD -> 82329.35   (2 casas no retorno, 5 na tela da XM)
 *     XM   Bitcoin vs US Dollar · 1h  Abr 85.516,15
 *
 * Uma preferencia global de casas decimais seria o AGENTS.md §9: "Casas
 * decimais nao e preferencia global". O `Digits` existe por ativo, e aqui o que
 * esta em mao e o proprio preco — com as casas que ele veio.
 *
 * Arredondado no limite de 8 casas porque `String(0.1 + 0.2)` devolve 16 casas,
 * e nenhuma corretora mostra `0,30000000000000004` num cabecalho de grafico.
 */
function fmtPreco(valor: unknown): string {
  const n = Number(valor);
  if (!Number.isFinite(n)) return '--';
  const texto = String(n);
  const casas = texto.includes('.') ? Math.min(texto.split('.')[1].length, 8) : 2;
  return n.toLocaleString('pt-BR', { minimumFractionDigits: casas, maximumFractionDigits: casas });
}

/*
  AS DUAS DECISOES QUE FAZIAM O GRAFICO FICAR ESCURO (09/10/2026)
  =================================================================
  MEDIDO no app instalado, 17:09 e 17:18, em qualquer par e qualquer timeframe:

      Grafico indisponivel: Identidade de mercado invalida.
      EURUSD sem candles reais para M1.
      0 candles

  E o backend respondia 300 candles. MEDIDO:
  `_universal_candles('mt5','forex','EURUSD','H1',300)` -> ok, count=300.

  Sao funções PURAS de proposito, e nao logica dentro do componente:

  MEDIDO nesta sessao: o defeito nao se reproduz no `jsdom` — la o `getCandles`
  falha no `fetch`, antes de chegar no `normalizeMarketSource`, e o erro que
  aparece e outro. Um teste de componente passava com a correcao LIGADA e
  DESLIGADA: decorativo, e o AGENTS.md §6 na forma mais facil de cair. Com a
  regra isolada em funcao pura, o teste mede a regra e reprova quando ela volta.

  Ver `PriceChart.candles.test.tsx`.
*/

/**
 * O mercado para consultar, ou `''` quando ele ainda nao foi medido.
 *
 * `market === undefined` cai no padrao do broker, como antes: quem chama o
 * componente sem informar o mercado continua funcionando.
 *
 * `''` NAO cai no padrao. `''` e "a classe do ativo ainda nao foi publicada",
 * e completar com `forex` seria a presuncao que o AGENTS.md §3 proibe:
 * `BTCUSD` nao e forex, e a tela provaria o erro na conta do operador.
 *
 * A expressao antiga era `market ?? defaultMarket(broker)`, e `??` so pega
 * `null` e `undefined`: com `''` ela devolvia `''`, e `normalizeMarketSource`
 * devolvia `null`, e o `getCandles` LANCAVA. Acontecia no primeiro render de
 * cada par, com o catalogo do gateway ainda nao voltado.
 */
export function mercadoParaConsulta(
  market: MarketKind | string | undefined | null,
  broker: MarketBroker,
): MarketKind | '' {
  if (market === undefined) return defaultMarket(broker);
  /*
    `null` E AUSENCIA, E `String(null)` E A PALAVRA "null".

    MEDIDO nesta sessao: com o `String(market).trim()` sozinho, `null` virava a
    string `'null'` — que nao esta em nenhum mercado habilitado, e o
    `normalizeMarketSource` a trataria como mercado desconhecido. O sintoma seria
    o mesmo de hoje, com outra letra.

    `undefined` e o unico que pega o padrao: e o que significa "o chamador nao
    informou". `null` e "informou que nao ha".
  */
  if (market === null) return '';
  return (String(market).trim() || '') as MarketKind;
}

/**
 * O erro que vale para os candles que estao na tela.
 *
 * Quem forneceu as velas e o dono do erro. `displayError = error || loadedError`
 * dava precedencia ao erro da CONSULTA PROPRIA, e ele sobrevivia a chegada das
 * velas pela prop `candles` — pintando a mensagem por cima de um grafico que ja
 * tinha dado para desenhar.
 *
 * `candles !== undefined` significa que o pai forneceu o dado (mesmo vazio), e
 * ai o erro valido e o DELE. Sem prop, quem responde e a consulta propria.
 */
export function erroVigente(
  error: string,
  loadedError: string,
  candlesPresentes: boolean,
): string {
  return candlesPresentes ? error || '' : error || loadedError;
}

/**
 * O RODAPE CONTA, OU O ERRO MANDA? (11/10/2026)
 * ==============================================
 * MEDIDO na captura do dono (12:28): o hint dizia `Gráfico indisponível:
 * candles ausentes ou inválidos no upstream` e, logo abaixo, o rodape dizia
 * `300 candles` — e no M5 `0 candles` com o eixo de horas preenchido. Dois
 * lados do mesmo dado discordando (AGENTS.md §5): o operador lia "sem candles"
 * e "300 candles" no mesmo bloco, e nao sabia qual dos dois acreditar.
 *
 * A causa: o hint e a arvore `displayError`, e o rodape e
 * `displayCandles.length`. São fontes DIFERENTES — `erroVigente` pode devolver
 * `''` (sem erro vigente) enquanto a prop trouxe lista vazia, e o rodape
 * escrevia `0 candles` ao lado de um eixo que mostrava dados.
 *
 * A regra: com erro vigente, o rodape NAO CONTA. O erro ja e a resposta, e
 * uma contagem ao lado dele so convida o operador a acreditar na errada.
 * `null` e "sem rotulo"; a string e o rotulo que o rodape deve escrever.
 */
export function rotuloRodape(erro: string, quantos: number): string | null {
  return erro ? null : `${quantos} candles`;
}

/**
 * O TEXTO DA LINHA DE AVISO, e o nome dela (11/10/2026).
 *
 * MEDIDO na captura das 12:24, MT5 fechado: a tela dizia "Gráfico indisponível"
 * AO LADO de um gráfico com 300 candles desenhados. O motivo era do PAI (a
 * atualização de 30s falhou), o prefixo era DESTE componente — e os dois
 * discordavam do que a própria tela mostrava. AGENTS.md 5, em dois lados do
 * mesmo dado: o operador culpa o gráfico, que está ali, com o dado de antes.
 *
 * Com candles na tela não há gráfico indisponível: a falha é da ATUALIZAÇÃO, e
 * o texto é o do pai, sem o prefixo. Sem candles, o gráfico mesmo não está
 * disponível e o nome continua o de sempre — que é o que os testes e o
 * histórico de capturas reconhecem.
 *
 * Função pura de propósito: o defeito não se reproduz no `jsdom` (o motivo está
 * em `PriceChart.regras.test.ts`, no cabeçalho), então a regra é medida aqui.
 */
export function textoDoAlertaDeErro(error: string, temCandles: boolean): string {
  return temCandles ? error : `Gráfico indisponível: ${error}`;
}

/**
 * O SEPARADOR DO CABEÇALHO, E ELE QUE IMPEDE A COLAGEM (11/10/2026).
 *
 * MEDIDO na captura do dono (12:28): `FECHA 83.129,45Candles OHLC reais` — os
 * dois blocos colados sem espaço, lidos como `45Candles`. A causa é de CSS: os
 * dois `<span>` são IRMÃOS inline, e o `gap: 6px` do `.price-chart-ohlc`
 * (`mt5-terminal.css:177`) é o espaço INTERNO do flexbox — ele só separa os
 * filhos do próprio span, nunca os dois spans entre si.
 *
 * Sem um separador textual, o olho lê a união dos dois como uma palavra só.
 * É pior que espaçamento errado: o número do fechamento encosta no nome da
 * fonte e o operador lê `83.129,45Candles` como se fosse um rótulo só.
 *
 * Função pura porque o defeito é de layout e não se reproduz no `jsdom`
 * (mesmo motivo de `textoDoAlertaDeErro`): a regra é medida aqui, e o JSX só
 * aplica o que ela devolve.
 *
 * @param temOhlc a linha OHLC está na tela (há candle);
 * @param fonte    o rótulo da fonte que vai depois — vazio quando não há.
 * @returns o separador a imprimir entre o OHLC e a fonte, ou `''` se não há
 *          os dois lados para separar.
 */
export function separadorCabecalho(temOhlc: boolean, fonte: string): string {
  return temOhlc && fonte ? ' · ' : '';
}

export default function PriceChart({
  symbol = '',
  // SEM CORRETORA PADRAO (11/10/2026, decisao do dono: nada de MT5 fixo). Era
  // `broker = 'mt5'` — e o cabecalho nascia "MT5 · ..." sem ninguem escolher.
  // Quem chama passa a corretora medida; sem ela, a fonte some do cabecalho
  // (ver abaixo) e nada e consultado (ver `defaultMarket` e `activeMarket`).
  broker = '' as MarketBroker,
  market,
  height = 360,
  candles,
  timeframe,
  onTimeframeChange,
  loading = false,
  error = '',
  sourceLabel,
  markers = [],
  lines = [],
  ema: emaProp,
  rsi: rsiProp,
  macd: macdProp,
  onIndicadoresChange,
  onMoveLine,
  modoOrdem = false,
  ordem = [],
  onMoverLinhaOrdem,
  onRemoverLinha,
  onOperarNoMenu,
  onEscolherPreco,
}: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'>>(null);
  const linhasRef = useRef<Array<ReturnType<ISeriesApi<'Candlestick'>['createPriceLine']>>>([]);
  const linhasOrdemRef = useRef<Array<ReturnType<ISeriesApi<'Candlestick'>['createPriceLine']>>>([]);
  const emaRef = useRef<Array<ISeriesApi<'Line'>>>([]);
  const overlaysRef = useRef<Record<string, ISeriesApi<'Line'>>>({});
  const volumeRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const legendaRef = useRef<HTMLDivElement>(null);
  /*
    Quantos candles JA FORAM ENQUADRADOS pelo `fitContent`.

    E um `ref` do COMPONENTE, nao do efeito: MEDIDO (06/10/2026), declarar
    `useRef` dentro do corpo de um efeito lanca "Invalid hook call" e derruba o
    componente inteiro — o grafico desaparece da tela. Hook vive no corpo do
    componente, sempre.

    O que ele guarda e o NUMERO de candles do ultimo enquadramento. `fitContent`
    so deve rodar quando o CONJUNTO muda (trocar de ativo, timeframe ou tipo de
    grafico), e nao a cada cotacao — ver o uso no efeito dos dados.
  */
  const candlesEnquadrados = useRef(0);
  const [chartReady, setChartReady] = useState(false);
  const [internalTimeframe, setInternalTimeframe] = useState<ChartTimeframe>('M5');

  /*
    O MENU DO BOTAO DIREITO (09/10/2026)
    ====================================
    MEDIDO na captura da XM (`Screenshot 2026-10-09 201959.png`): o clique
    direito dentro do grafico abre TRADE, VER, DESENHAR e LIMPAR. Aqui abria o
    menu DO WEBVIEW — Recarregar, Inspecionar, Imprimir —, que e do navegador e
    nao tem nenhuma funcao de operacao. O dono pediu: "quando tem direito tem
    que abrir todas funcoes do menu".

    `precoNoMenu` e o preco ONDE o clique caiu: e o que a linha de stop e de
    alvo usam para nascer no lugar que o operador apontou, e nao no meio do
    grafico. Vem de `coordinateToPrice`, que e o valor real da serie — nunca
    estimado pelo tamanho do grafico.
  */
  const [menu, setMenu] = useState({ aberto: false, x: 0, y: 0, preco: null as number | null });

  /** Converte o Y do mouse no preco da serie. `null` quando a serie nao diz. */
  const precoDoPixel = useCallback((clientY: number): number | null => {
    const el = containerRef.current;
    const series = seriesRef.current;
    if (!el || !series) return null;
    try {
      const p = series.coordinateToPrice(clientY - el.getBoundingClientRect().top);
      return typeof p === 'number' && Number.isFinite(p) ? p : null;
    } catch {
      return null;
    }
  }, []);

  const abrirMenu = useCallback(
    (e: { clientX: number; clientY: number; preventDefault: () => void }) => {
      e.preventDefault();
      const el = containerRef.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      setMenu({
        aberto: true,
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        preco: precoDoPixel(e.clientY),
      });
    },
    [precoDoPixel],
  );

  /**
   * O que cada item do menu faz.
   *
   * A REGRA DO DONO, 08/10/2026, VALE AQUI TAMBEM
   * =============================================
   * "O clique nao arma ordem": MEDIDO em 08/10/2026 19:35, conta real
   * 391773676 — dois cliques criaram tres linhas de ordem a 75670,29 /
   * 75470,29 / 75270,29, a um clique do botao `Colocar ordem`. O defeito nunca
   * foi enviar sozinho; era ARMAR sozinho.
   *
   * Por isso `operar-compra` e `operar-venda` NAO criam linha nenhuma: elas
   * passam o PRECO onde o operador clicou para o pai, que e quem tem o botao
   * `Colocar ordem` e a tela mostra tudoo que vai sair. O menu DIREITO nao
   * pode virar o caminho por onde a ordem nasce sozinha — se ele criasse linha,
   * seria o 1-clique que o dono mandou remover, so que pelo botao direito.
   *
   * O menu direito mexe na VISTA (zoom, grade, tipo, ferramenta) e escolhe o
   * PRECO de stop e alvo — que e informacao para a mesa, nao ordem.
   */

  /*
    O `x` DE CADA LINHA da ordem armada, e o clique que ARMA.

    O `x` e um botao de verdade, e por isso que ele nao pode ser o `title` da
    `createPriceLine`: aquele e TEXTO desenhado no canvas e nao recebe clique.
    MEDIDO no typings da 4.2.3: `createPriceLine` devolve `IPriceLine` com
    `applyOptions`/`options`/`remove`, e nao ha evento. Um `x` desenhado como
    texto seria o botao que parece funcionar e nao funciona — o mesmo defeito do
    botao EMA que o dono reportou.

    A CAMADA DE CLIQUE e um `div` por cima do canvas, com `pointer-events: none`
    no container e `auto` so no botao. Sem isso o `div` transparence o grafico
    inteiro e o crosshair, o arraste e o `fitContent` param de funcionar.

    As COORDENADAS sao lidas de `series.priceToCoordinate(preco)`, que e a
    unica fonte: escrever uma conta de onde a linha esta na tela seria o app
    inventando a posicao, e a linha cairia no lugar errado a cada zoom.
  */
  const overlayOrdemRef = useRef<HTMLDivElement>(null);
  /*
    Linha de POSICAO ja segurada pelo arraste existente.

    Os dois arastes escutam o mesmo `mousedown`. Sem esta trava, clicar perto de
    um SL de posicao arrastaria a posicao E armada a ordem no preco do clique —
    doisvely estados a partir de um clique so. Quem segura primeiro ganha.
  */
  const posicaoSegurada = useRef(false);

  const [rsiInterno, setRsiInterno] = useState(false);
  const [macdInterno, setMacdInterno] = useState(false);
  const [emaInterno, setEmaInterno] = useState(false);
  /*
    SMA, BOLLINGER E VWAP (23/10/2026)
    ----------------------------------
    A barra de indicadores so tinha EMA, RSI e MACD. Estes tres sao os que o
    MT5 traz de fabrica e que o operador usa para entrada e saida. Ficam em
    estado proprio porque nao vem do pai (nao ha prop para eles) e sao
    recalculados dos candles EXIBIDOS, como os demais.
  */
  const [extras, setExtras] = useState({ sma: false, bollinger: false, vwap: false });
  /*
    TELA CHEIA (23/10/2026)
    -----------------------
    O pedido foi "botao full tela". Um botao que chama `requestFullscreen` numa
    janela do Tauri funciona no Chromium embutido; quando a API nao existir, o
    botao fica DESABILITADO e o `title` diz o motivo — controle que parece
    funcionar e nao funciona e o defeito que o AGENTS.md §9 descreve.
  */
  const wrapRef = useRef<HTMLDivElement>(null);
  const [telaCheia, setTelaCheia] = useState(false);
  const suportaTelaCheia =
    typeof document !== 'undefined' && Boolean(document.documentElement.requestFullscreen);
  const alternarTelaCheia = useCallback(() => {
    const el = wrapRef.current;
    if (!el || !suportaTelaCheia) return;
    if (document.fullscreenElement) {
      void document.exitFullscreen?.().catch(() => undefined);
      return;
    }
    void el.requestFullscreen?.().catch(() => undefined);
  }, [suportaTelaCheia]);

  useEffect(() => {
    const aoMudar = () => {
      setTelaCheia(document.fullscreenElement === wrapRef.current);
      // O canvas do lightweight-charts nao escuta o container: sem este
      // `resize`, sair da tela cheia devolveria um grafico com a largura da
      // tela inteira dentro de uma coluna estreita.
      const el = containerRef.current;
      const chart = chartRef.current;
      if (el && chart) {
        const { width, height } = el.getBoundingClientRect();
        if (width > 0 && height > 0) chart.resize(width, height);
      }
    };
    document.addEventListener('fullscreenchange', aoMudar);
    return () => document.removeEventListener('fullscreenchange', aoMudar);
  }, []);
  const [loadedCandles, setLoadedCandles] = useState<MarketCandle[]>([]);
  const [loadedError, setLoadedError] = useState('');
  /*
    OS INDICADORES PODEM VIR LIGADOS DO PAI, E O PAI PODE NAO MANDAR.

    `rsi`/`macd`/`ema` sao props com default `false`. Quando o pai nao passa a
    prop, o valor interno e o que vale; quando passa, a prop manda. Sem isso o
    botao da tela nao teria efeito nenhum em quem ja manda `rsi={false}` por
    omissao — e um controle que parece funcionar e nao funciona.
  */
  const rsiExterno = rsiProp ?? rsiInterno;
  const macdExterno = macdProp ?? macdInterno;
  const emaExterno = emaProp ?? emaInterno;
  const setRsi = (v: boolean) => {
    if (rsiProp === undefined) setRsiInterno(v);
    onIndicadoresChange?.({ ...indicadoresAtuais, rsi: v });
    // Um indicador que muda o desenho do grafico e um PASSO de desfazer. Sem
    // esta linha, o "desfazer" voltaria so o tipo de grafico e o operador
    // veria o RSI continuar ligado depois de desfazer — o botao pareceria
    // funcionar e nao desfaria o que ele fez.
    if (v !== rsiExterno) {
      registrarPasso(
        { tipo: tipoGrafico, timeframe: activeTimeframe, rsi: v, macd: macdExterno, ema: emaExterno },
        v ? 'ligar RSI' : 'desligar RSI',
      );
    }
  };
  const setMacd = (v: boolean) => {
    if (macdProp === undefined) setMacdInterno(v);
    onIndicadoresChange?.({ ...indicadoresAtuais, macd: v });
    if (v !== macdExterno) {
      registrarPasso(
        { tipo: tipoGrafico, timeframe: activeTimeframe, rsi: rsiExterno, macd: v, ema: emaExterno },
        v ? 'ligar MACD' : 'desligar MACD',
      );
    }
  };
  const setEma = (v: boolean) => {
    if (emaProp === undefined) setEmaInterno(v);
    onIndicadoresChange?.({ ...indicadoresAtuais, ema: v });
    if (v !== emaExterno) {
      registrarPasso(
        { tipo: tipoGrafico, timeframe: activeTimeframe, rsi: rsiExterno, macd: macdExterno, ema: v },
        v ? 'ligar EMA' : 'desligar EMA',
      );
    }
  };
  const indicadoresAtuais = { rsi: rsiExterno, macd: macdExterno, ema: emaExterno };

  /*
    O TIPO DE GRAFICO E O HISTORICO (06/10/2026)
    ===========================================
    O dono pediu a barra da XM: `1h · tipo de grafico · Indicadores · layout ·
    + · desfazer · refazer`.

    TIPO DE GRAFICO
    ---------------
    `lightweight-charts` 4.2.3 tem tres desenhos de preco — candlestick, linha
    e area — e eles sao SERIES DIFERENTES, com metodos diferentes. Trocar o tipo
    e criar outra serie: nao e uma opcao de `applyOptions`. Por isso a serie vive
    num `useEffect` que depende do tipo, e nao no efeito de criacao do grafico.

    CANDLES SEMPRE
    -------------
    O grafico SEMPRE nasce em candlestick. A barra comeca em `candles` e o
    operador escolhe a partir dai. O eixo de preco, as linhas de SL/TP e a
    legenda OHLC dependem do desenho de candlestick — e sao eles que o operador
    usa para conferir a protecao da posicao.

    DESFAZER E REFAZER
    ------------------
    Historico de verdade, em `lib/historicoGrafico.ts`. O que entra nele e o que
    muda o desenho do grafico: tipo de grafico, os tres indicadores e o timeframe.
    O que NAO entra e a cotacao — senao o proximo tick criaria um passo novo e o
    operador nunca voltaria a um estado anterior.
  */
  const [tipoGrafico, setTipoGrafico] = useState<TipoGrafico>('candles');
  /*
    `seriesAtivo` e o SINAL de que a serie de preco existe.

    MEDIDO (06/10/2026, app instalado): o grafico saia VAZIO. A serie e criada por
    um efeito que depende de `chartReady`, e o efeito que DESENHA os dados
    dependia so de `chartReady` e `displayCandles`. Na primeira passagem a serie
    ainda era `null`, o efeito de dados saia com `return`, e nao voltava a rodar —
    os dados nunca chegavam a serie.

    Este contador existe para打破 esse deadlock: o efeito que desenha depende
    dele, entao a criacao da serie dispara o desenho. E um numero, nao a serie,
    porque a serie vive num `ref` (nao causa re-render por si so).

    A barra de tipo de grafico nao usa este sinal.
  */
  const [seriesAtivo, setSeriesAtivo] = useState(0);
  const historicoRef = useRef<Historico<EstadoGrafico>>(historicoVazio<EstadoGrafico>({
    tipo: 'candles',
    timeframe: 'M5',
    rsi: false,
    macd: false,
    ema: false,
  }));
  const [passos, setPassos] = useState(0);
  const [refaziveis, setRefaziveis] = useState(0);

  /** Um passo novo, e a contagem que os botoes leem. */
  const registrarPasso = useCallback(
    (depois: EstadoGrafico, rotulo: string) => {
      const anterior = historicoRef.current;
      const novo = registrar(anterior, depois, rotulo);
      historicoRef.current = novo;
      setPassos(novo.passos.length);
      setRefaziveis(novo.refazer.length);
    },
    [],
  );

  const activeTimeframe = timeframe ?? internalTimeframe;
  /*
    MERCADO VAZIO E "AINDA NAO MEDIDO", E NAO `forex` (09/10/2026)
    ==============================================================
    MEDIDO no app instalado, 17:09 e 17:18, em qualquer par e qualquer
    timeframe — EURUSD, AUDUSD, H1, M1, todos iguais:

        Gráfico indisponível: Identidade de mercado inválida.
        EURUSD sem candles reais para M1.
        RSI (14) precisa de 15 candles; há 0.
        0 candles

    E o BACKEND estava respondendo 300 candles corretos. MEDIDO:

        _universal_candles('mt5','forex','EURUSD','H1',300) -> ok, count=300
        EURUSD 1.14166 -> 1.14069 ... ultima 1.12009

    A CAUSA, em duas partes, e as duas no MESMO lugar
    =================================================
    1. `market ?? defaultMarket(broker)`: `??` so pega `null` e `undefined`.
       A cadeia entrega `String(mercadoDaFicha ?? auto?.market ?? '')`, que e
       `''` — string vazia. Entao `activeMarket` ficava `''`,
       `normalizeMarketSource('mt5','')` devolvia `null` (porque `''` nao esta
       em `markets`), e o `getCandles` LANCAVA "Identidade de mercado invalida".

       E isso acontecia no PRIMEIRO RENDER de cada par: o catalogo do gateway
       ainda nao tinha voltado, entao `mercadoDaFicha` era `null` e a cadeia
       entregava `''`. O operador lia um erro de IDENTIDADE e culpava o
       servidor — que estava com 300 velas na mao. O AGENTS.md 5.

       Aqui nao se assume `forex` como reserva. `defaultMarket` presume, e
       `BTCUSD` nao e forex: a classe vem da ficha que a corretora publica
       (AGENTS.md 3). `''` e "ainda nao medido", e nao e uma resposta.

    2. `displayError = error || loadedError`: o erro da CONSULTA PROPRIA tem
       precedencia sobre o erro do pai. Depois que os 300 candles chegaram pela
       prop, `displayCandles` estava cheio — e `displayError` continuava
       mostrando a mensagem do primeiro render, que cobre o grafico.

       Um erro de uma tentativa que ja foi superada nao pode sobreviver a dado
       novo. Nao e `error || loadedError`; e "o erro que corresponde a quem
       forneceu os candles que estou mostrando".
  */
const activeMarket = mercadoParaConsulta(market, broker);
  const displayCandles = candles ?? loadedCandles;
  const displayError = erroVigente(error, loadedError, candles !== undefined);
  /*
    A FONTE SO EXISTE COM CORRETORA (11/10/2026, nada de MT5 fixo). Sem
    `broker`, o cabecalho mostra so o OHLC — e o `separadorCabecalho` ja
    devolve `''` sem fonte, entao nada cola em nada.
  */
  const fonteDoGrafico =
    sourceLabel ?? (broker ? `${broker.toUpperCase()} · ${activeMarket}` : '');
  const latestCandle = displayCandles[displayCandles.length - 1] ?? null;
  /*
    SEM FERRAMENTAS DE DESENHO — decisao do dono, 11/10/2026.
    ==========================================================
    O grafico e para COLOCAR ORDENS, nao para editar/estudar/analisar: sairam a
    barra de ferramentas (cursor, tendencia, horizontal, apagar, limpar,
    desfazer/refazer de desenho), a fileira de estilo (cor, espessura,
    opacidade, cadeado), a camada SVG, o desenho por clique, o arraste de
    pontas, o `Ctrl + Z` de desenho e os itens de desenho do menu de contexto.

    O QUE FICA, E PORQUE E ORDEM: arrastar a ponta do stop/alvo (ajusta o
    dinheiro), o `x` que apaga stop/alvo, timeframe, tipo de grafico,
    indicadores, zoom do menu e a tabela de dados. O clique continua
    sem armar nada (08/10/2026).
  */
  const acaoDoMenu = useCallback(
    (acao: AcaoDoMenu, preco: number | null) => {
      const ts = chartRef.current?.timeScale();

      switch (acao) {
        case 'operar-compra':
        case 'operar-venda':
          // Vai para o pai, que ȩ dono do botao de envio. Sem pai, nao ha
          // menu: um clique que nao faz nada ȩ pior que o menu sem o item.
          onOperarNoMenu?.(acao === 'operar-compra' ? 'compra' : 'venda', preco);
          return;
        case 'stop':
        case 'alvo':
          onEscolherPreco?.(acao === 'stop' ? 'sl' : 'tp', preco);
          return;
        case 'zoom-mais':
        case 'zoom-menos': {
          /*
            ZOOM DE VERDADE (23/10/2026).
            Antes os dois itens chamavam `fitContent()` — "Aproximar" e
            "Afastar" faziam a MESMA coisa, e nenhuma era zoom. Agora a janela
            visivel e escalada em torno do centro.
          */
          const faixa = ts?.getVisibleLogicalRange();
          if (!ts || !faixa) return;
          const fator = acao === 'zoom-mais' ? 0.8 : 1.25;
          const centro = (faixa.from + faixa.to) / 2;
          const meia = ((faixa.to - faixa.from) * fator) / 2;
          ts.setVisibleLogicalRange({ from: centro - meia, to: centro + meia });
          return;
        }
        case 'ir-para-agora':
          ts?.scrollToRealTime();
          return;
        case 'tela-cheia':
          alternarTelaCheia();
          return;
        case 'copiar-preco': {
          const valor = preco ?? displayCandles[displayCandles.length - 1]?.close;
          if (valor === undefined || !Number.isFinite(valor)) return;
          void navigator.clipboard?.writeText(String(valor)).catch(() => undefined);
          return;
        }
        case 'ajustar':
          ts?.fitContent();
          return;
      }
    },
    [onOperarNoMenu, onEscolherPreco, alternarTelaCheia, displayCandles],
  );

  /*
    Estado de desenho REMOVIDO (11/10/2026, decisao do dono: o grafico e para
    colocar ordens). Saiu: `desenhos`, `emConstrucao`, `desenhosRef`,
    `selecionadoId`, grade/crosshair (eram write-only: nunca chegavam nas
    opcoes do grafico), `svgDesenhosRef`, a condicao e o SVG com pontas e
    previews, e a regra `.price-chart-desenhos` da folha (removida junto).
  */
  /* Historico de desenho, arraste de ponta e `raizRef` do `Ctrl + Z`: removidos
     junto (11/10/2026). O atalho de teclado de desenho saiu com a ferramenta. */

  /* `registrarPassoDesenho`, `desfazerDesenho` e `refazerDesenho`: removidos. */

  /* `selecionado`, `estiloSelecionado` e `mudarEstilo`: removidos (paleta do desenho). */

  /* Os conversores da camada de desenho e a assinatura que a repintava no zoom:
     removidos com a camada (11/10/2026). */

  /* O efeito que repintava os desenhos no zoom/deslocamento: removido. */

  const chartSummary = latestCandle
    ? `${symbol || 'Ativo'}: ${displayCandles.length} candles no timeframe ${activeTimeframe}. Último fechamento ${latestCandle.close}, abertura ${latestCandle.open}, máxima ${latestCandle.high} e mínima ${latestCandle.low}.`
    : `${symbol || 'Ativo'} sem candles reais para ${activeTimeframe}.`;

  useEffect(() => {
    if (!containerRef.current) return undefined;
    // Padrao XM: fundo do tema, grade quase invisivel, sem borda gritando.
    // Leve = pouca tinta, so preco. Candles + volume embaixo, legenda OHLC
    // no canto — o resto some.
    const chart = createChart(containerRef.current, {
      height,
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#8b93a7' },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: 'rgba(139,147,167,.06)' },
      },
      timeScale: { timeVisible: true, secondsVisible: false, borderVisible: false },
      rightPriceScale: { borderVisible: false },
      crosshair: {
        /*
          MOUSE LIVRE EM TODA PARTE (12/10/2026, decisao do dono).
          ==========================================================
          Era `CrosshairMode.Magnet`: o cursor grudava no candle mais proximo
          e so andava solto no vazio a frente — "o mouse so e livre onde nao
          tem vela". `Normal` anda em toda parte; a legenda continua seguindo
          (ela ja trata ponto ausente, ver `aoMirar`).
        */
        mode: CrosshairMode.Normal,
        vertLine: { color: 'rgba(139,147,167,.4)', labelBackgroundColor: '#4f7cff' },
        horzLine: { color: 'rgba(139,147,167,.4)', labelBackgroundColor: '#4f7cff' },
      },
    });
    /*
    A SERIE DE PRECO NASCE NO EFEITO DO `tipoGrafico`, E AQUI NAO.

    MEDIDO: ela nascia neste ponto e ficava FIXA. `addCandlestickSeries` e
    `addLineSeries` sao metodos DIFERENTES — trocar o tipo nao e opcao de
    `applyOptions` — entao o botao "tipo de grafico" teria sido decorativo, como
    o botao EMA. Ver `criarSerie` e o efeito que a consome.

    Este efeito cria o grafico e o VOLUME, que nao depende do tipo de preco.
  */
    const volume = chart.addHistogramSeries({
      priceFormat: { type: 'volume' },
      priceScaleId: 'vol',
    });
    chart.priceScale('vol').applyOptions({ scaleMargins: { top: 0.85, bottom: 0 } });
chartRef.current = chart;
  volumeRef.current = volume;
  // Legenda OHLC segue o crosshair (padrao das plataformas): atualiza o
  // DOM direto, sem setState — 60 movimentos por segundo sem re-render.
  const legenda = legendaRef.current;
  const aoMirar = (param: { time?: unknown; seriesData?: Map<unknown, unknown> }) => {
    if (!legenda) return;
    // A serie e lida do ref a cada movimento: ela troca quando o tipo muda, e
    // uma serie capturada no efeito seria a antiga depois do `removeSeries`.
    const serieAtual = seriesRef.current;
    if (!serieAtual) {
      legenda.textContent = legenda.dataset.base ?? '';
      return;
    }
    /*
      Um tipo unico, e nao uma UNIAO de "OHLC" e "valor".

      MEDIDO: com `as {open?...} | {value?:...}`, o TypeScript reprova o acesso a
      `.value` e a `.open` — o campo existe em um dos ramos, e ele nao sabe qual.
      Um tipo com todos os campos opcionais deixa o codigo ler os dois e tratar
      a ausencia pelo `typeof`, que e a forma como o dado chega de verdade: o
      crosshair manda OHLC para candle e so `value` para linha e area.
    */
    const ponto = param.seriesData?.get(serieAtual) as
      | { open?: number; high?: number; low?: number; close?: number; value?: number }
      | undefined;
    if (!ponto) {
      legenda.textContent = legenda.dataset.base ?? '';
      return;
    }
    // Em LINHA e AREA so existe o valor. Mostrar `O H L C` comecando no valor e
    // meio dado seria pior que mostrar so o que o desenho mostra.
    if (typeof ponto.value === 'number') {
      legenda.textContent = `C ${ponto.value}`;
      return;
    }
    if (typeof ponto.open !== 'number') {
      legenda.textContent = legenda.dataset.base ?? '';
      return;
    }
      const cor = ponto.close >= ponto.open ? '#2ecc71' : '#e74c3c';
      legenda.innerHTML = '';
      const etiqueta = (t: string, v: number) => {
        const b = document.createElement('b');
        b.style.color = cor;
        b.textContent = `${t} ${v}`;
        return b;
      };
      legenda.append(`O `, etiqueta('', ponto.open), ` H `, etiqueta('', ponto.high), ` L `, etiqueta('', ponto.low), ` C `, etiqueta('', ponto.close));
    };
    chart.subscribeCrosshairMove(aoMirar);
    setChartReady(true);
    const observer =
      typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(() => {
            const el = containerRef.current;
            if (!el) return;
            const width = el.clientWidth;
            const altura = el.clientHeight;
            if (width > 0 && altura > 0) chart.applyOptions({ width, height: altura });
          })
        : null;
    observer?.observe(containerRef.current);
    return () => {
      observer?.disconnect();
      chart.unsubscribeCrosshairMove(aoMirar);
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      volumeRef.current = null;
    };
  }, [height]);

/*
    A SERIE DE PRECO, conforme o TIPO ESCOLHIDO (06/10/2026)
    =======================================================
    MEDIDO: `chart.addCandlestickSeries(...)` era chamado uma vez, na criacao do
    grafico, e ficava FIXO. Trocar o tipo nao era opcao de `applyOptions` — sao
    series diferentes, com metodos diferentes — entao o botao "tipo de grafico"
    teria sido decorativo, como o botao EMA.

    A serie agora e criada e DESTRUIDA conforme o `tipoGrafico`. O grafico
    (`createChart`) continua sendo criado uma vez: recria-lo a cada troca
    perderia o zoom e a posicao do operador, que sao estado do grafico e nao
    do componente.
*/
const criarSerie = useCallback(
  (chart: IChartApi, tipo: TipoGrafico) => {
    if (tipo === 'candles') {
      return chart.addCandlestickSeries({
        upColor: '#2ecc71',
        downColor: '#e74c3c',
        borderVisible: false,
        wickUpColor: '#2ecc71',
        wickDownColor: '#e74c3c',
      }) as ISeriesApi<'Candlestick'>;
    }
    if (tipo === 'area') {
      return chart.addAreaSeries({
        lineColor: '#4f7cff',
        topColor: 'rgba(79,124,255,.28)',
        bottomColor: 'rgba(79,124,255,.02)',
        lineWidth: 2,
      }) as unknown as ISeriesApi<'Candlestick'>;
    }
    return chart.addLineSeries({
      color: '#4f7cff',
      lineWidth: 2,
    }) as unknown as ISeriesApi<'Candlestick'>;
  },
  [],
);

useEffect(() => {
  if (!chartReady) return undefined;
  const chart = chartRef.current;
  if (!chart) return undefined;
  seriesRef.current = criarSerie(chart, tipoGrafico);
  // O sinal de que a serie existe. Sem ele, o efeito que desenha os dados roda
  // uma vez (com a serie `null`), sai, e nunca mais — e o grafico fica vazio.
  setSeriesAtivo((n) => n + 1);
  return () => {
    // `removeSeries` existe na 4.2.3 e e o que impede a serie antiga de ficar
    // desenhada por cima da nova — o sintoma de "troquei para linha e continuei
    // vendo candle".
    try {
      chart.removeSeries(seriesRef.current as unknown as ISeriesApi<'Candlestick'>);
    } catch {
      /* a serie ja saiu com o grafico */
    }
    seriesRef.current = null;
  };
}, [chartReady, tipoGrafico, criarSerie]);

useEffect(() => {
    if (candles !== undefined || !symbol) return undefined;
    /*
      SEM MERCADO MEDIDO, NAO SE CONSULTA (09/10/2026)
      ================================================
      MEDIDO: com `market === ''` a consulta lancava "Identidade de mercado
      invalida" e o grafico ficava coberto por um erro que mandava culpar o
      servidor — que respondia 300 candles (ver `activeMarket` acima).

      Aqui nao se completa com `defaultMarket`: assumir `forex` para qualquer
      simbolo seria a presuncao que o AGENTS.md §3 proibe, e `BTCUSD` provaria
      o erro na tela. Sem classe publicada, o certo e NAO CHAMAR e deixar o
      pai, que tem a ficha, buscar.
    */
    if (!activeMarket) return undefined;
    const controller = new AbortController();
    let active = true;
    const load = async () => {
      try {
        const result = await getCandles(
          { broker, market: activeMarket, symbol: symbol.toUpperCase() },
          activeTimeframe,
          LIMITE_VELAS_GRAFICO,
          { signal: controller.signal },
        );
        if (active) {
          setLoadedCandles(result.candles);
          setLoadedError('');
        }
      } catch (reason) {
        if (
          active &&
          !(
            reason instanceof Error &&
            reason.name === 'MarketApiError' &&
            reason.message === 'Requisição cancelada.'
          )
        )
          setLoadedError(
            reason instanceof Error ? reason.message : 'Candles indisponíveis para esta fonte.',
          );
      }
    };
    void load();
    const timer = window.setInterval(load, 30_000);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(timer);
    };
  }, [activeMarket, activeTimeframe, broker, candles, symbol]);

  /*
    OS DADOS NA SERIE DE PRECO.

    MEDIDO (06/10/2026, app instalado): o grafico FICOU VAZIO. Este efeito lia
    `seriesRef.current` e saia com `if (!series || !chartReady) return;` — mas a
    serie so e criada por OUTRO efeito, que depende de `chartReady`. Na primeira
    passagem a serie ainda e `null`, este efeito sai sem desenhar, e nao volta a
    rodar porque `displayCandles` nao mudou.

    A CORRECAO e a serie estar na LISTA DE DEPENDENCIAS. Enquanto a serie nao
    existir, o efeito espera; quando ela e criada, o efeito roda de novo e
    desenha. E a unica forma de um efeito que depende de um recurso criado por
    outro efeito nao perder o primeiro desenho.
  */
  useEffect(() => {
    const series = seriesRef.current;
    if (!series || !chartReady) return;
    const data: CandlestickData[] = displayCandles.map((candle) => ({
      time: candle.time as UTCTimestamp,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));
    series.setData(data);
    // Volume embaixo, na cor do candle (padrao das plataformas).
    const vol = volumeRef.current;
    if (vol) {
      vol.setData(
        displayCandles.map((candle) => ({
          time: candle.time as UTCTimestamp,
          value: typeof candle.volume === 'number' ? candle.volume : 0,
          color: candle.close >= candle.open ? 'rgba(46,204,113,.5)' : 'rgba(231,76,60,.5)',
        })),
      );
    }
    // Base da legenda: ultimo candle (o crosshair sobrescreve ao mirar).
    const ultimo = displayCandles[displayCandles.length - 1];
    if (legendaRef.current && ultimo) {
      legendaRef.current.dataset.base = `O ${ultimo.open} H ${ultimo.high} L ${ultimo.low} C ${ultimo.close}`;
      if (!legendaRef.current.textContent) legendaRef.current.textContent = legendaRef.current.dataset.base;
    }
    // Sinais do modelo sobre as barras. So BUY/SELL entram; NEUTRAL e
    // recusa nao marcam o grafico (marcador sem decisao e ruido).
    const times = new Set(data.map((d) => d.time));
    series.setMarkers(
      markers
        .filter((m) => (m.signal === 'BUY' || m.signal === 'SELL') && times.has(m.time as UTCTimestamp))
        .map((m) => ({
          time: m.time as UTCTimestamp,
          position: m.signal === 'BUY' ? 'belowBar' : 'aboveBar',
          color: m.signal === 'BUY' ? '#2ecc71' : '#e74c3c',
          shape: m.signal === 'BUY' ? 'arrowUp' : 'arrowDown',
          text: m.text ?? m.signal,
        })),
    );
    // Linhas de posicao: recriadas a cada render (a API nao atualiza em
    // lote — remover e recriar e o caminho documentado).
    for (const antiga of linhasRef.current) {
      try {
        series.removePriceLine(antiga);
      } catch {
        /* linha de serie anterior, ja descartada */
      }
    }
    linhasRef.current = lines
      .filter((l) => Number.isFinite(l.price))
      .map((l) =>
        series.createPriceLine({
          price: l.price,
          color: l.color,
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: l.title,
        }),
      );
    const emaSerie = emaRef.current;
    if (emaExterno && chartRef.current) {
      const fechas = data.map((d) => d.close);
      const pares: Array<number[]> = [
        emaValores(fechas, 12),
        emaValores(fechas, 26),
      ];
      const cores = ['#f0b90b', '#a78bfa'];
      pares.forEach((valores, idx) => {
        const pontos = data
          .map((d, i) => (valores[i] === null ? null : { time: d.time, value: valores[i] as number }))
          .filter((p): p is { time: UTCTimestamp; value: number } => p !== null);
        const existente = emaSerie[idx];
        if (existente) {
          existente.setData(pontos);
        } else if (pontos.length) {
          emaSerie[idx] = chartRef.current!.addLineSeries({
            color: cores[idx],
            lineWidth: 1,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
          });
          emaSerie[idx].setData(pontos);
        }
      });
    } else {
      for (const s of emaSerie) {
        try {
          chartRef.current?.removeSeries(s);
        } catch {
          /* ja removida */
        }
      }
      emaRef.current = [];
    }
    /*
      OVERLAYS: SMA 20, BOLLINGER (20, 2) E VWAP.
      `null` vira buraco no desenho: ponto que o indicador ainda nao pode
      calcular nao e zero, e ligar os pontos por cima inventaria valor.
    */
    const fechasOverlay = displayCandles.map((c) => c.close);
    const desenharOverlay = (
      id: string,
      cor: string,
      valores: Array<number | null>,
      largura: 1 | 2 = 1,
    ) => {
      const pontos = displayCandles
        .map((c, i) =>
          valores[i] === null || valores[i] === undefined
            ? null
            : { time: c.time as UTCTimestamp, value: valores[i] as number },
        )
        .filter((ponto): ponto is { time: UTCTimestamp; value: number } => ponto !== null);
      const existente = overlaysRef.current[id];
      if (!pontos.length) {
        if (existente) {
          try {
            chartRef.current?.removeSeries(existente);
          } catch {
            /* ja removida */
          }
          delete overlaysRef.current[id];
        }
        return;
      }
      if (existente) {
        existente.setData(pontos);
        return;
      }
      if (!chartRef.current) return;
      const serie = chartRef.current.addLineSeries({
        color: cor,
        lineWidth: largura,
        priceLineVisible: false,
        lastValueVisible: false,
        crosshairMarkerVisible: false,
      });
      serie.setData(pontos);
      overlaysRef.current[id] = serie;
    };
    const boll = bollingerValores(fechasOverlay, 20, 2);
    if (extras.sma) desenharOverlay('sma20', '#3b82f6', smaValores(fechasOverlay, 20));
    if (extras.bollinger) {
      desenharOverlay('boll-sup', 'rgba(167,139,250,.65)', boll.superior);
      desenharOverlay('boll-inf', 'rgba(167,139,250,.65)', boll.inferior);
      desenharOverlay('boll-med', '#a78bfa', boll.media);
    }
    if (extras.vwap) desenharOverlay('vwap', '#f59e0b', vwapValores(displayCandles));
    for (const id of Object.keys(overlaysRef.current)) {
      if (id.startsWith('sma20') && !extras.sma) {
        try { chartRef.current?.removeSeries(overlaysRef.current[id]); } catch { /* ja removida */ }
        delete overlaysRef.current[id];
      }
      if (id.startsWith('boll') && !extras.bollinger) {
        try { chartRef.current?.removeSeries(overlaysRef.current[id]); } catch { /* ja removida */ }
        delete overlaysRef.current[id];
      }
      if (id === 'vwap' && !extras.vwap) {
        try { chartRef.current?.removeSeries(overlaysRef.current[id]); } catch { /* ja removida */ }
        delete overlaysRef.current[id];
      }
    }
    /*
    AJUSTAR A ESCALA SO QUANDO O NUMERO DE CANDLES MUDA.

    MEDIDO (06/10/2026, app instalado): o dono reportou "quando eu desloco, depois
    ele volta para onde esta fixo sem eu apertar nada". A causa e esta linha:
    `fitContent()` era chamado a CADA `setData`, e `setData` roda a cada candle
    novo — que chega a cada cotacao. O operador arrastava para ver um ponto, o
    proximo candle chegava, e a visao voltava para o fim.

    `fitContent()` e o que enquadra o grafico quando o operador TROCA de ativo ou
    de timeframe. Ele nao deve rodar a cada atualizacao de valor.

    A guarda e pelo NUMERO de candles: `setData` com os MESMOS horarios e um
    candle a mais e uma cotacao — nao muda o enquadramento. Trocar de ativo,
    timeframe ou tipo de grafico muda o conjunto, e ai o `fitContent` e correto.
  */
  if (data.length && data.length !== candlesEnquadrados.current) {
    candlesEnquadrados.current = data.length;
    chartRef.current?.timeScale().fitContent();
  }
  }, [chartReady, displayCandles, markers, lines, emaExterno, tipoGrafico, seriesAtivo, extras]);

  // Arrastar SL/TP estilo MT5. So linhas com ticket+kind sao moveis; a
  // entrada nunca arrasta. O preco segue o mouse via rAF (sem travar) e
  // SOLTAR aplica via onMoveLine — igual ao terminal, sem modal no meio.
  useEffect(() => {
    const el = containerRef.current;
    const series = seriesRef.current;
    if (!el || !series || !chartReady || !onMoveLine) return undefined;
    const moveis = lines.filter(
      (l): l is { price: number; color: string; title: string; ticket: number | string; kind: 'sl' | 'tp' } =>
        (l.kind === 'sl' || l.kind === 'tp') && l.ticket !== undefined,
    );
    if (!moveis.length) return undefined;
    let alvo: { ticket: number | string; kind: 'sl' | 'tp' } | null = null;
    let precoSessao = 0;
    let frame = 0;
    let pressY = 0;
    let moveu = false;
    const yParaPreco = (clientY: number): number | null => {
      const rect = el.getBoundingClientRect();
      try {
        const p = series.coordinateToPrice(clientY - rect.top);
        return typeof p === 'number' && Number.isFinite(p) ? p : null;
      } catch {
        return null;
      }
    };
    const perto = (clientY: number) => {
      const rect = el.getBoundingClientRect();
      const py = clientY - rect.top;
      let melhor: typeof alvo & { dist: number } | null = null;
      for (const l of moveis) {
        let ly: number | null = null;
        try { ly = series.priceToCoordinate(l.price); } catch { ly = null; }
        if (ly === null) continue;
        const distPx = Math.abs(ly - py);
        // 8px de tolerancia: pegar a linha e facil, mas nao pega a linha vizinha.
        if (distPx <= 8 && (!melhor || distPx < melhor.dist)) melhor = { ticket: l.ticket, kind: l.kind, dist: distPx };
      }
      return melhor;
    };
    const redesenhar = () => {
      frame = 0;
      if (!alvo) return;
      for (let i = 0; i < linhasRef.current.length; i++) {
        const base = moveis[i];
        if (!base || base.ticket !== alvo.ticket || base.kind !== alvo.kind) continue;
        try {
          series.removePriceLine(linhasRef.current[i]);
        } catch {
          /* serie anterior */
        }
        try {
          linhasRef.current[i] = series.createPriceLine({
            price: precoSessao,
            color: base.color,
            lineWidth: 2,
            lineStyle: 0,
            axisLabelVisible: true,
            title: base.title,
          });
        } catch {
          /* fora da escala visivel */
        }
      }
    };
    const aoMover = (e: MouseEvent) => {
      if (!alvo) {
        el.style.cursor = perto(e.clientY) ? 'ns-resize' : '';
        return;
      }
      if (Math.abs(e.clientY - pressY) > 3) moveu = true;
      const p = yParaPreco(e.clientY);
      if (p === null) return;
      precoSessao = p;
      if (!frame) frame = window.requestAnimationFrame(redesenhar);
    };
    const aoSoltar = (e: MouseEvent) => {
      if (!alvo) return;
      const final = alvo;
      alvo = null;
      el.style.cursor = '';
      if (frame) {
        window.cancelAnimationFrame(frame);
        frame = 0;
      }
      // CLIQUE PURO = queda no MESMO ponto (mesma folga de 3px do `aoMover`).
      // O proprio `mouseup` e prova de arraste: queda longe da pressao move,
      // mesmo sem `mousemove` intermediario — o navegador pode agrupar ou omitir
      // moves em arraste rapido, e quem consome o evento e o soltar.
      // 63e4680 quis matar o clique, nao o soltar longe.
      if (!moveu && Math.abs(e.clientY - pressY) <= 3) return;
      const p = yParaPreco(e.clientY);
      if (p !== null) onMoveLine(final.ticket, final.kind, Math.round(p * 100) / 100);
    };
    const aoPressionar = (e: MouseEvent) => {
      const achou = perto(e.clientY);
      if (achou) {
        alvo = { ticket: achou.ticket, kind: achou.kind };
        const atual = moveis.find((l) => l.ticket === achou.ticket && l.kind === achou.kind);
        precoSessao = atual ? atual.price : 0;
        pressY = e.clientY;
        moveu = false;
        el.style.cursor = 'ns-resize';
        e.preventDefault();
        // A linha de posicao foi segurada: o clique nao arma ordem. Ver
        // `posicaoSegurada`.
        posicaoSegurada.current = true;
      }
    };
    el.addEventListener('mousedown', aoPressionar);
    window.addEventListener('mousemove', aoMover);
    window.addEventListener('mouseup', aoSoltar);
    return () => {
      el.removeEventListener('mousedown', aoPressionar);
      window.removeEventListener('mousemove', aoMover);
      window.removeEventListener('mouseup', aoSoltar);
      posicaoSegurada.current = false;
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [chartReady, lines, onMoveLine]);

  /*
    A ORDEM ARMADA: AS TRES LINHAS, O `x`, O ARRASTE E O CLIQUE (06/10/2026)
    =======================================================================
    MEDIDO nas capturas da XM: as tres linhas (`entrada`, `stop`, `alvo`) com o
    rotulo em dinheiro e um `x` cada, todas arrastaveis. O clique ARMA; o envio
    e o botao do painel.

    POR QUE ESTE EFEITO E SEPARADO DO ARRASTE DAS POSICOES
    -------------------------------------------------------
    As linhas de posicao tem `ticket` e aplicam `/api/trade/modify-position` ao
    soltar. As linhas de ordem nao tem ticket: elas NAO existem no servidor ate
    a ordem ser enviada, e o que solt-las faz e recalcular o preco do stop ou do
    alvo e rearmar o painel. Sao dois caminhos de escrita diferentes sobre o
    mesmo `mousedown`, e misturar os dois colocaria um `ticket` de posicao no
    lugar de um `papel` de ordem.

    A TOLERANCIA DO ARRASTE
    -----------------------
    `Math.abs(p) * 0.002` e o mesmo valor do arraste de posicao, e pela mesma
    razao: 0,2% do preco e grande o bastante para pegar a linha com o mouse e
    pequeno o bastante para nao pegar a linha vizinha. Em BTCUSD a 85.000 isso
    e 170 pontos — uma faixa de 15 pixels na tela, nao a altura inteira.
  */
  useEffect(() => {
    const el = containerRef.current;
    const series = seriesRef.current;
    const overlay = overlayOrdemRef.current;
    if (!el || !series || !chartReady) return undefined;
    for (const antiga of linhasOrdemRef.current) {
      try {
        series.removePriceLine(antiga);
      } catch {
        /* serie anterior, ja descartada */
      }
    }
    const removeis = ordem.filter((l) => l.papel !== 'entrada' && Number.isFinite(l.preco));
    /*
      Desenho das tres linhas.

      `axisLabelVisible: true` escreve o preco no eixo, e `title` escreve o
      rotulo em dinheiro (`0,01 | −2,00 USD`). O `title` da XM e o dinheiro, e
      nao o preco: o preco ja esta no eixo, e repetir os dois no mesmo lugar e
      o que faz a largura da etiqueta mudar a cada tique.
    */
    linhasOrdemRef.current = ordem
      .filter((l) => Number.isFinite(l.preco))
      .map((l) =>
        series.createPriceLine({
          price: l.preco,
          color: l.cor,
          lineWidth: 1,
          lineStyle: 2,
          axisLabelVisible: true,
          title: l.rotulo,
        }),
      );

    const yParaPreco = (clientY: number): number | null => {
      const rect = el.getBoundingClientRect();
      try {
        const p = series.coordinateToPrice(clientY - rect.top);
        return typeof p === 'number' && Number.isFinite(p) ? p : null;
      } catch {
        return null;
      }
    };
    /** A linha de ordem mais proxima do cursor, para o arraste. */
    const perto = (clientY: number) => {
      const rect = el.getBoundingClientRect();
      const py = clientY - rect.top;
      let melhor: { papel: LinhaOrdem['papel']; linha: LinhaOrdem; dist: number } | null = null;
      for (const l of removeis) {
        let ly: number | null = null;
        try { ly = series.priceToCoordinate(l.preco); } catch { ly = null; }
        if (ly === null) continue;
        const distPx = Math.abs(ly - py);
        if (distPx <= 8 && (!melhor || distPx < melhor.dist)) melhor = { papel: l.papel, linha: l, dist: distPx };
      }
      return melhor;
    };
    /*
      O `x` NO LUGAR DA LINHA.

      A posicao vem de `priceToCoordinate` do proprio grafico. Um `top` calculado
      por conta propria seria um `x` que sai do lugar no primeiro zoom, e o
      operador acabaria apagando a linha errada believing no que ve.

      `priceToCoordinate` devolve `null` quando o preco esta FORA da escala
      visivel. A posicao `null` vira `-9999px`, que some: e melhor um `x`
      invisivel do que um `x` parado no topo da tela, que parece clicavel.
    */
    const posicionar = () => {
      if (!overlay) return;
      overlay.innerHTML = '';
      for (const l of removeis) {
        let coord: number | null = null;
        try {
          coord = series.priceToCoordinate(l.preco);
        } catch {
          coord = null;
        }
        const botao = document.createElement('button');
        botao.type = 'button';
        botao.className = 'price-chart-x';
        botao.textContent = '×';
        botao.dataset.papel = l.papel;
        botao.style.top = `${typeof coord === 'number' ? coord : -9999}px`;
        botao.style.borderColor = l.cor;
        botao.title = `Apagar ${l.papel === 'sl' ? 'o stop' : 'o alvo'} em ${l.preco}`;
        botao.setAttribute('aria-label', `Apagar ${l.papel === 'sl' ? 'stop' : 'alvo'}`);
        overlay.appendChild(botao);
      }
    };
    posicionar();

    let alvo: { papel: LinhaOrdem['papel']; linha: LinhaOrdem } | null = null;
    let precoSessao = 0;
    let frame = 0;
    let pressYOrdem = 0;
    let moveuOrdem = false;
    const redesenhar = () => {
      frame = 0;
      if (!alvo) return;
      const base = alvo.linha;
      try {
        series.removePriceLine(linhasOrdemRef.current[ordem.indexOf(base)]);
      } catch {
        /* ja removida */
      }
      try {
        linhasOrdemRef.current[ordem.indexOf(base)] = series.createPriceLine({
          price: precoSessao,
          color: base.cor,
          lineWidth: 2,
          lineStyle: 0,
          axisLabelVisible: true,
          title: base.rotulo,
        });
      } catch {
        /* fora da escala visivel */
      }
    };
    const aoMover = (e: MouseEvent) => {
      if (!alvo) {
        el.style.cursor = perto(e.clientY) ? 'ns-resize' : '';
        return;
      }
      if (Math.abs(e.clientY - pressYOrdem) > 3) moveuOrdem = true;
      const p = yParaPreco(e.clientY);
      if (p === null) return;
      precoSessao = p;
      if (!frame) frame = window.requestAnimationFrame(redesenhar);
    };
    const aoSoltar = (e: MouseEvent) => {
      if (!alvo) return;
      const papel = alvo.papel;
      alvo = null;
      el.style.cursor = '';
      if (frame) {
        window.cancelAnimationFrame(frame);
        frame = 0;
      }
      // Mesma regra do arraste de posicao: clique puro e queda no MESMO ponto;
      // queda longe da pressao prova arraste sem precisar de `mousemove`.
      if (!moveuOrdem && Math.abs(e.clientY - pressYOrdem) <= 3) return;
      const p = yParaPreco(e.clientY);
      if (p !== null) onMoverLinhaOrdem?.(papel, p);
    };
    /*
      O CLIQUE QUE ARMA.

      `click` e nao `mousedown`: o `mousedown` e o primeiro pedaco do arraste, e
      armar a ordem nele produziria uma ordem a cada arrastada de linha. O
      `click` so chega quando nao houve arrasto — o navegador nao emite `click`
      quando o ponteiro se move entre pressionar e soltar.

      E `posicaoSegurada` zera o estado do outro arraste: clicar em uma linha de
      posicao nao pode virar ordem.
    */
    const aoClicar = (e: MouseEvent) => {
      if (posicaoSegurada.current) {
        posicaoSegurada.current = false;
        return;
      }
      /*
        O CLIQUE NAO ARMA ORDEM — decisao do dono, 08/10/2026
        ======================================================
        Antes era `if (!modoOrdem) return;` e logo abaixo
        `onArmarOrdem?.(p)`. O dono mandou REMOVER, e nao foi removido — o
        guarda virou um MODO, e `AcompanharModelos.tsx:536` passa
        `modoOrdem` ligado sempre.

        MEDIDO em 08/10/2026 19:35, conta real 391773676: dois cliques criaram
        tres linhas de ordem a 75670,29 / 75470,29 / 75270,29, a um clique do
        botao `Colocar ordem`. MEDIDO tambem que NENHUMA ordem saiu
        (`Orders=0 | Exec=0 | Reject=0` nos 8 simbolos): o envio sempre foi o
        botao. O defeito nunca foi enviar sozinho — era ARMAR sozinho, e armar
        deixa uma ordem de verdade montada com o AUTO ligado.

        O QUE FICOU, E POR QUE:
          - ARRASTAR a ponta do stop e do alvo continua, e continua AJUSTANDO O
            DINHEIRO. E o uso que o dono descreveu: quem aceita perder 2,00 ve
            2,00 depois de arrastar. Mexer no preco ali seria trocar o risco que
            o operador escreveu.
          - o `x` que apaga stop e alvo continua, em `modoOrdem`.
          - o botao `Colocar ordem a <preco>` continua. O preco vem do ultimo
            fechamento, no pai — e nao de um clique em qualquer pixel.

        O QUE SAIU: a prop `onArmarOrdem` saiu do contrato. Nao e um `if` que
        pode ser lido ao contrario: e uma propriedade que nao existe mais, e o
        `tsc --noEmit` reprovaria qualquer tentativa de repassar.
      */
      if (!modoOrdem) return;
    };
    const aoPressionar = (e: MouseEvent) => {
      const achou = perto(e.clientY);
      if (achou) {
        alvo = { papel: achou.papel, linha: achou.linha };
        precoSessao = achou.linha.preco;
        pressYOrdem = e.clientY;
        moveuOrdem = false;
        el.style.cursor = 'ns-resize';
        e.preventDefault();
      }
    };
    const aoApagar = (e: MouseEvent) => {
      const botao = (e.target as HTMLElement | null)?.closest('button[data-papel]');
      const papel = botao?.getAttribute('data-papel') as LinhaOrdem['papel'] | null;
      if (!papel) return;
      e.preventDefault();
      e.stopPropagation();
      onRemoverLinha?.(papel);
    };
    el.addEventListener('mousedown', aoPressionar);
    el.addEventListener('click', aoClicar);
    overlay?.addEventListener('click', aoApagar);
    window.addEventListener('mousemove', aoMover);
    window.addEventListener('mouseup', aoSoltar);
    return () => {
      el.removeEventListener('mousedown', aoPressionar);
      el.removeEventListener('click', aoClicar);
      overlay?.removeEventListener('click', aoApagar);
      window.removeEventListener('mousemove', aoMover);
      window.removeEventListener('mouseup', aoSoltar);
      el.style.cursor = '';
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [chartReady, ordem, modoOrdem, onMoverLinhaOrdem, onRemoverLinha, tipoGrafico, seriesAtivo]);

  const changeTimeframe = (next: ChartTimeframe) => {
    if (onTimeframeChange) onTimeframeChange(next);
    else setInternalTimeframe(next);
  };

  return (
    <div className="card compact-card price-chart" ref={wrapRef} aria-busy={loading}>
      <div className="section-head">
        <div>
          <h2>{symbol || 'Selecione um ativo'}</h2>
          {/*
            O CABECALHO DA VELA, COMO A XM (09/10/2026)
            ============================================
            MEDIDO nas capturas da XM (`my.xm.com/pt/symbol-info/BTCUSD`,
            06/10 20:36 e 20:37): a primeira linha do grafico e

                Bitcoin vs US Dollar · 1h   Abr 85.516,15  Máx. 85.531,45
                                           Mín. 85.330,44  Fecha 82.573,70

            Aqui havia so o nome do simbolo e a frase "Candles OHLC reais". O
            operador tinha de descer o olho ate a barra de preco para saber o
            ultimo fechamento — e o cabecalho, que e o primeiro lugar que se
            olha, dizia o nome e nao o numero.

            `Abertura`, `Máxima`, `Mínima` e `Fechamento` sao os ROTULOS
            reduzidos, e nao abreviaturas inventedas: e assim que a XM escreve,
            e um operador que conhece o terminal reconhece sem traduzir nada.

            O timeframe vai no cabecalho com o MESMO rotulo da barra de baixo.

            MEDIDO numa validação desta sessão: eu havia escrito `1m` aqui e `M1`
            na barra — dois nomes para a mesma coisa na mesma tela, que e o
            AGENTS.md §5 na forma mais boba: o operador nao saberia dizer se
            `1m` e `M1` sao o mesmo timeframe. A XM escreve `1h` e o MT5
            escreve `H1`; escolher uma das duas linguas e coerente, misturar as
            duas nao e.
          */}
          {latestCandle && (
            <span className="muted price-chart-ohlc">
              {activeTimeframe}
              {' · '}
              <b>Abr</b> {fmtPreco(latestCandle.open)}
              {' · '}
              <b>Máx</b> {fmtPreco(latestCandle.high)}
              {' · '}
              <b>Mín</b> {fmtPreco(latestCandle.low)}
              {' · '}
              <b>Fecha</b>{' '}
              <span className={clsPnl(arredondarPnl(latestCandle.close - latestCandle.open))}>
                {fmtPreco(latestCandle.close)}
              </span>
            </span>
          )}
          {/*
            O SEPARADOR E TEXTO, NAO GAP (11/10/2026)
            ==========================================
            MEDIDO na captura do dono (12:28): `FECHA 83.129,45Candles OHLC
            reais`, dois blocos colados sem espaco. A causa e que os dois
            `<span>` sao IRMAOS inline, e o `gap: 6px` do
            `.price-chart-ohlc` (mt5-terminal.css:177) e o espaco INTERNO
            do flexbox — ele so separa os filhos do proprio span, nunca os
            dois spans entre si.

            O separador e UM TERCEIRO no, entre os dois, aplicado pela regra
            pura `separadorCabecalho` — porque com OHLC ele e ` · `, e sem ele
            (sem candle na tela) nao ha nada a separar. Antes ele estava DENTRO
            do span do OHLC, e continuava colado na fonte.
          */}
          {separadorCabecalho(
            latestCandle !== null,
            fonteDoGrafico,
          )}
          {fonteDoGrafico ? (
            <span className="muted">Candles OHLC reais · {fonteDoGrafico}</span>
          ) : null}
        </div>
        {/*
          A BARRA, na ordem da XM (06/10/2026)
          ======================================
          O dono pediu a barra: `1h · tipo de grafico · Indicadores · layout ·
          + · desfazer · refazer`.

          TIPO DE GRAFICO
          ---------------
          Tres botoes: candle, linha e area. Sao tres SERIES diferentes no
          lightweight-charts, e nao tres cores do mesmo desenho — por isso cada
          troca cria a serie de novo (`criarSerie`).

          NAO E UM MENU. A XM esconde em dropdown, mas tres botoes com
          `aria-pressed` mostram o estado sem clique nenhum, e o operador nao
          precisa descobrir o que ha dentro.

          DESFAZER E REFAZER
          ------------------
          O botao diz o que vai desfazer no `title` e no `aria-label`, e
          desabilita quando nao ha passo. Botao que parece funcionar sem
          funcionar e o defeito que o dono reportou no botao EMA; nao se
          repete aqui.
        */}
        <div className="btn-row" role="group" aria-label="Tipo de gráfico">
          {(
            [
              ['candles', 'Candles', 'Vela com abertura, máxima, mínima e fechamento'],
              ['linha', 'Linha', 'Só o preço de fechamento'],
              ['area', 'Área', 'Preço preenchido até a linha'],
            ] as Array<[TipoGrafico, string, string]>
          ).map(([tipo, rotulo, ajuda]) => (
            <button
              key={tipo}
              type="button"
              className={`btn sm ${tipoGrafico === tipo ? 'primary' : 'ghost'}`}
              aria-pressed={tipoGrafico === tipo}
              onClick={() => {
                setTipoGrafico(tipo);
                registrarPasso(
                  {
                    tipo,
                    timeframe: activeTimeframe,
                    rsi: rsiExterno,
                    macd: macdExterno,
                    ema: emaExterno,
                  },
                  'tipo de gráfico',
                );
              }}
              title={ajuda}
            >
              {rotulo}
            </button>
          ))}
        </div>
        <div className="btn-row" role="group" aria-label="Desfazer e refazer">
          <button
            type="button"
            className="btn sm ghost"
            onClick={() => {
              const novo = desfazerPasso(historicoRef.current);
              historicoRef.current = novo;
              setTipoGrafico(novo.atual.tipo);
              if (novo.atual.timeframe !== activeTimeframe) changeTimeframe(novo.atual.timeframe);
              setRsi(novo.atual.rsi);
              setMacd(novo.atual.macd);
              if (emaProp === undefined) setEmaInterno(novo.atual.ema);
              setExtras({
                sma: Boolean(novo.atual.sma),
                bollinger: Boolean(novo.atual.bollinger),
                vwap: Boolean(novo.atual.vwap),
              });
              onIndicadoresChange?.(novo.atual);
              setPassos(novo.passos.length);
              setRefaziveis(novo.refazer.length);
            }}
            disabled={!podeDesfazer(historicoRef.current)}
            title={
              podeDesfazer(historicoRef.current)
                ? `Desfazer: ${rotuloDesfazer(historicoRef.current)}`
                : 'Nada para desfazer'
            }
            aria-label="Desfazer"
          >
            Desfazer
          </button>
          <button
            type="button"
            className="btn sm ghost"
            onClick={() => {
              const novo = refazerPasso(historicoRef.current);
              historicoRef.current = novo;
              setTipoGrafico(novo.atual.tipo);
              if (novo.atual.timeframe !== activeTimeframe) changeTimeframe(novo.atual.timeframe);
              setRsi(novo.atual.rsi);
              setMacd(novo.atual.macd);
              if (emaProp === undefined) setEmaInterno(novo.atual.ema);
              setExtras({
                sma: Boolean(novo.atual.sma),
                bollinger: Boolean(novo.atual.bollinger),
                vwap: Boolean(novo.atual.vwap),
              });
              onIndicadoresChange?.(novo.atual);
              setPassos(novo.passos.length);
              setRefaziveis(novo.refazer.length);
            }}
            disabled={!podeRefazer(historicoRef.current)}
            title={
              podeRefazer(historicoRef.current)
                ? `Refazer: ${rotuloRefazer(historicoRef.current)}`
                : 'Nada para refazer'
            }
            aria-label="Refazer"
          >
            Refazer
          </button>
        </div>
        {/*
          INDICADORES EM LISTA COM BOTAO (25/10/2026, pedido do dono)
          ==========================================================
          A fileira de siglas virou a mesma lista dos cards de modelo: nome,
          parametros, o que mede e um botao Liga/Desliga por linha. O painel
          so chama `onAlternar`; quem desenha e este grafico. Os seis tem
          consumidor real (EMA/RSI/MACD pelas props, SMA/Bollinger/VWAP pelos
          `extras`), e o Estocastico continua como roteiro, sem botao.
        */}
        <PainelIndicadores
          ativos={{
            ema: emaExterno,
            sma: extras.sma,
            bollinger: extras.bollinger,
            vwap: extras.vwap,
            rsi: rsiExterno,
            macd: macdExterno,
          }}
          onAlternar={(id: IndicadorId) => {
            if (id === 'ema') {
              setEma(!emaExterno);
              return;
            }
            if (id === 'rsi') {
              setRsi(!rsiExterno);
              return;
            }
            if (id === 'macd') {
              setMacd(!macdExterno);
              return;
            }
            const proximo = { ...extras, [id]: !extras[id] };
            setExtras(proximo);
            // Entra no desfazer: um indicador que liga e nao desliga no
            // "desfazer" e controle que mente.
            const rotulo = id === 'sma' ? 'SMA 20' : id === 'bollinger' ? 'Bollinger' : 'VWAP';
            registrarPasso(
              {
                tipo: tipoGrafico,
                timeframe: activeTimeframe,
                rsi: rsiExterno,
                macd: macdExterno,
                ema: emaExterno,
                ...proximo,
              },
              proximo[id] ? `ligar ${rotulo}` : `desligar ${rotulo}`,
            );
          }}
        />
        <div className="btn-row" role="group" aria-label="Tela do grafico">
          <button
            type="button"
            className={`btn sm ${telaCheia ? 'primary' : 'ghost'}`}
            aria-pressed={telaCheia}
            onClick={alternarTelaCheia}
            disabled={!suportaTelaCheia}
            title={
              suportaTelaCheia
                ? telaCheia
                  ? 'Sair da tela cheia (Esc)'
                  : 'Grafico em tela cheia (F)'
                : 'Este ambiente nao permite tela cheia'
            }
          >
            {telaCheia ? 'Sair da tela' : 'Tela cheia'}
          </button>
        </div>
        <div className="btn-row" role="group" aria-label="Timeframe do gráfico">
          {TIMEFRAMES.map((value) => (
            <button
              key={value}
              type="button"
              className={`btn sm ${value === activeTimeframe ? 'primary' : 'ghost'}`}
              aria-pressed={value === activeTimeframe}
              onClick={() => changeTimeframe(value)}
            >
              {value}
            </button>
          ))}
        </div>
      </div>
      {/*
        UMA LINHA DE AVISO, E NAO TRES (09/10/2026)
        =============================================
        MEDIDO: havia tres blocos empilhados no fim do grafico — erro, "carregando
        candles" e "candles reais indisponiveis". Cada um ȧ uma linha inteira, e
        os dois ultimos dizem praticamente a mesma coisa. O dono resumiu o
        sintoma: "e pouca coisa e ocupa muito espaco".

        Agora ȧ UMA linha, com o primeiro motivo que se aplicar, na ordem do que
        o operador precisa saber primeiro:

          1. erro da consulta: o gateway respondeu e disse o que foi;
          2. carregando: ainda nao ha resposta;
          3. sem velas: respondeu, e nao trouxe nada — dai o que fazer.

        E a linha do "sem par" continua sendo a mais importante das tres, porque
        sem par o grafico nao ȧ so vazio: ele nao sabe o que desenhar.
      */}
      {/*
        E O NOME DO AVISO DEPENDE DE HA DADO OU NAO (11/10/2026)
        =========================================================
        Ver `textoDoAlertaDeErro`, acima: com candles na tela o aviso é do PAI
        e sem o "indisponível"; sem candles é o gráfico mesmo, com o nome de
        sempre. O papel (`alert`/`status`) acompanha — alerta é para o caso em
        que não há nada para olhar.
      */}
      {displayError ? (
        <div className="hint" role={displayCandles.length > 0 ? 'status' : 'alert'}>
          {textoDoAlertaDeErro(displayError, displayCandles.length > 0)}
        </div>
      ) : loading && !displayCandles.length ? (
        <div className="hint" role="status">
          Carregando candles…
        </div>
      ) : (
        !displayCandles.length && (
          <div className="hint" role="status">
            {symbol
              ? 'Candles reais indisponíveis para esta fonte.'
              : /*
                  SEM PAR: o vazio mais importante da tela.
                  ==================================
                  MEDIDO (05/10/2026): sem par escolhido, o gráfico ficava com a
                  caixa vazia e sem explicação, e o operador relatava "não tem
                  gráfico na aba robô". Um espaço em branco não é resposta: ele
                  não diz se falta par, se o gateway está fora, ou se a corretora
                  não devolveu nada.

                  A mensagem diz o que fazer AQUI, porque o seletor está no topo
                  da operação automática, nesta mesma tela.
                */
                'Sem par escolhido. Escolha em "Par para operar", no topo da operação automática.'}
          </div>
        )
      )}
      <p id="price-chart-summary" className="sr-only">
        {chartSummary}
      </p>
      {/*
        Barra de ferramentas e fileira de estilo REMOVIDAS (11/10/2026, decisao
        do dono: o grafico e para colocar ordens). Ver o comentario acima de
        `acaoDoMenu`.
      */}
        {/*
          O CONTAINER: canvas do grafico + a camada dos `x`.

          O `div` do grafico vira `position: relative` (via `.market-chart-wrap`)
          e a camada do `x` fica por cima, sem capturar ponteiro — senao ela
          transparenta o crosshair, o arraste e o clique que arma a ordem.
        */}
      <div className="market-chart-wrap">
        <div
          ref={containerRef}
          className="market-chart-canvas"
          style={{ height: telaCheia ? '100%' : height }}
          aria-label={`Gráfico de candles de ${symbol || 'ativo'}`}
          aria-describedby="price-chart-summary"
          role="img"
          tabIndex={0}
          onContextMenu={abrirMenu}
        />
        {/*
          A CAMADA DOS DESENHOS SAIU (11/10/2026, decisao do dono: o grafico e
          para colocar ordens). Saiu o SVG com pontas e previews, e a regra
          `.price-chart-desenhos` saiu junto da folha (`market.css`).
        */}
        {/*
          O MENU DO BOTAO DIREITO. Fica DENTRO do `market-chart-wrap`, que e
          `relative`, para o `left/top` daqui serem relativos ao grafico e nao a
          pagina — com menu absoluto na pagina, o menu aparecia longe do clique
          quando a pagina estava rolada.
        */}
        <MenuGrafico
          aberto={menu.aberto}
          x={menu.x}
          y={menu.y}
          precoNoPonto={menu.preco}
          aoEscolher={acaoDoMenu}
          aoFechar={() => setMenu((m) => ({ ...m, aberto: false }))}
        />
        {/*
          A CAMADA DOS `x`. So existe em `modoOrdem`, e so recebe conteudo
          quando ha stop ou alvo para apagar — a entrada nao tem `x` na XM, e um
          `x` nela seria um botao que apaga a ordem que o operador acabou de
          armar por engano de um clique.
        */}
        {modoOrdem && (
          <div ref={overlayOrdemRef} className="price-chart-overlay" aria-hidden="false" />
        )}
      </div>
      {modoOrdem && (
        <p className="hint" role="status">
          O preço da ordem é o último fechamento. Arraste a ponta do stop ou do alvo para
          ajustar o nível — o dinheiro é recalculado. O envio é o botão do painel; clicar
          no gráfico não arma nada.
        </p>
      )}
            {rsiExterno && (
        <GraficoIndicador candles={displayCandles} indicador="rsi" />
      )}
      {macdExterno && (
        <GraficoIndicador candles={displayCandles} indicador="macd" />
      )}
      <div ref={legendaRef} className="muted mono" aria-hidden="true" style={{ fontSize: 12 }} />
      {/*
        A BASE DO GRAFICO (05/10/2026) — o dono mandou "como XM".
        ==================================================
        MEDIDO na captura da XM, 21:01: na base do grafico, `1H 1D 1W 1M 3M 1Y
        MAX` a esquerda; a direita, o relogio `21:01:24 UTC-3` e, logo depois,
        o rotulo do offset — que e o botao do seletor de fuso.

        O seletor entra AQUI, ao lado do relogio, e nao em Configuracoes nem na
        barra geral: e o lugar onde o dono ja olha a hora do mercado.

        Os botoos de timeframe do cabecalho NAO foram movidos para as pills da
        base. Sao o mesmo controle em dois lugares, e duas entradas para o mesmo
        estado e divergencia esperando acontecer; mover e uma mudanca de layout
        que o dono nao pediu.
      */}
      <div className="market-chart-foot">
        {/*
          O RODAPE NAO CONTA QUANDO HA ERRO (11/10/2026)
          ===============================================
          MEDIDO na captura do dono (12:28): o hint dizia `Gráfico indisponível:
          candles ausentes ou inválidos no upstream` e, logo abaixo, o rodape
          dizia `300 candles` — e no M5 `0 candles` com o eixo de horas
          preenchido. Dois lados do mesmo dado discordando (AGENTS.md §5).

          A causa: o hint e a arvore `displayError`, e o rodape e
          `displayCandles.length`. São fontes DIFERENTES — `erroVigente` pode
          devolver '' (sem erro vigente) enquanto a prop trouxe lista vazia, e
          o rodape escrevia `0 candles` ao lado de um eixo que mostrava dados.

          Com erro, o rodape some: o erro ja e a resposta, e uma contagem ao
          lado dele so convida o operador a acreditar na errada. A regra e
          `rotuloRodape`, pura, medida no `PriceChart.regras.test.ts`.
        */}
        {(() => {
          const rotulo = rotuloRodape(displayError, displayCandles.length);
          return rotulo ? <span className="muted mono">{rotulo}</span> : null;
        })()}
      </div>

      {displayCandles.length > 0 && (
        <details className="market-chart-data">
          <summary>Ver dados em tabela</summary>
          <div
            className="table-scroll market-focus-scroll"
            role="region"
            aria-label="Candles em formato tabular"
            tabIndex={0}
          >
            <table className="tbl">
              <caption className="sr-only">Últimos candles reais em formato tabular</caption>
              <thead>
                <tr>
                  <th scope="col">Data</th>
                  <th scope="col">Abertura</th>
                  <th scope="col">Máxima</th>
                  <th scope="col">Mínima</th>
                  <th scope="col">Fechamento</th>
                  <th scope="col">Volume</th>
                </tr>
              </thead>
              <tbody>
                {displayCandles
                  .slice(-20)
                  .reverse()
                  .map((candle) => (
                    <tr key={candle.time}>
                      <td>
                        {/*
                          HORA DO SERVIDOR, NAO DO FUSO DA MAQUINA.
                          O `time` do candle do MT5 e a hora de parede do
                          servidor codificada como epoch. Converter para o fuso
                          da maquina (UTC-3) mostrava 6 h a menos que o MT5
                          nesta conta (servidor UTC+3), e perto da meia-noite
                          trocava o DIA. `timeZone: 'UTC'` reproduz o mesmo
                          carimbo que o eixo do grafico ja desenha.
                        */}
                        {new Date(candle.time * 1000).toLocaleString('pt-BR', {
                          timeZone: 'UTC',
                        })}
                      </td>
                      <td>{candle.open}</td>
                      <td>{candle.high}</td>
                      <td>{candle.low}</td>
                      <td>{candle.close}</td>
                      <td>{candle.volume ?? '—'}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </div>
  );
}
