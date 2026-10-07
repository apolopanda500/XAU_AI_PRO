import { useCallback, useEffect, useRef, useState } from 'react';
import { GraficoIndicador } from './GraficoIndicador';
import QuantumClock from '../QuantumClock';
import SeletorFuso from '../SeletorFuso';
import '../../theme/market.css';
import '../../theme/fuso.css';
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
import {
  getCandles,
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
import BarraFerramentas, { type FerramentaAtiva } from './BarraFerramentas';
import {
  completo,
  desenhoMaisProximo,
  distanciaAteHorizontal,
  distanciaAteTendencia,
  estiloDe,
  moverPonto,
  nivelHorizontal,
  podeMoverPontos,
  pontaMaisProxima,
  pontoDoEvento,
  pontasVisiveis,
  segmentoTendencia,
  PONTOS_POR_FERRAMENTA,
  type Desenho,
  type TipoDesenho,
} from './desenhos';

export const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'] as const;
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
    A ORDEM ARMADA PELO GRAFICO (06/10/2026)
    ========================================
    MEDIDO nas capturas da XM: o clique ARMA a ordem e nao envia. O envio e o
    botao `Colocar ordem a <preco>`, no painel. Sem esta separacao o clique
    seria o caminho de 1-clique que o dono mandou remover.

    `modoOrdem` e o interruptor. Ligado, o clique no grafico vira preco de
    entrada; desligado, o grafico e so leitura, como era.
  */
  modoOrdem?: boolean;
  /** As tres linhas da ordem armada, com o rotulo em dinheiro da XM. */
  ordem?: LinhaOrdem[];
  /** Clique no grafico: arma a ordem no preco clicado. O preco vai cru. */
  onArmarOrdem?: (preco: number) => void;
  /** Soltar uma linha arrastada: o preco vai cru, quem arredonda e o pai. */
  onMoverLinhaOrdem?: (papel: LinhaOrdem['papel'], preco: number) => void;
  /** O `x` da linha: apaga stop ou alvo. `entrada` nao apaga. */
  onRemoverLinha?: (papel: LinhaOrdem['papel']) => void;
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

function defaultMarket(broker: MarketBroker): MarketKind {
  return broker === 'mt5' ? 'forex' : 'crypto-spot';
}

export default function PriceChart({
  symbol = '',
  broker = 'mt5',
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
  onArmarOrdem,
  onMoverLinhaOrdem,
  onRemoverLinha,
}: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'>>(null);
  const linhasRef = useRef<Array<ReturnType<ISeriesApi<'Candlestick'>['createPriceLine']>>>([]);
  const linhasOrdemRef = useRef<Array<ReturnType<ISeriesApi<'Candlestick'>['createPriceLine']>>>([]);
  const emaRef = useRef<Array<ISeriesApi<'Line'>>>([]);
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
  const activeMarket = market ?? defaultMarket(broker);
  const displayCandles = candles ?? loadedCandles;
  const displayError = error || loadedError;
  const latestCandle = displayCandles[displayCandles.length - 1] ?? null;
  /*
    AS FERRAMENTAS DO GRAFICO (06/10/2026)
    ======================================
    MEDIDO nas capturas da XM (`my.xm.com/pt/symbol-info/BTCUSD`, 20:28): a barra
    vertical tem cursor, linha de tendencia, linhas horizontais, Elliot,
    Fibonacci, pincel, texto, previsao, grade, zoom, ima, cadeado, ocultar e
    lixeira. E o menu de contexto da linha de preco oferece
    "Desenhar linha horizontal em 85.376,64" com o atalho `Alt + H`.

    O que entra aqui e o que serve para OPERAR, nesta ordem: cursor, tendencia,
    horizontal e apagar. O resto (Fibonacci, Elliot, texto) entra em seguida e
    nao entra agora pela metade: ferramenta que existe e nao faz o que promete
    e o botao decorativo que o dono reportou.

    `ferramenta` e a MESMA variable que decide se o clique arma ordem. E unica
    de proposito: com a tendencia armada, o primeiro clique seria tambem uma
    ordem — e a linha apareceria sobre uma posicao que ninguem pediu.
  */
  const [ferramenta, setFerramenta] = useState<FerramentaAtiva>('nenhuma');
  const [desenhos, setDesenhos] = useState<Desenho[]>([]);
  const [gradeVertical, setGradeVertical] = useState(false);
  const [gradeHorizontal, setGradeHorizontal] = useState(true);
  const [crosshairMagnetico, setCrosshairMagnetico] = useState(true);
  /*
    O desenho em CONSTRUCAO, separado do salvo.

    Separar porque a linha meio desenhada segue o mouse e some se o operador
    turbar o foco — enquanto as salvas sobrevivem a zoom, deslocamento e troca
    de timeframe. Sem separar, um cancelamento no meio apagaria o desenho errado.
  */
  const [emConstrucao, setEmConstrucao] = useState<Desenho | null>(null);
  const overlayDesenhoRef = useRef<HTMLDivElement>(null);
  const svgDesenhosRef = useRef<SVGSVGElement>(null);
  /*
    `desenhos` num ref, para o callback de zoom.

    O callback de `subscribeVisibleLogicalRangeChange` roda a CADA quadro de
    arraste. Se ele dependesse do `desenhos` do estado, a assinatura seria
    refeita a cada criacao — e a inscricao antiga nunca cancelada, com o
    grafico chamando o callback velho para sempre. O ref da a lista atual sem
    recriar a assinatura.
  */
  const desenhosRef = useRef<Desenho[]>([]);
  desenhosRef.current = desenhos;
  const proximoDesenho = useRef(1);

  /*
    O DESENHO ESCOLHIDO (06/10/2026)
    =================================
    MEDIDO nas capturas da XM (20:35 e 20:36): a paleta, a espessura, a opacidade
    e o cadeado aparecem na barra flutuante SOBRE O DESENHO ESCOLHIDO.

    `id`, e nao o objeto: o objeto muda a cada arraste, e guardar o objeto
    significaria que a selecione se descolaria do desenho assim que ele andasse.
    O `id` acompanha, e o objeto e sempre lido da lista atual.

    Nasce selecionado ao fechar o desenho — o operador acabou de escolher ESTE
    desenho ao clicar nele, e um desenho recem-criado sem paleta aberta e o
    "controle que nada le" do AGENTS.md 9.
  */
  const [selecionadoId, setSelecionadoId] = useState<string | null>(null);
  /*
    HISTORICO DOS DESENHOS, SEPARADO do historico do GRAFICO.

    Sao dois historicos porque desfazer o TIPO DE GRAFICO e desfazer uma LINHA DE
    TENDENCIA sao coisas diferentes, e um historico so faria o `Ctrl + Z` do
    operador desfazer a linha — que e o que ele fez por ultimo — e o botao da
    barra mentindo sobre a sua propria acao. O que fica guardado e a LISTA de
    desenhos, e nao o delta: desfazer e devolver a lista anterior inteira.
  */
  const historicoDesenhosRef = useRef<{ passos: Desenho[][]; refazer: Desenho[][] }>({
    passos: [],
    refazer: [],
  });
  const [passosDesenho, setPassosDesenho] = useState(0);
  const [refaziveisDesenho, setRefaziveisDesenho] = useState(0);
  const [arraste, setArraste] = useState<{ id: string; indice: number } | null>(null);
  /*
    `arraste` no estado e `arrastandoPonta` no ref sao o MESMO arraste, lidos de
    dois lugares, e nao e duplicidade.

    O ref e lido pelo `mousemove`, que roda a CADA pixel: la dentro nao ha
    tempo para o proximo render, e ler o estado daria a lista do render anterior
    — o circulo ficaria um quadro atras do cursor, e o operador veria a ponta
    onde o mouse JA FOI. O estado existe para o JSX saber que ha arraste em
    curso, e `setArraste` no `mouseup` e o que fecha o ciclo.

    O `arraste` do estado nao entra no JSX hoje: o que o operador ve durante o
    arrasto e a propria linha andando. Ele fica porque e o estado do gesto, e um
    gesto sem estado termination e um gesto que o proximo agente vai precisar
    adivinhar.
  */
  const arrastandoPonta = useRef<{ id: string; indice: number } | null>(null);
  /*
    A RAIZ do componente, para o `Ctrl + Z`. E o elemento que o `closest`
    encontra a partir do canvas, e por isso que o atalho funciona depois de um
    clique em qualquer linha: sem ele o ouvinte estaria so no canvas, e o
    `Ctrl + Z` dependeria de onde o clique caiu.
  */
  const raizRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    arrastandoPonta.current = arraste;
  }, [arraste]);

  /** Um passo novo do historico de DESENHOS, e nao do grafico. */
  const registrarPassoDesenho = useCallback((lista: Desenho[]) => {
    const h = historicoDesenhosRef.current;
    historicoDesenhosRef.current = { passos: [...h.passos, lista], refazer: [] };
    setPassosDesenho(historicoDesenhosRef.current.passos.length);
    setRefaziveisDesenho(0);
  }, []);

  /*
    DESFAZER E REFAZER DOS DESENHOS.

    Devolve a LISTA INTEIRA do passo anterior, e nao aplica o delta. A razao e o
    que o `Ctrl + Z` precisa prometer: a tela volta a ser EXATAMENTE como era.
    Com delta, desfazer um arraste devolveria um ponto trocado e deixaria para
    tras o estilo, a selecao e a ordem dos desenhos — e o operador veria um
    desenho parecido, no lugar errado, e marcaria o stop nele.

    `refazer` e guardada a parte. Um `Ctrl + Z` seguido de `Ctrl + Y` tem de
    devolver o desenho, e nao descartar o passo: e o que o operador espera de
    todo editor, e o que torna o `Ctrl + Z` seguro de tentar.
*/
const desfazerDesenho = useCallback(() => {
    const h = historicoDesenhosRef.current;
    const anterior = h.passos[h.passos.length - 1];
    if (!anterior) return;
    historicoDesenhosRef.current = {
      passos: h.passos.slice(0, -1),
      refazer: [...h.refazer, desenhosRef.current],
    };
    setDesenhos(anterior);
    setPassosDesenho(historicoDesenhosRef.current.passos.length);
    setRefaziveisDesenho(historicoDesenhosRef.current.refazer.length);
  }, []);

  const refazerDesenho = useCallback(() => {
    const h = historicoDesenhosRef.current;
    const proxima = h.refazer[h.refazer.length - 1];
    if (!proxima) return;
    historicoDesenhosRef.current = {
      passos: [...h.passos, desenhosRef.current],
      refazer: h.refazer.slice(0, -1),
    };
    setDesenhos(proxima);
    setPassosDesenho(historicoDesenhosRef.current.passos.length);
    setRefaziveisDesenho(historicoDesenhosRef.current.refazer.length);
  }, []);

  const selecionado = desenhos.find((d) => d.id === selecionadoId) ?? null;
  const estiloSelecionado = selecionado
    ? estiloDe(selecionado)
    : { cor: '#4f7cff', opacidade: 1, espessura: 2, travado: false };

  /** Troca o estilo do desenho escolhido, e registra o passo para desfazer. */
  const mudarEstilo = useCallback(
    (muda: (e: ReturnType<typeof estiloDe>) => ReturnType<typeof estiloDe>) => {
      if (!selecionadoId) return;
      const listaAntes = desenhosRef.current;
      const proxima = listaAntes.map((d) => {
        if (d.id !== selecionadoId) return d;
        const novo = muda(estiloDe(d));
        return { ...d, estilo: novo };
      });
      registrarPassoDesenho(listaAntes);
      setDesenhos(proxima);
    },
    [selecionadoId, registrarPassoDesenho],
  );

  /*
    OS CONVERSORES, no corpo do componente e nao dentro do efeito.

    A camada de desenho precisa deles no RENDER, para saber onde cada linha
    esta a cada quadro. Dentro do efeito eles nao chegariam no JSX, e o desenho
    sairia preso na posicao do primeiro quadro — o mesmo defeito de guardar
    pixel, so que escondido.

    Todos devolvem `null` quando o grafico nao responde. `null` e "nao medido":
    a linha some da tela, que e o correto. Nunca vira 0, que colocaria a linha
    no topo do grafico parecendo valida.
  */
  const converter = {
    precoParaY: (p: number): number | null => {
      try {
        const y = seriesRef.current?.priceToCoordinate(p);
        return typeof y === 'number' && Number.isFinite(y) ? y : null;
      } catch {
        return null;
      }
    },
    tempoParaX: (t: number): number | null => {
      try {
        const x = chartRef.current?.timeScale().timeToCoordinate(t as UTCTimestamp);
        return typeof x === 'number' && Number.isFinite(x) ? x : null;
      } catch {
        return null;
      }
    },
  };

  /*
    OS DESENHOS ACOMPANHAM O ZOOM E O DESLOCAMENTO (06/10/2026)
    ==========================================================
    MEDIDO nas capturas da XM (20:31 e 20:33): com tres horizontais, uma verde,
    uma vermelha e duas diagonais desenhadas, todas ficam ancoradas ao PRECO e
    andam junto quando o operador amplia ou desloca. Os rotulos `86.712,20`,
    `85.718,63`, `85.609,18` e `84.704,79` continuam nos mesmos niveis.

    ESTE E O PONTO QUE FAZ O GRAFICO SER "LIVRE".

    Sem esta assinatura, o desenho fica preso no PIXEL: o React so re-renderiza
    quando o estado muda, e zoom/deslocamento mudam o estado do GRAFICO, nao o
    do componente. A linha ficaria parada enquanto os candles andam — e isso
    e pior que nao ter linha, porque a linha parece confiavel e esta errada.

    Por que o DOM e mexido DIRETO e nao por `setState`: um re-render por quadro
    de arraste comCandles seria caro, e o grafico precisa ficar macico. O
    `subscribeVisibleLogicalRangeChange` entrega o novo visivel, e aqui se
    reescreve so o atributo `x1/y1/x2/y2` dos SVG. O React redesenha no
    proximo render de verdade (criar, apagar, trocar de timeframe).
  */
  useEffect(() => {
    const ts = chartRef.current?.timeScale();
    const svg = svgDesenhosRef.current;
    if (!ts || !svg) return undefined;

    const repintar = () => {
      const selecao = svg.querySelectorAll<SVGLineElement>('line[data-desenho]');
      selecao.forEach((no) => {
        const id = no.dataset.desenho;
        const tipo = no.dataset.tipo;
        const d = desenhosRef.current.find((x) => x.id === id);
        if (!d) return;
        if (tipo === 'tendencia') {
          const s = segmentoTendencia(d, converter.tempoParaX, converter.precoParaY);
          if (!s) {
            no.setAttribute('x1', '-9999');
            no.setAttribute('y1', '-9999');
            no.setAttribute('x2', '-9999');
            no.setAttribute('y2', '-9999');
            return;
          }
          no.setAttribute('x1', String(s.x1));
          no.setAttribute('y1', String(s.y1));
          no.setAttribute('x2', String(s.x2));
          no.setAttribute('y2', String(s.y2));
        } else {
          const y = nivelHorizontal(d, converter.precoParaY);
          const py = y === null ? '-9999' : String(y);
          no.setAttribute('y1', py);
          no.setAttribute('y2', py);
        }
      });
      // Os ROTULOS de preco andam com a linha. Um rotulo parado no eixo, com a
      // linha longe dele, e o operador lendo o preco errado.
      svg.querySelectorAll<SVGTextElement>('text[data-desenho]').forEach((no) => {
        const d = desenhosRef.current.find((x) => x.id === no.dataset.desenho);
        if (!d || d.tipo !== 'horizontal') return;
        const y = nivelHorizontal(d, converter.precoParaY);
        if (y !== null) no.setAttribute('y', String(y - 5));
      });
      /*
        AS PONTAS andam com a MESMA assinatura da linha, e pelo mesmo motivo.

        Se a linha andasse e o circulo ficasse, o operador veria a ponta onde o
        mouse esta e a linha em outro lugar — e moveria a linha ERRADA achando
        que arrastou a que queria. E a linha existe para marcar o stop: um
        `mousedown` na ponta errada marca o nivel errado com toda a aparencia de
        estar certo.
      */
      svg.querySelectorAll<SVGCircleElement>('circle[data-ponta]').forEach((no) => {
        const d = desenhosRef.current.find((x) => x.id === no.dataset.desenho);
        if (!d) return;
        const indice = Number(no.dataset.indice);
        const ponto = d.pontos[indice];
        if (!ponto) return;
        const x = converter.tempoParaX(ponto.time);
        const y = converter.precoParaY(ponto.preco);
        no.setAttribute('cx', x === null ? '-9999' : String(x));
        no.setAttribute('cy', y === null ? '-9999' : String(y));
      });
    };

    ts.subscribeVisibleLogicalRangeChange(repintar);
    repintar();
    return () => {
      try {
        ts.unsubscribeVisibleLogicalRangeChange(repintar);
      } catch {
        /* grafico desmontado */
      }
    };
  }, [chartReady, tipoGrafico, seriesAtivo]);

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
        mode: CrosshairMode.Magnet,
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
        ? new ResizeObserver(() =>
            chart.applyOptions({ width: containerRef.current?.clientWidth ?? 0 }),
          )
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
    const controller = new AbortController();
    let active = true;
    const load = async () => {
      try {
        const result = await getCandles(
          { broker, market: activeMarket, symbol: symbol.toUpperCase() },
          activeTimeframe,
          300,
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
  }, [chartReady, displayCandles, markers, lines, emaExterno, tipoGrafico, seriesAtivo]);

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
      const p = yParaPreco(clientY);
      if (p === null) return null;
      let melhor: typeof alvo & { dist: number } | null = null;
      for (const l of moveis) {
        const dist = Math.abs(l.price - p);
        const tol = Math.max(Math.abs(p) * 0.002, 0.01);
        if (dist <= tol && (!melhor || dist < melhor.dist)) melhor = { ticket: l.ticket, kind: l.kind, dist };
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
      const p = yParaPreco(e.clientY);
      if (p !== null) onMoveLine(final.ticket, final.kind, Math.round(p * 100) / 100);
    };
    const aoPressionar = (e: MouseEvent) => {
      const achou = perto(e.clientY);
      if (achou) {
        alvo = { ticket: achou.ticket, kind: achou.kind };
        const atual = moveis.find((l) => l.ticket === achou.ticket && l.kind === achou.kind);
        precoSessao = atual ? atual.price : 0;
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

    const raiz = raizRef.current ?? el;
    const yParaPreco = (clientY: number): number | null => {
      const rect = el.getBoundingClientRect();
      try {
        const p = series.coordinateToPrice(clientY - rect.top);
        return typeof p === 'number' && Number.isFinite(p) ? p : null;
      } catch {
        return null;
      }
    };
    /*
      AS CONVERSÕES DO DESENHO (06/10/2026)
      =====================================
      O desenho guarda `time` e `preco` — as coordenadas da CORRETORA — e nao
      pixel. E o que faz a linha de tendencia continuar sendo a MESMA linha
      depois de zoom, deslocamento ou troca de timeframe: sao estas quatro
      funcoes que a redesenham onde ela deve estar.

      `null` quando o grafico nao responde (fora da area visivel). Ponto sem
      coordenada NAO vira posicao inventada: some da tela, que e o correto.
    */
    const xParaTempo = (clientX: number): number | null => {
      const rect = el.getBoundingClientRect();
      try {
        const t = chartRef.current?.timeScale().coordinateToTime(clientX - rect.left);
        return typeof t === 'number' && Number.isFinite(t) ? t : null;
      } catch {
        return null;
      }
    };
    const tempoParaX = (t: number): number | null => {
      try {
        const x = chartRef.current?.timeScale().timeToCoordinate(t as UTCTimestamp);
        return typeof x === 'number' && Number.isFinite(x) ? x : null;
      } catch {
        return null;
      }
    };
    const precoParaY = (p: number): number | null => {
      try {
        const y = series.priceToCoordinate(p);
        return typeof y === 'number' && Number.isFinite(y) ? y : null;
      } catch {
        return null;
      }
    };
    /** A linha de ordem mais proxima do cursor, para o arraste. */
    const perto = (clientY: number) => {
      const p = yParaPreco(clientY);
      if (p === null) return null;
      let melhor: { papel: LinhaOrdem['papel']; linha: LinhaOrdem; dist: number } | null = null;
      for (const l of removeis) {
        const dist = Math.abs(l.preco - p);
        const tol = Math.max(Math.abs(p) * 0.002, 0.01);
        if (dist <= tol && (!melhor || dist < melhor.dist)) melhor = { papel: l.papel, linha: l, dist };
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
      /*
        A PONTA tem prioridade sobre a linha de ordem, e a ordem de leitura e o
        que decide: com as duas debaixo do cursor, o que o operador mirou e o
        que ele VE em cima — e a ponta e desenhada sobre a linha.
      */
      if (arrastandoPonta.current) {
        const { id, indice } = arrastandoPonta.current;
        const d = desenhosRef.current.find((x) => x.id === id);
        if (!d) return;
        const ponto = pontoDoEvento(e.clientX, e.clientY, xParaTempo, (y) => yParaPreco(y));
        const movido = moverPonto(d, indice, ponto);
        if (!movido) return;
        /*
          IMMUTAVEL e de proposito: `moverPonto` devolve um objeto novo. Mutar o
          desenho no lugar faria o React nao ver mudanca, e a linha andaria no
          estado mas ficaria parada na tela — o botao que funciona e nada
          acontece, que e o defeito do botao EMA.
        */
        setDesenhos(desenhosRef.current.map((x) => (x.id === id ? movido : x)));
        return;
      }
      if (!alvo) {
        el.style.cursor = perto(e.clientY) ? 'ns-resize' : '';
        return;
      }
      const p = yParaPreco(e.clientY);
      if (p === null) return;
      precoSessao = p;
      if (!frame) frame = window.requestAnimationFrame(redesenhar);
    };
    const aoSoltar = (e: MouseEvent) => {
      if (arrastandoPonta.current) {
        arrastandoPonta.current = null;
        setArraste(null);
        el.style.cursor = '';
        return;
      }
      if (!alvo) return;
      const papel = alvo.papel;
      alvo = null;
      el.style.cursor = '';
      if (frame) {
        window.cancelAnimationFrame(frame);
        frame = 0;
      }
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
        FERRAMENTA ARMADA TEM PRIORIDADE SOBRE A ORDEM (06/10/2026)

        Com a tendencia armada, o primeiro clique e o primeiro PONTO da linha.
        Sem esta guarda ele seria tambem o clique que arma a ordem — e o
        operador teria uma posicao que nao pediu, aberta no preco do primeiro
        ponto de uma linha de tendencia. E o caminho de 1-clique que o dono
        mandou remover, voltando por outra porta.
      */
      if (ferramenta === 'tendencia' || ferramenta === 'horizontal') {
        const ponto = pontoDoEvento(
          e.clientX, e.clientY, xParaTempo, (y) => yParaPreco(y),
        );
        if (!ponto) return;
        const tipo: TipoDesenho = ferramenta;
        const precisa = PONTOS_POR_FERRAMENTA[tipo];
        setEmConstrucao((atual) => {
          const pontos = atual && atual.tipo === tipo ? [...atual.pontos, ponto] : [ponto];
          if (pontos.length >= precisa) {
            // Fecha o desenho e volta ao cursor: o operador quer voltar a olhar
            // o grafico, nao ficar preso na ferramenta.
            const id = `d${proximoDesenho.current}`;
            proximoDesenho.current += 1;
            /*
              O PASSO DE DESFAZER e registrado ANTES de mudar a lista, e guarda a
              lista ANTERIOR — e nao a nova.

              E a razao de `desfazer` devolver a lista antiga inteira em vez de
              aplicar o delta: um delta de criacao desfaria apagando o desenho,
              e um delta de arraste desfaria trocando um ponto. Guardar a lista
              anterior e o unico jeito de o `Ctrl + Z` devolver EXATAMENTE o que
              a tela mostrava antes — inclusive o estilo, que o delta nao
              carregaria.
            */
            registrarPassoDesenho(desenhosRef.current);
            setDesenhos([...desenhosRef.current, { id, tipo, pontos }]);
            /*
              NASCE SELECIONADO. O operador acabou de escolher ESTE desenho ao
              clicar nos dois pontos dele; sem isso a paleta, a espessura, a
              opacidade e a tranca ficariam fora da tela ate ele clicar na
              linha de novo — e o desenho recem-criado sem nenhum controle e
              exatamente o "controle que nada le" do AGENTS.md 9.
            */
            setSelecionadoId(id);
            setEmConstrucao(null);
            setFerramenta('nenhuma');
            return null;
          }
          const id = atual && atual.tipo === tipo ? atual.id : `d${proximoDesenho.current}`;
          if (!atual || atual.tipo !== tipo) proximoDesenho.current += 1;
          return { id, tipo, pontos };
        });
        return;
      }
      if (ferramenta === 'apagar') {
        const rect = el.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const alvo = desenhoMaisProximo(
          desenhos, x, y, 8,
          (d) => {
            if (d.tipo === 'tendencia') {
              const s = segmentoTendencia(d, tempoParaX, precoParaY);
              return s ? distanciaAteTendencia(x, y, s) : null;
            }
            const n = nivelHorizontal(d, precoParaY);
            return n === null ? null : distanciaAteHorizontal(y, n);
          },
        );
        if (alvo) {
        registrarPassoDesenho(desenhosRef.current);
        setDesenhos(desenhosRef.current.filter((d) => d.id !== alvo.id));
        if (selecionadoId === alvo.id) setSelecionadoId(null);
      }
        return;
      }
      /*
        CLIQUE SOBRE UM DESENHO O ESCOLHE (06/10/2026).

        MEDIDO nas capturas da XM (20:35): a paleta, a espessura e o cadeado
        aparecem sobre o desenho escolhido. Sem este clique o operador teria
        duas formas de escolher — a paleta flutuante e o `apagar` — e nenhuma
        delas escolheria um desenho para ESTILIZAR.

        Por que `perto(e.clientY)` vem ANTES: clicar numa linha de ordem com a
        ferramenta de apagar armada tem que apagar a linha de ordem. E o que o
        operador mirou e o que ele ve em cima.
      */
      if (perto(e.clientY)) return;
      {
        const rect = el.getBoundingClientRect();
        const alvoDesenho = desenhoMaisProximo(
          desenhosRef.current,
          e.clientX - rect.left,
          e.clientY - rect.top,
          8,
          (d) => {
            if (d.tipo === 'tendencia') {
              const s = segmentoTendencia(d, tempoParaX, precoParaY);
              return s ? distanciaAteTendencia(e.clientX - rect.left, e.clientY - rect.top, s) : null;
            }
            const n = nivelHorizontal(d, precoParaY);
            return n === null ? null : distanciaAteHorizontal(e.clientY - rect.top, n);
          },
        );
        setSelecionadoId(alvoDesenho ? alvoDesenho.id : null);
      }
      /*
        A ORDEM SO ARMA EM `modoOrdem`.

        Removi o `return` antecipado de `!modoOrdem` que existia antes: ele
        impedia o grafico de ESCOLHER um desenho e de ARRASTAR uma ponta fora do
        modo de ordem, e essas duas gestures servem justamente quando o
        operador esta so olhando. Mas sem ele o `onArmarOrdem` passaria a ser
        chamado sempre, e abrir uma ordem nao pedida ao clicar no grafico e
        exatamente o caminho de 1-clique que o dono mandou remover.

        Por isso o guarda e AQUI, no ultimo passo, e nao no comeco do efeito: o
        clique primeiro escolhe desenho, e so o que sobra disso vira ordem.
      */
      if (!modoOrdem) return;
      const p = yParaPreco(e.clientY);
      if (p !== null && p > 0 && ferramenta === 'nenhuma') onArmarOrdem?.(p);
    };
    /*
      O ARRASTE DA PONTA (06/10/2026)
      ================================
      MEDIDO nas capturas da XM (20:31 e 20:35): a linha de tendencia tem dois
      circulos nas pontas, e arrastar um deles move a linha. Sem isso a linha
      existe mas nao serve para AJUSTAR O STOP — que e o uso que o dono descreveu.

      O guarda `podeMoverPontos` e AQUI, e nao so no desenho do circulo: sem ele
      o circulo sumiria com a tranca fechada e o `mousedown` continuaria pegando.
      O operador veria o cadeado FECHADO e a linha andando, e marcaria o stop
      num nivel que ele nao escolheu.
    */
    const aoPressionar = (e: MouseEvent) => {
      const rect = el.getBoundingClientRect();
      const px = e.clientX - rect.left;
      const py = e.clientY - rect.top;
      const pegou = pontaMaisProxima(
        desenhosRef.current.filter((d) => podeMoverPontos(d)),
        px,
        py,
        12,
        tempoParaX,
        precoParaY,
      );
      if (pegou) {
        /*
          O PASSO e registrado no `mousedown`, e nao no `mouseup`, para que o
          arrasto INTEIRO seja um passo so. Registrar no `mouseup` guardaria a
          lista ja movida, e o `Ctrl + Z` devolveria o desenho no lugar novo —
          parecendo nao fazer nada.
        */
        registrarPassoDesenho(desenhosRef.current);
        arrastandoPonta.current = { id: pegou.desenho.id, indice: pegou.indice };
        setArraste(arrastandoPonta.current);
        setSelecionadoId(pegou.desenho.id);
        el.style.cursor = 'grabbing';
        e.preventDefault();
        return;
      }
      const achou = perto(e.clientY);
      if (achou) {
        alvo = { papel: achou.papel, linha: achou.linha };
        precoSessao = achou.linha.preco;
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
    /*
      `Ctrl + Z` e `Ctrl + Y` (06/10/2026), MEDIDO na captura da XM de 20:37.

      Acionados por `key` E nao por `keyCode`: `keyCode` e um numero legado que
      o navegador mantem so por compatibilidade, e `Ctrl + Z` em teclado
      internacional pode nao estar na tecla fisica `Z`. `e.key` e o que o
      operador digitou.
    */
    const aoTecla = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey)) return;
      const tecla = e.key.toLowerCase();
      if (tecla === 'z' && !e.shiftKey) {
        e.preventDefault();
        desfazerDesenho();
      } else if (tecla === 'y' || (tecla === 'z' && e.shiftKey)) {
        e.preventDefault();
        refazerDesenho();
      }
    };
    el.addEventListener('mousedown', aoPressionar);
    el.addEventListener('click', aoClicar);
    overlay?.addEventListener('click', aoApagar);
    window.addEventListener('mousemove', aoMover);
    window.addEventListener('mouseup', aoSoltar);
    /*
      `keydown` na RAIZ do componente, e nao em `window`: um `Ctrl + Z` global
      desfaria desenho mesmo com o foco num campo onde o operador esta
      digitando o nivel do stop — e o `Ctrl + Z` de um campo de texto e
      DESFAZER O TEXTO, nao a linha.

      E na raiz, e nao no canvas, porque o operador nao clica no canvas para
      desfazer: ele clica numa linha, o foco sobe para o elemento do evento, e
      o `Ctrl + Z` tem de funcionar em qualquer ponto do grafico. Ouvir so no
      canvas faria o atalho depender de onde o clique caiu — e um atalho que
      as vezes funciona e o tipo de coisa que o operador aprende a nao usar.
    */
    raiz.addEventListener('keydown', aoTecla);
    return () => {
      raiz.removeEventListener('keydown', aoTecla);
      el.removeEventListener('mousedown', aoPressionar);
      el.removeEventListener('click', aoClicar);
      overlay?.removeEventListener('click', aoApagar);
      window.removeEventListener('mousemove', aoMover);
      window.removeEventListener('mouseup', aoSoltar);
      el.style.cursor = '';
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, [chartReady, ordem, modoOrdem, onArmarOrdem, onMoverLinhaOrdem, onRemoverLinha, tipoGrafico, seriesAtivo]);

  const changeTimeframe = (next: ChartTimeframe) => {
    if (onTimeframeChange) onTimeframeChange(next);
    else setInternalTimeframe(next);
  };

  return (
    <div ref={raizRef} className="card compact-card price-chart" aria-busy={loading}>
      <div className="section-head">
        <div>
          <h2>{symbol || 'Selecione um ativo'}</h2>
          <span className="muted">
            Candles OHLC reais · {sourceLabel ?? `${broker.toUpperCase()} · ${activeMarket}`}
          </span>
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
        <div className="btn-row" role="group" aria-label="Indicadores do gráfico">
          <button
            type="button"
            className={`btn sm ${emaExterno ? 'primary' : 'ghost'}`}
            aria-pressed={emaExterno}
            onClick={() => setEma(!emaExterno)}
            title="Media movel exponencial, calculada dos candles exibidos"
          >
            EMA
          </button>
          <button
            type="button"
            className={`btn sm ${rsiExterno ? 'primary' : 'ghost'}`}
            aria-pressed={rsiExterno}
            onClick={() => setRsi(!rsiExterno)}
            title="RSI de Wilder (14), dos candles exibidos"
          >
            RSI
          </button>
          <button
            type="button"
            className={`btn sm ${macdExterno ? 'primary' : 'ghost'}`}
            aria-pressed={macdExterno}
            onClick={() => setMacd(!macdExterno)}
            title="MACD (12, 26, 9), dos candles exibidos"
          >
            MACD
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
      {displayError && (
        <div className="hint" role="alert">
          Gráfico indisponível: {displayError}
        </div>
      )}
      {loading && !displayCandles.length && (
        <div className="hint" role="status">
          Carregando candles…
        </div>
      )}
      {!displayCandles.length && !loading && !displayError && (
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
      )}
      <p id="price-chart-summary" className="sr-only">
        {chartSummary}
      </p>
      <BarraFerramentas
        ferramenta={ferramenta}
        gradeVertical={gradeVertical}
        gradeHorizontal={gradeHorizontal}
        crosshairMagnetico={crosshairMagnetico}
        quantosDesenhos={desenhos.length}
        aoEscolher={setFerramenta}
        aoAlternarGrade={(eixo) => {
          if (eixo === 'vertical') setGradeVertical((v) => !v);
          else setGradeHorizontal((v) => !v);
        }}
        aoAlternarCrosshair={() => setCrosshairMagnetico((v) => !v)}
        aoZoom={(dir) => {
          const ts = chartRef.current?.timeScale();
          if (!ts) return;
          if (dir === 0) {
            ts.fitContent();
            return;
          }
          try {
            const atual = ts.options().barSpacing;
            // Zoom e MULTIPLICATIVO, e a escala e o que o olho aceita. Um
            // `+` fixo seria 2 barras a mais em qualquer zoom, e no fim da
            // escala o grafico deixaria de caber.
            const alvo = Math.max(0.5, Math.min(400, atual * (dir > 0 ? 1.25 : 0.8)));
            ts.applyOptions({ barSpacing: alvo });
          } catch {
            /* sem serie visivel */
          }
        }}
        aoLimparDesenhos={() => {
          // Registrar o passo ANTES de limpar: sem isso, um `Ctrl + Z` depois de
          // limpar nao devolveria os desenhos, e "limpei sem querer" seria
          // irreversivel — que e o pior defeito que uma ferramenta de desenho
          // pode ter.
          registrarPassoDesenho(desenhosRef.current);
          setDesenhos([]);
          setSelecionadoId(null);
        }}
        selecionado={selecionado !== null}
        estiloSelecionado={estiloSelecionado}
        podeDesfazer={passosDesenho > 0}
        podeRefazer={refaziveisDesenho > 0}
        aoDesfazer={desfazerDesenho}
        aoRefazer={refazerDesenho}
        aoMudarCor={(cor) => mudarEstilo((e) => ({ ...e, cor }))}
        aoMudarEspessura={(espessura) => mudarEstilo((e) => ({ ...e, espessura }))}
        aoMudarOpacidade={(opacidade) => mudarEstilo((e) => ({ ...e, opacidade }))}
        aoAlternarTrava={() => mudarEstilo((e) => ({ ...e, travado: !e.travado }))}
      />
      {/*
        A CAMADA DOS DESENHOS.

        `pointer-events: none` no container e `auto` so nos PEGADINHOS: sem isso
        a camada invisivel capturaria o crosshair, o arraste das linhas de
        ordem e o clique que arma a ordem — exatamente os tres gestos que o
        operador precisa.

        As coordenadas sao lidas do proprio grafico a cada desenho. Um desenho
        guardado em PIXEL gruda na tela e sai de lugar no primeiro zoom, e o
        operador deixa de confiar na linha — que e o que faz uma linha de
        tendencia servir para alguma coisa.
      */}
      {ferramenta !== 'nenhuma' && (
        <p className="hint price-chart-dica" role="status">
          {ferramenta === 'tendencia'
            ? 'Linha de tendência: clique em dois pontos.'
            : ferramenta === 'horizontal'
              ? 'Linha horizontal: clique em um ponto.'
              : 'Clique sobre a linha para apagar.'}
        </p>
      )}
      {/*
          A CAMADA DOS DESENHOS: SVG sobre o canvas.

          As coordenadas sao lidas do grafico a cada render. Um desenho guardado
          em PIXEL gruda na tela e sai de lugar no primeiro zoom — e o operador
          deixa de confiar na linha, que e o que faz uma linha de tendencia
          servir para alguma coisa.

          `pointer-events: none` no SVG: a camada nao pode capturar o crosshair,
          o arraste das linhas de ordem nem o clique que arma a ordem. Sao os
          tres gestos que o operador precisa, e um retangulo invisivel por
          cima de todos eles seria o grafico quebrado de um jeito novo.
        */}
        {(desenhos.length > 0 || emConstrucao) && (
          <svg
            ref={svgDesenhosRef}
            className="price-chart-desenhos"
            aria-hidden="true"
          >
            {desenhos.map((d) => {
              /*
                O ESTILO E LIDO DO DESENHO, e nao de um padrao da barra.

                MEDIDO na XM (20:35): a paleta e a espessura sao do desenho
                escolhido. Um estilo global obrigaria o operador a redesenhar a
                linha para trocar a cor — e a linha existe para marcar o stop.
                Perder o ponto marcado para mudar a cor e o oposto do que a
                ferramenta serve.
              */
              const estilo = estiloDe(d);
              if (d.tipo === 'tendencia') {
                const s = segmentoTendencia(d, converter.tempoParaX, converter.precoParaY);
                if (!s) return null;
                return (
                  <g key={d.id}>
                    <line
                      data-desenho={d.id}
                      data-tipo="tendencia"
                      x1={s.x1}
                      y1={s.y1}
                      x2={s.x2}
                      y2={s.y2}
                      stroke={estilo.cor}
                      strokeWidth={estilo.espessura}
                      strokeLinecap="round"
                      opacity={estilo.opacidade}
                    />
                    {/*
                      AS PONTAS ARRASTAVEIS. MEDIDO na XM (20:31 e 20:35): dois
                      circulos nas pontas da tendencia, um na horizontal, e
                      arrastar move a linha.

                      `data-ponta` com o `indice` do ponto: e o que o
                      `mousemove` le para saber QUAL ponto mover, sem guardar
                      pixel em lugar nenhum. E `aria-hidden` no SVG inteiro,
                      entao a ponta nao aparece para leitor de tela — o controle
                      equivalente e o `Desfazer`, que o teste mede.
                    */}
                    {pontasVisiveis(d, converter.tempoParaX, converter.precoParaY).map((p) => (
                      <circle
                        key={`${d.id}-${p.indice}`}
                        data-ponta="1"
                        data-desenho={d.id}
                        data-indice={p.indice}
                        cx={p.x}
                        cy={p.y}
                        r={5}
                        fill="none"
                        stroke={estilo.cor}
                        strokeWidth={2}
                        opacity={estilo.opacidade}
                      />
                    ))}
                  </g>
                );
              }
              const y = nivelHorizontal(d, converter.precoParaY);
              if (y === null) return null;
              return (
                <g key={d.id}>
                  <line data-desenho={d.id} data-tipo="horizontal" x1={0} y1={y} x2="100%" y2={y} stroke={estilo.cor} strokeWidth={estilo.espessura} strokeDasharray="6 4" opacity={estilo.opacidade} />
                  <text data-desenho={d.id} x={6} y={y - 5} fill={estilo.cor} fontSize={11} className="mono" opacity={estilo.opacidade}>
                    {d.pontos[0].preco.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </text>
                  {pontasVisiveis(d, converter.tempoParaX, converter.precoParaY).map((p) => (
                    <circle
                      key={`${d.id}-${p.indice}`}
                      data-ponta="1"
                      data-desenho={d.id}
                      data-indice={p.indice}
                      cx={p.x}
                      cy={p.y}
                      r={5}
                      fill="none"
                      stroke={estilo.cor}
                      strokeWidth={2}
                      opacity={estilo.opacidade}
                    />
                  ))}
                </g>
              );
            })}
            {emConstrucao && emConstrucao.tipo === 'tendencia' && emConstrucao.pontos.length === 1 && (
              <circle
                cx={converter.tempoParaX(emConstrucao.pontos[0].time) ?? -9999}
                cy={converter.precoParaY(emConstrucao.pontos[0].preco) ?? -9999}
                r={4}
                fill="none"
                stroke="#4f7cff"
                strokeWidth={2}
              />
            )}
            {emConstrucao && emConstrucao.tipo === 'horizontal' && (
              <line
                x1={0}
                y1={nivelHorizontal(emConstrucao, converter.precoParaY) ?? -9999}
                x2="100%"
                y2={nivelHorizontal(emConstrucao, converter.precoParaY) ?? -9999}
                stroke="#f0b90b"
                strokeWidth={1.5}
                strokeDasharray="6 4"
              />
            )}
          </svg>
        )}
        {/*
          O CONTAINER: canvas do grafico + a camada dos `x` + os desenhos.

        O `div` do grafico vira `position: relative` (via `.market-chart-canvas`)
        e a camada do `x` fica por cima, sem capturar ponteiro — senao ela
        transparenta o crosshair, o arraste e o clique que arma a ordem.
      */}
      <div className="market-chart-wrap">
        <div
          ref={containerRef}
          className="market-chart-canvas"
          style={{ height }}
          aria-label={`Gráfico de candles de ${symbol || 'ativo'}`}
          aria-describedby="price-chart-summary"
          role="img"
          tabIndex={0}
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
          Clique no gráfico para armar a ordem no preço escolhido. O clique arma; o envio é
          o botão do painel.
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
        <span className="muted mono">
          {displayCandles.length} candles
        </span>
        <div className="market-chart-foot-right">
          <QuantumClock compact />
          <SeletorFuso />
        </div>
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
                      <td>{new Date(candle.time * 1000).toLocaleString('pt-BR')}</td>
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
