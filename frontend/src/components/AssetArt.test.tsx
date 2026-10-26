// @vitest-environment jsdom
// O DESENHO DE FUNDO VEM DA CLASSE, NAO DO NOME
// =============================================
// O card recebe a classe da corretora e desenha de acordo com ela. Este teste
// trava tres coisas:
//
//  1. classe conhecida desenha o desenho daquela classe;
//  2. classes diferentes desenham desenhos diferentes (nao e a mesma arte
//     recolorida);
//  3. classe desconhecida cai no neutro — nunca chuta um ativo.
//
// Prova negativa: sem a classe, o `data-art` tem de ser `indefinida`. Se
// alguem voltar a adivinhar pelo simbolo, o caso 3 passa a falhar.
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render } from '@testing-library/react';
import AssetArt from './AssetArt';

afterEach(cleanup);

const svg = (container: HTMLElement) => container.querySelector('svg.mc-art-svg') as SVGElement | null;

describe('AssetArt', () => {
  it('desenha pela classe que a corretora publicou', () => {
    const { container } = render(<AssetArt classe="metal" seed={120} cor="#ffd24a" />);
    const el = svg(container);
    expect(el).not.toBeNull();
    expect(el?.getAttribute('data-art')).toBe('metal');
    expect(el?.querySelectorAll('path').length).toBeGreaterThan(1);
  });

  it('classes diferentes nao compartilham o mesmo desenho', () => {
    const a = render(<AssetArt classe="forex" seed={7} cor="#7fc0ff" />);
    const b = render(<AssetArt classe="cripto" seed={7} cor="#3ee6f0" />);
    expect(svg(a.container)?.innerHTML).not.toBe(svg(b.container)?.innerHTML);
    a.unmount();
    b.unmount();
  });

  it('classe desconhecida cai no neutro, sem chutar ativo', () => {
    const { container } = render(<AssetArt classe="" seed={1} cor="#8a94a6" />);
    expect(svg(container)?.getAttribute('data-art')).toBe('indefinida');
  });

  it('o seed muda posicao e inclinacao sem mudar o desenho', () => {
    const a = render(<AssetArt classe="indice" seed={3} cor="#c4a6ff" />);
    const b = render(<AssetArt classe="indice" seed={31} cor="#c4a6ff" />);
    const estilo = (c: HTMLElement) =>
      svg(c)?.style.getPropertyValue('--aa-r');
    expect(estilo(a.container)).not.toBe(estilo(b.container));
    expect(svg(a.container)?.getAttribute('data-art')).toBe('indice');
    a.unmount();
    b.unmount();
  });
});
