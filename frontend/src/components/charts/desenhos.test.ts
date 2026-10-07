// A CAMADA DE DESENHO SEGUE O GRAFICO (06/10/2026)
//
// MEDIDO nas capturas da XM (20:31, 20:33, 20:39): com horizontais coloridas,
// diagonais cruzando, traco livre e um "E A" escrito, tudo fica ancorado ao
// PRECO e anda junto quando o operador amplia ou desloca. Os rotulos do eixo
// (`86.712,20`, `85.726,99`, `84.535,89`) continuam nos mesmos niveis.
//
// ESTE E O TESTE QUE PROVA QUE O GRAFICO E "LIVRE".
//
// Sem `subscribeVisibleLogicalRangeChange`, o desenho fica preso no PIXEL: o
// React so re-renderiza quando o ESTADO muda, e zoom e deslocamento mudam o
// estado do GRAFICO, nao o do componente. A linha ficaria parada enquanto os
// candles andam — e isso e pior que nao ter linha: ela parece confiavel e
// esta errada. O operador marcaria o stop no lugar errado.

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  completo,
  distanciaAteHorizontal,
  distanciaAteTendencia,
  desenhoMaisProximo,
  ESPESSURAS,
  estiloDe,
  moverPonto,
  nivelHorizontal,
  PALETA,
  PONTOS_POR_FERRAMENTA,
  podeMoverPontos,
  pontaMaisProxima,
  pontasVisiveis,
  normalizarEspessura,
  normalizarOpacidade,
  pontoDoEvento,
  segmentoTendencia,
  type Desenho,
} from './desenhos';

const TENDENCIA: Desenho = {
  id: 'd1',
  tipo: 'tendencia',
  pontos: [
    { time: 1000, preco: 100 },
    { time: 2000, preco: 120 },
  ],
};

const HORIZONTAL: Desenho = {
  id: 'd2',
  tipo: 'horizontal',
  pontos: [{ time: 1000, preco: 110 }],
};

describe('o desenho guarda COORDENADA DA CORRETORA, e nao pixel', () => {
  it('a tendencia e montada a partir de tempo e preco, nao de x e y', () => {
    expect(TENDENCIA.pontos[0]).toEqual({ time: 1000, preco: 100 });
    expect(TENDENCIA.pontos[1]).toEqual({ time: 2000, preco: 120 });
  });

  it('pontoDoEvento le tempo e preco do proprio grafico', () => {
    const ponto = pontoDoEvento(120, 45, (x) => (x === 120 ? 1500 : null), (y) => (y === 45 ? 105 : null));
    expect(ponto).toEqual({ time: 1500, preco: 105 });
  });

  it('PROVA NEGATIVA: grafico que nao responde NAO inventa o ponto', () => {
    // `null` e "nao medido". Um ponto inventado colocaria a linha num preco
    // que ninguem escolheu — e o operador marcaria o stop nele.
    expect(pontoDoEvento(120, 45, () => null, () => 105)).toBeNull();
    expect(pontoDoEvento(120, 45, () => 1500, () => null)).toBeNull();
    expect(pontoDoEvento(120, 45, () => Number.NaN, () => 105)).toBeNull();
  });

  it('PROVA NEGATIVA: preco ZERO e recusado, e nao aceito como ponto', () => {
    /*
    MEDIDO nesta implementacao: `Number.isFinite(0)` e verdadeiro, entao um
    `precoParaY` degenerado devolvia 0 e o ponto passava. O efeito seria uma
    linha horizontal colada no topo do grafico, e o operador marcaria o stop
    nela. Nenhum ativo opera a 0, e `time = 0` e 1970 — nao uma barra.
    */
    expect(pontoDoEvento(1, 1, () => 1500, () => 0)).toBeNull();
    expect(pontoDoEvento(1, 1, () => 0, () => 105)).toBeNull();
    expect(pontoDoEvento(1, 1, () => 1500, () => -5)).toBeNull();
  });
});

describe('a linha se redesenha depois de zoom e deslocamento', () => {
  const tempoParaX = (t: number) => (t === 1000 ? 10 : t === 2000 ? 90 : null);
  const precoParaY = (p: number) => (p === 100 ? 200 : p === 120 ? 40 : p === 110 ? 55 : null);

  it('o mesmo desenho produz o MESMO caminho onde a corretora manda', () => {
    expect(segmentoTendencia(TENDENCIA, tempoParaX, precoParaY)).toEqual({
      x1: 10, y1: 200, x2: 90, y2: 40,
    });
  });

  it('PROVA: mudando a escala do grafico, o desenho muda JUNTO', () => {
    // Zoom: o mesmo tempo agora ocupa outro pixel. Se o desenho ficasse preso
    // no pixel antigo, antes e depois seriam IGUAIS — e a linha estaria errada
    // sem parecer. Aqui eles diferem, que e o comportamento correto.
    const antes = segmentoTendencia(TENDENCIA, tempoParaX, precoParaY);
    const depois = segmentoTendencia(
      TENDENCIA,
      (t) => (t === 1000 ? 30 : t === 2000 ? 300 : null),
      (p) => (p === 100 ? 400 : p === 120 ? 20 : null),
    );
    expect(depois).not.toEqual(antes);
    expect(depois).toEqual({ x1: 30, y1: 400, x2: 300, y2: 20 });
  });

  it('ponto fora da tela NAO vira 0: some, e nao gruda no topo', () => {
    const s = segmentoTendencia(TENDENCIA, () => null, precoParaY);
    expect(s).toBeNull();
    // Um `0` aqui seria uma linha valendo o preco mais alto do grafico, com
    // aparencia de linha correta.
    expect(s).not.toEqual({ x1: 0, y1: 0, x2: 0, y2: 0 });
  });

  it('a horizontal usa o nivel, e o rotulo de preco acompanha o nivel', () => {
    // `HORIZONTAL.pontos[0].preco` e 110, e o duble mapeia 110 -> 55. Uma
    // expectativa de 200 aqui era o preco da TENDENCIA: o teste lia o numero
    // de outro desenho, e passava por acaso num caso e falhava no outro.
    expect(nivelHorizontal(HORIZONTAL, precoParaY)).toBe(55);
    // E o rotulo se move junto: o mesmo desenho, outra escala, outro pixel.
    expect(nivelHorizontal(HORIZONTAL, (p) => (p === 110 ? 12 : null))).toBe(12);
  });

  it('PROVA NEGATIVA: horizontal fora da escala devolve null, nao 0', () => {
    expect(nivelHorizontal(HORIZONTAL, () => null)).toBeNull();
  });
});

describe('completar o desenho', () => {
  it('a tendencia so fecha com DOIS pontos', () => {
    expect(PONTOS_POR_FERRAMENTA.tendencia).toBe(2);
    expect(completo({ ...TENDENCIA, pontos: [TENDENCIA.pontos[0]] })).toBe(false);
    expect(completo(TENDENCIA)).toBe(true);
  });

  it('a horizontal fecha com UM ponto', () => {
    expect(PONTOS_POR_FERRAMENTA.horizontal).toBe(1);
    expect(completo(HORIZONTAL)).toBe(true);
  });

  it('PROVA NEGATIVA: com tres pontos, so os DOIS PRIMEIROS viram linha', () => {
    // Tres pontos seria uma poligonia, que e outra ferramenta. Aqui o terceiro
    // ponto seria silenciosamente ignorado — e o operador veria uma linha que
    // nao passa onde ele clicou pela terceira vez.
    const tres = { ...TENDENCIA, pontos: [...TENDENCIA.pontos, { time: 3000, preco: 90 }] };
    const s = segmentoTendencia(tres, (t) => (t === 1000 ? 5 : t === 2000 ? 95 : 500), () => 50);
    expect(s!.x2).toBe(95);
  });
});

describe('apagar: o desenho mais proximo do clique', () => {
  /*
    A assinatura de `desenhoMaisProximo` e `(d) => dist`: o callback NAO recebe
    a posicao do cursor. Quem chama fecha o cursor por fora — e assim que o
    `PriceChart` faz, medindo com `distanciaAteTendencia(x, y, ...)`.

    O teste faz o mesmo com uma fabrica `distanciaPara(x, y)`. A primeira
    versao media com um y fixo, e por isso "longe nao apaga" passava por acaso
    e "acha sob o cursor" falhava: o duble media a linha com o nivel errado, e
    nao o desenho que estava na tela. E o AGENTS.md 6 — duble que mede a coisa
    errada faz o teste passar calado.
  */
  const distanciaPara = (x: number, y: number) => (d: Desenho): number | null => {
    if (d.tipo === 'tendencia') {
      return distanciaAteTendencia(x, y, { x1: 0, y1: 100, x2: 100, y2: 100 });
    }
    // O duble "pinta" o preco no pixel que ele realmente ocuparia.
    const nivel = nivelHorizontal(d, (p) => (p === d.pontos[0].preco ? d.pontos[0].preco : null));
    return nivel === null ? null : distanciaAteHorizontal(y, nivel);
  };

  beforeEach(() => vi.clearAllMocks());

  it('acha o desenho que esta sob o cursor', () => {
    // A linha esta no preco 110 -> pixel 110. Com o cursor em y=112 ela esta a
    // 2 px, dentro da tolerancia de 8.
    expect(desenhoMaisProximo([HORIZONTAL], 50, 112, 8, distanciaPara(50, 112))?.id).toBe('d2');
  });

  it('PROVA NEGATIVA: longe de todo desenho, nao apaga NENHUM', () => {
    // Apagar o vizinho quando o operador errou o clique perde trabalho sem
    // como desfazer.
    expect(desenhoMaisProximo([HORIZONTAL], 50, 50, 8, distanciaPara(50, 50))).toBeNull();
  });

  it('PROVA NEGATIVA: com dois desenhos, apaga o MAIS proximo, e nao o primeiro', () => {
    const lista: Desenho[] = [
      { id: 'longe', tipo: 'horizontal', pontos: [{ time: 0, preco: 400 }] },
      { id: 'perto', tipo: 'horizontal', pontos: [{ time: 0, preco: 112 }] },
    ];
    expect(desenhoMaisProximo(lista, 50, 112, 8, distanciaPara(50, 112))?.id).toBe('perto');
  });

  it('desenho fora da tela nao entra na conta do clique', () => {
    expect(desenhoMaisProximo([HORIZONTAL], 50, 50, 8, () => null)).toBeNull();
  });
});

describe('a distancia ate a linha', () => {
  it('a tendencia: ponto sobre a linha da zero', () => {
    expect(distanciaAteTendencia(50, 50, { x1: 0, y1: 0, x2: 100, y2: 100 })).toBeCloseTo(0, 6);
  });

  it('a tendencia: ponto na diagonal de baixo da distancia real', () => {
    // De (0,0) a (100,100), o ponto (0,100) esta a 70,71 da linha.
    expect(distanciaAteTendencia(0, 100, { x1: 0, y1: 0, x2: 100, y2: 100 })).toBeCloseTo(70.71, 2);
  });

  it('PROVA NEGATIVA: linha de comprimento zero nao divide por zero', () => {
    // Dois pontos no mesmo lugar: comprimento 0. A formula normal daria NaN, e
    // `NaN <= tolerancia` e falso — o desenho ficaria impossivel de apagar.
    const d = distanciaAteTendencia(30, 40, { x1: 0, y1: 0, x2: 0, y2: 0 });
    expect(Number.isFinite(d)).toBe(true);
    expect(d).toBeCloseTo(50, 6);
  });

  it('a horizontal e distancia vertical pura', () => {
    expect(distanciaAteHorizontal(120, 100)).toBe(20);
    expect(distanciaAteHorizontal(80, 100)).toBe(20);
  });
});

/*
  AS PONTAS ARRASTAVEIS
  ====================
  MEDIDO nas capturas da XM (20:31, 20:35): dois circulos nas pontas da linha de
  tendencia, e arrastar um deles move a linha. E o que faltava para a linha
  servir para AJUSTAR O STOP, que e o uso que o dono descreveu.

  O teste que importa nao e "a ponta existe": e que a ponta ANDA JUNTO com a
  linha no zoom. Ponta presa em pixel e o defeito que faria o operador arrastar
  a linha errada achando que acertou a ponta.
*/
describe('as pontas arrastaveis', () => {
  const tempoParaX = (t: number) => (t === 1000 ? 10 : t === 2000 ? 90 : null);
  const precoParaY = (p: number) => (p === 100 ? 40 : p === 120 ? 8 : null);

  it('a tendencia tem DUAS pontas, nos dois pontos', () => {
    expect(pontasVisiveis(TENDENCIA, tempoParaX, precoParaY)).toEqual([
      { indice: 0, x: 10, y: 40 },
      { indice: 1, x: 90, y: 8 },
    ]);
  });

  it('a horizontal tem UMA ponta', () => {
    expect(pontasVisiveis(HORIZONTAL, tempoParaX, (p) => (p === 110 ? 25 : null))).toEqual([
      { indice: 0, x: 10, y: 25 },
    ]);
  });

  it('PROVA: dando zoom, a ponta muda JUNTO com a linha', () => {
    // O mesmo tempo 1000 que estava em x=10 agora ocupa x=5, porque o grafico
    // dobrou a escala. A ponta que ficasse em 10 estaria fora da linha — e o
    // operador arrastaria a ponta errada.
    const antes = pontasVisiveis(TENDENCIA, tempoParaX, precoParaY);
    const depois = pontasVisiveis(TENDENCIA, (t) => (t === 1000 ? 5 : 45), precoParaY);
    expect(antes[0].x).toBe(10);
    expect(depois[0].x).toBe(5);
    // E o segmento usa a MESMA ponta: os dois vem do mesmo ponto.
    const segmento = segmentoTendencia(TENDENCIA, (t) => (t === 1000 ? 5 : 45), precoParaY);
    expect(segmento?.x1).toBe(depois[0].x);
    expect(segmento?.x2).toBe(depois[1].x);
  });

  it('PROVA NEGATIVA: ponto fora da tela NAO vira ponta em (0,0)', () => {
    // Sem esta guarda, o `?? 0` do conversor quebrado colocaria um circulo no
    // canto do grafico, clicavel, e arrastaria o desenho para o preco errado.
    const pontas = pontasVisiveis(TENDENCIA, () => null, precoParaY);
    expect(pontas).toEqual([]);
  });

  it('PROVA NEGATIVA: desenho TRAVADO nao tem ponta nenhuma', () => {
    const trancado: Desenho = { ...TENDENCIA, estilo: { travado: true } };
    expect(pontasVisiveis(trancado, tempoParaX, precoParaY)).toEqual([]);
    expect(podeMoverPontos(trancado)).toBe(false);
  });

  it('PROVA NEGATIVA: o conversor que devolve NaN nao gera ponta', () => {
    expect(pontasVisiveis(TENDENCIA, () => Number.NaN, precoParaY)).toEqual([]);
  });
});

describe('arrastar a ponta', () => {
  const tempoParaX = (t: number) => (t === 1000 ? 10 : t === 2000 ? 90 : null);
  const precoParaY = (p: number) => (p === 100 ? 40 : p === 120 ? 8 : null);

  it('acha a ponta sob o cursor e devolve o indice', () => {
    const achou = pontaMaisProxima([TENDENCIA], 12, 39, 8, tempoParaX, precoParaY);
    expect(achou?.desenho.id).toBe('d1');
    expect(achou?.indice).toBe(0);
  });

  it('PROVA NEGATIVA: longe de toda ponta, NAO arrasta nada', () => {
    // O ponto (200,200) esta longe das duas pontas. Se devolvesse a ponta 0, o
    // operador arrastaria a linha ao clicar no vazio.
    expect(pontaMaisProxima([TENDENCIA], 200, 200, 8, tempoParaX, precoParaY)).toBeNull();
  });

  it('PROVA NEGATIVA: com duas pontas, pega a MAIS PROXIMA, nao a primeira', () => {
    // As duas pontas de TENDENCIA estao a x=10 e x=90. Mirando em x=90 tem de
    // devolver o indice 1 — devolver 0 seria arrastar a ponta errada da linha.
    expect(pontaMaisProxima([TENDENCIA], 90, 8, 8, tempoParaX, precoParaY)?.indice).toBe(1);
  });

  it('PROVA NEGATIVA: desenho travado nao e arrastavel, mesmo com a ponta no cursor', () => {
    const trancado: Desenho = { ...TENDENCIA, estilo: { travado: true } };
    expect(pontaMaisProxima([trancado], 10, 40, 8, tempoParaX, precoParaY)).toBeNull();
  });

  it('mover a ponta grava a COORDENADA DA CORRETORA, nao o pixel', () => {
    const novo = moverPonto(TENDENCIA, 0, { time: 3000, preco: 130 });
    expect(novo?.pontos[0]).toEqual({ time: 3000, preco: 130 });
    // O outro ponto NAO foi tocado.
    expect(novo?.pontos[1]).toEqual({ time: 2000, preco: 120 });
  });

  it('mover devolve um objeto NOVO, sem mexer no original', () => {
    const antes = JSON.stringify(TENDENCIA);
    const novo = moverPonto(TENDENCIA, 0, { time: 3000, preco: 130 });
    expect(novo).not.toBe(TENDENCIA);
    expect(JSON.stringify(TENDENCIA)).toBe(antes);
  });

  it('PROVA NEGATIVA: ponto invalido e recusado, nao meia-linha', () => {
    // `preco` e `time` que nao vieram do grafico: aceitá-los colocaria a linha no
    // topo do grafico, e o operador marcaria o stop lá.
    expect(moverPonto(TENDENCIA, 0, null)).toBeNull();
    expect(moverPonto(TENDENCIA, 0, { time: 3000, preco: 0 })).toBeNull();
    expect(moverPonto(TENDENCIA, 0, { time: 0, preco: 130 })).toBeNull();
    expect(moverPonto(TENDENCIA, 0, { time: Number.NaN, preco: 130 })).toBeNull();
    expect(moverPonto(TENDENCIA, 5, { time: 3000, preco: 130 })).toBeNull();
    expect(moverPonto(TENDENCIA, -1, { time: 3000, preco: 130 })).toBeNull();
  });
});

describe('o estilo do desenho', () => {
  it('desenho sem estilo recebe o padrao, nunca indefinido', () => {
    // `stroke` vazio no SVG desenharia a linha preta do navegador, que parece
    // uma linha de verdade.
    const e = estiloDe(TENDENCIA);
    expect(e.cor).toBeTruthy();
    expect(e.opacidade).toBe(1);
    expect(e.espessura).toBe(2);
    expect(e.travado).toBe(false);
  });

  it('o estilo guardado tem precedencia sobre o padrao', () => {
    const d: Desenho = { ...TENDENCIA, estilo: { cor: '#e74c3c', espessura: 4, opacidade: 0.5, travado: true } };
    expect(estiloDe(d)).toEqual({ cor: '#e74c3c', espessura: 4, opacidade: 0.5, travado: true });
  });

  it('estilo pela metade completa com o padrao, sem inventar campo', () => {
    expect(estiloDe({ ...TENDENCIA, estilo: { cor: '#2ecc71' } })).toEqual({
      cor: '#2ecc71', opacidade: 1, espessura: 2, travado: false,
    });
  });

  it('a paleta e da tela: hexadecimal, nunca nome de cor', () => {
    // Um nome como `red` seria resolvido pelo navegador em um lugar e nao no
    // outro; e nenhuma cor aqui significa mercado.
    expect(PALETA.length).toBeGreaterThanOrEqual(16);
    PALETA.forEach((cor) => expect(cor).toMatch(/^#[0-9a-f]{6}$/i));
    expect(new Set(PALETA).size).toBe(PALETA.length);
  });

  it('PROVA NEGATIVA: opacidade fora de 0..1 e RECUSADA, nao ignorada', () => {
    // O SVG ignora `opacity` invalida e a linha fica com a opacidade anterior —
    // o clique pareceria nao funcionar.
    expect(normalizarOpacidade(1.5)).toBeNull();
    expect(normalizarOpacidade(-0.1)).toBeNull();
    // `NaN` passa por qualquer comparacao `<`/`>` e viraria atributo invalido.
    expect(normalizarOpacidade(Number.NaN)).toBeNull();
    expect(normalizarOpacidade(0)).toBe(0);
    expect(normalizarOpacidade(0.35)).toBe(0.35);
    expect(normalizarOpacidade(1)).toBe(1);
  });

  it('PROVA NEGATIVA: espessura fora de 1..4, ou fracionaria, e recusada', () => {
    expect(normalizarEspessura(0)).toBeNull();
    expect(normalizarEspessura(5)).toBeNull();
    expect(normalizarEspessura(1.5)).toBeNull();
    expect(normalizarEspessura(Number.NaN)).toBeNull();
    ESPESSURAS.forEach((e) => expect(normalizarEspessura(e)).toBe(e));
  });
});