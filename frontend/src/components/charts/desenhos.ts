/**
  OS DESENHOS DO GRAFICO (06/10/2026)
  ===================================
  Linha de tendencia e linha horizontal, como nas plataformas.

  POR QUE ESTE MODULO E SO LOGICA
  ===============================
  O desenho e uma conta de conversao: o evento do mouse chega em PIXEL, e a
  linha precisa sobreviver a zoom e deslocamento. Guardar pixel faria a linha
  grudar na tela e sair de lugar no primeiro zoom — e o operador deixaria de
  confiar nela, que e o que faz uma linha de tendencia ser usada.

  Guardar `tempo` e `preco` e o que resolve: sao as coordenadas que a
  corretora usa, e `timeToCoordinate`/`priceToCoordinate` as redesenham onde
  elas devem estar a cada quadro. A linha continua sendo a MESMA linha depois
  de zoom, deslocamento ou troca de timeframe.

  O AGENTS.md 5 aparece aqui de novo: `coordinateToTime` pode devolver `null`
  (fora da area visivel) e `priceToCoordinate` tambem. O desenho que some da
  tela e esperado; o que e PROIBIDO e o app inventar a posicao de um ponto que
  nao deu para medir. Aqui ponto sem coordenada devolve `null` e a camada nao
  desenha — nunca um numero inventado.
*/

export type TipoDesenho = 'tendencia' | 'horizontal';

/** Um ponto do desenho, em coordenadas da CORRETORA, nao da tela. */
export type PontoDesenho = { time: number; preco: number };

/**
  * O ESTILO DO DESENHO, guardado JUNTO do desenho e nao global na barra.
  *
  * MEDIDO nas capturas da XM (20:35): a espessura `2 px`, a paleta e o
  * arrastar das pontas sao do DESENHO SELECIONADO, nao do proximo a nascer. Uma
  * cor global obrigaria o operador a redesenhar a linha para trocar a cor, e a
  * linha existe para marcar o stop — redesenhar e perder o ponto marcado.
  *
  * Por isso `estilo` e opcional: um `Desenho` gravado antes desta mudanca (ou
  * montado por teste) continua valendo e recebe o padrao. Nao e obrigatoriedade
  * de migrar dado: e o preco de nao quebrar o que ja funciona.
  */
export type EstiloDesenho = {
  cor: string;
  opacidade: number;
  espessura: number;
  travado: boolean;
};

export type Desenho = {
  id: string;
  tipo: TipoDesenho;
  pontos: PontoDesenho[];
  estilo?: Partial<EstiloDesenho>;
};

/**
  * A PALETA, no tamanho que a XM mostra (grade 8x10 + variantes).
  *
  * Sao cores literais de tela, nao nomes: `chart.applyOptions` e SVG aceitam
  * hexadecimal, e um nome como `red` seria resolvido pelo navegador em um lugar
  * e nao no outro. Nenhuma delas e usada como rotulo de mercado.
  */
export const PALETA: readonly string[] = [
  '#4f7cff', '#2ecc71', '#e74c3c', '#f0b90b',
  '#9b59b6', '#00bcd4', '#ff9800', '#607d8b',
  '#1abc9c', '#8e44ad', '#e91e63', '#795548',
  '#ff5722', '#ffc107', '#cddc39', '#00bfa5',
] as const;

/** As espessuras que a XM oferece: 1 px a 4 px. */
export const ESPESSURAS: readonly number[] = [1, 2, 3, 4] as const;

/**
  * O estilo EFETIVO de um desenho, com o padrao preenchido.
  *
  * Devolve sempre um objeto completo para o render nunca ler `cor` de um
  * `undefined` — e o SVG com `stroke` vazio desenharia a linha preta do
  * navegador, que parece uma linha de verdade.
  */
export function estiloDe(desenho: Desenho): EstiloDesenho {
  const e = desenho.estilo ?? {};
  return {
    cor: e.cor ?? PALETA[0],
    opacidade: e.opacidade ?? 1,
    espessura: e.espessura ?? 2,
    travado: e.travado ?? false,
  };
}

/**
  * Opacidade valida.
  *
  * `opacidade` vai direto no atributo `opacity` do SVG. Um valor fora de 0..1
  * e IGNORADO pelo navegador: a linha apareceria com a opacidade anterior e o
  * operador repetiria o clique achando que o controle nao funciona. Aqui o
  * valor e RECUSADO no lugar, e o `Number.isFinite` cobre `NaN` — que passaria
  * por qualquer comparacao `<` ou `>` e viraria atributo invalido.
  */
export function normalizarOpacidade(valor: number): number | null {
  if (!Number.isFinite(valor)) return null;
  if (valor < 0 || valor > 1) return null;
  return valor;
}

/** Espessura valida: inteiro de 1 a 4, como a XM oferece. */
export function normalizarEspessura(valor: number): number | null {
  if (!Number.isFinite(valor)) return null;
  if (!Number.isInteger(valor)) return null;
  if (!ESPESSURAS.includes(valor)) return null;
  return valor;
}

/** Quantos pontos cada ferramenta precisa para fechar o desenho. */
export const PONTOS_POR_FERRAMENTA: Record<TipoDesenho, number> = {
  tendencia: 2,
  horizontal: 1,
};

/** O desenho esta pronto? Nao e enquanto faltarem pontos. */
export function completo(desenho: Desenho): boolean {
  return desenho.pontos.length >= PONTOS_POR_FERRAMENTA[desenho.tipo];
}

/**
 * Converte o clique em ponto de desenho.
 *
 * `null` quando o grafico nao consegue responder: click fora da area plotada,
 * ou sem serie (o `PriceChart` cria a serie num efeito aparte). Nesse caso o
 * ponto NAO e inventado.
 */
export function pontoDoEvento(
  x: number,
  y: number,
  lerTempo: (x: number) => number | null,
  lerPreco: (y: number) => number | null,
): PontoDesenho | null {
  const time = lerTempo(x);
  const preco = lerPreco(y);
  if (time === null || preco === null) return null;
  if (!Number.isFinite(time) || !Number.isFinite(preco)) return null;
  /*
    `preco <= 0` E RECUSA, e nao ponto.

    MEDIDO nesta implementacao: `Number.isFinite(0)` e verdadeiro, entao um
    `precoParaY` degenerado devolvia 0 e o ponto passava. O efeito seria uma
    linha horizontal colada no topo do grafico — e o operador marcaria o stop
    nela.

    Nenhum ativo opera a 0, e `time = 0` e 1970, nao uma barra. Um ponto
    nesses valores nao veio do grafico: veio de uma conversao quebrada.
  */
  if (preco <= 0 || time <= 0) return null;
  return { time, preco };
}

/** Segmento em pixels, ou `null` se algum ponto estiver fora da tela. */
export function segmentoTendencia(
  desenho: Desenho,
  tempoParaX: (t: number) => number | null,
  precoParaY: (p: number) => number | null,
): { x1: number; y1: number; x2: number; y2: number } | null {
  if (desenho.tipo !== 'tendencia' || desenho.pontos.length < 2) return null;
  const [a, b] = desenho.pontos;
  const x1 = tempoParaX(a.time);
  const y1 = precoParaY(a.preco);
  const x2 = tempoParaX(b.time);
  const y2 = precoParaY(b.preco);
  if (x1 === null || y1 === null || x2 === null || y2 === null) return null;
  return { x1, y1, x2, y2 };
}

/** Nivel em pixels da linha horizontal, ou `null` fora da escala. */
export function nivelHorizontal(
  desenho: Desenho,
  precoParaY: (p: number) => number | null,
): number | null {
  if (desenho.tipo !== 'horizontal' || desenho.pontos.length < 1) return null;
  return precoParaY(desenho.pontos[0].preco);
}

/**
 * O desenho mais proximo do ponto, para o botao de apagar.
 *
 * `toleranciaPx` em PIXEL e nao em preco: o operador mira com o olho, e o
 * que ele acerta e um lugar da tela. Converter para preco antes de comparar
 * faria a tolerancia mudar com o zoom — e a 85.000, 6 px sao poucos pontos.
 */
export function desenhoMaisProximo(
  desenhos: Desenho[],
  x: number,
  y: number,
  toleranciaPx = 8,
  distancia: (d: Desenho) => number | null,
): Desenho | null {
  let melhor: { d: Desenho; dist: number } | null = null;
  for (const d of desenhos) {
    const dist = distancia(d);
    if (dist === null) continue;
    if (dist <= toleranciaPx && (!melhor || dist < melhor.dist)) melhor = { d, dist };
  }
  return melhor ? melhor.d : null;
}

/** Distancia do ponto ate a linha de tendencia, em pixels. */
export function distanciaAteTendencia(px: number, py: number, s: {
  x1: number; y1: number; x2: number; y2: number;
}): number {
  const dx = s.x2 - s.x1;
  const dy = s.y2 - s.y1;
  const comprimento2 = dx * dx + dy * dy;
  // Linha de comprimento zero: todo ponto esta a mesma distancia da origem.
  if (comprimento2 === 0) return Math.hypot(px - s.x1, py - s.y1);
  let t = ((px - s.x1) * dx + (py - s.y1) * dy) / comprimento2;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(px - (s.x1 + t * dx), py - (s.y1 + t * dy));
}

/** Distancia do ponto ate a linha horizontal, em pixels. */
export function distanciaAteHorizontal(py: number, nivel: number): number {
  return Math.abs(py - nivel);
}

/*
  AS PONTAS ARRASTAVEIS (06/10/2026)
  ==================================
  MEDIDO nas capturas da XM (20:31 e 20:35): a linha de tendencia tem DOIS
  circulos nas pontas, e arrastar um deles move a linha. Sem isso a tendencia
  existe mas nao serve para ajustar o stop — que e o que o dono pediu.

  A PONTA E O PONTO DO DESENHO, e nao um pixel.

  `pontasVisiveis` converte os pontos de `tempo`/`preco` para tela com os MESMOS
  conversores que a linha usa. E por isso que a ponta acompanha o zoom: se ela
  guardasse pixel, a linha andaria e o circulo ficaria para tras — o operador
  veria a ponta onde o mouse esta e a linha em outro lugar, e moveria a linha
  errada achando que arrastou a certa.
*/

/** Uma ponta desenhavel, ja em pixels. */
export type Ponta = { indice: number; x: number; y: number };

/**
 * As pontas que existem AGORA, ou `[]`.
 *
 * `[]` quando o desenho esta travado ou nao da para medir um dos pontos. E a
 * diferenca entre "sem ponta" e "ponta em (0,0)": um circulo no canto do
 * grafico parece clicavel e arrasta o desenho para o preco errado.
 */
export function pontasVisiveis(
  desenho: Desenho,
  tempoParaX: (t: number) => number | null,
  precoParaY: (p: number) => number | null,
): Ponta[] {
  if (estiloDe(desenho).travado) return [];
  const saida: Ponta[] = [];
  desenho.pontos.forEach((ponto, indice) => {
    const x = tempoParaX(ponto.time);
    const y = precoParaY(ponto.preco);
    if (x === null || y === null) return;
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    saida.push({ indice, x, y });
  });
  return saida;
}

/**
 * A ponta mais proxima do cursor, dentro da tolerancia, ou `null`.
 *
 * A tolerancia e em PIXEL pelo mesmo motivo de `desenhoMaisProximo`: o operador
 * mira com o olho, e o que ele acerta e um lugar da tela. `RAIO_PONTA` e o
 * raio desenhado mais uma folga — a ponta precisa ser clicavel no lugar onde
 * ela APARECE, senao o operador mira no circulo e o arraste nao pega.
 */
export function pontaMaisProxima(
  desenhos: Desenho[],
  x: number,
  y: number,
  toleranciaPx: number,
  tempoParaX: (t: number) => number | null,
  precoParaY: (p: number) => number | null,
): { desenho: Desenho; indice: number } | null {
  let melhor: { desenho: Desenho; indice: number; dist: number } | null = null;
  for (const desenho of desenhos) {
    for (const ponta of pontasVisiveis(desenho, tempoParaX, precoParaY)) {
      const dist = Math.hypot(x - ponta.x, y - ponta.y);
      if (dist > toleranciaPx) continue;
      if (!melhor || dist < melhor.dist) {
        melhor = { desenho, indice: ponta.indice, dist };
      }
    }
  }
  return melhor ? { desenho: melhor.desenho, indice: melhor.indice } : null;
}

/**
 * Devolve o desenho com UM ponto trocado.
 *
 * IMMUTAVEL de proposito: o `PriceChart` guarda os desenhos em estado do React
 * e compara por identidade para redesenhar. Mutar o objeto no lugar faria o
 * React nao ver mudanca nenhuma, e a linha nao se moveria — o botaoaria
 * funcionar e nada aconteceria, que e o defeito do botao EMA.
 *
 * Devolve `null` quando o ponto novo nao veio do grafico. Aprovar um ponto com
 * `preco` invalido e o que colocaria a linha no topo do grafico, e o operador
 * marcaria o stop la.
 */
export function moverPonto(
  desenho: Desenho,
  indice: number,
  ponto: PontoDesenho | null,
): Desenho | null {
  if (!ponto) return null;
  if (indice < 0 || indice >= desenho.pontos.length) return null;
  if (!Number.isFinite(ponto.time) || !Number.isFinite(ponto.preco)) return null;
  if (ponto.preco <= 0 || ponto.time <= 0) return null;
  const pontos = [...desenho.pontos];
  pontos[indice] = ponto;
  return { ...desenho, pontos };
}

/**
 * O desenho pode receber arraste de ponto agora?
  *
 * Este e o guarda que impede o desenho travado de voltar a ser arrastado por
 * baixo da tranca: sem ele, o circulo some mas o `mousedown` continuaria
 * pegando — e o operador veria a tranca fechada e a linha se mexendo.
 */
export function podeMoverPontos(desenho: Desenho): boolean {
  return !estiloDe(desenho).travado;
}