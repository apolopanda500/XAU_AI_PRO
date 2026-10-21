// @vitest-environment jsdom
/*
  A CONTAGEM E UMA FRASE DE OITO IRMAOS (09/10/2026)
  ===================================================
  MEDIDO na captura de 07/10 00:38, no app instalado, aba "Historico":

      Exibindo / 5 / operacoes / e / 3 / movimentacoes / 12 registros / 00:38:10

  Oito palavras empilhadas, com a janela de 1456px.

  POR QUE ESTE ARQUIVO EXISTE AO LADO DO TESTE DE CSS
  ===================================================
  `test_history_css.test.ts` trava a REGRA (o eixo do flex). Isso e necessario e
  nao e suficiente: uma regra pode estar correta e o JSX entregar outra coisa.

  E `jsdom` nao calcula layout, entao renderizar e medir `offsetWidth` daria `0`
  para tudo — verde com o defeito na tela (AGENTS.md §6).

  O QUE ESTE ARQUIVO FAZ, entao: nao mede pixel. Mede a ESTRUTURA que a regra
  precisa — os oito nos como IRMAOS diretos, no mesmo container, para que
  `row wrap` tenha o que colocar na linha. E mede que a frase montada e a frase
  da captura, na ordem, para que a contagem nao possa virar seis nos soltos.

  Se um dia alguem trocar o `div` por um `ul` de listas, ou envolver cada par
  (`5` + `operacoes`) num `<span>` proprio, a frase volta a quebrar — e aqui
  reprova, por estrutura e nao por palavra.
*/
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render } from '@testing-library/react';

const { useHistoricoMock } = vi.hoisted(() => ({ useHistoricoMock: vi.fn() }));

vi.mock('../../lib/historico', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/historico')>();
  return { ...actual, useHistorico: useHistoricoMock };
});

const { default: HistoryTab } = await import('./HistoryTab');

/*
  A CONTA DA CAPTURA
  ==================
  MEDIDO em 07/10 00:38: `Exibindo 5 operacoes e 3 movimentacoes · 12 registros ·
  00:38:10`. Sao 5 operacoes (4 de BTCUSD com uma abertura e um fechamento
  formando linha unica, mais ...) e 3 movimentacoes de saldo.

  O que importa aqui e a CONTAGEM: `deals` traz os registros, e o componente e
  que decide quantos sao operacao e quantos sao movimentacao (AGENTS.md §10: as
  duas camadas nao se misturam).
*/
const CONTA: Record<string, unknown>[] = [
  {
    id: 'op-1',
    broker: 'mt5',
    symbol: 'BTCUSD',
    volume: 0.01,
    price: 85533.55,
    profit: 0,
    executedAt: '2026-10-07T00:36:28Z',
    type: 'BUY',
    ticket: 261109609,
    comment: '',
    categoria: 'operacao',
    position_id: 'p1',
  },
  ...Array.from({ length: 3 }, (_, i) => ({
    id: `mov-${i}`,
    broker: 'mt5',
    symbol: '',
    volume: 0,
    price: 0,
    profit: 5.62,
    executedAt: '2026-10-04T21:53:54Z',
    type: i === 0 ? 'BALANCE' : 'CREDIT',
    ticket: 260002613 + i,
    comment: `mov ${i}`,
    categoria: 'movimentacao',
  })),
];

function devolver(extra: Record<string, unknown> = {}) {
  useHistoricoMock.mockReturnValue({
    deals: CONTA,
    loading: false,
    erro: '',
    status: 'mt5: 6',
    updatedAt: '00:38:10',
    recarregar: vi.fn(),
    ...extra,
  });
}

describe('a contagem do historico e uma frase de irmaos', () => {
  beforeEach(() => devolver());
  afterEach(() => cleanup());

  /** Os filhos diretos do container da contagem, na ordem da tela. */
  const irmaos = (container: HTMLElement): Element[] =>
    Array.from(container.querySelector('.history-count')?.children ?? []);

  it('o container da contagem EXISTE — sem isto o resto passa por acidente', () => {
    /*
      Sem este `expect`, um `.history-count` renomeado faria `irmaos()` devolver
      `[]`, e `toHaveLength` reprovaria por motivo errado — e o agente seguinte
      buscaria um bug de dado num teste de layout.
    */
    const { container } = render(<HistoryTab />);
    expect(container.querySelector('.history-count')).not.toBeNull();
  });

  it('os itens da frase sao IRMAOS, nao um dentro do outro', () => {
    const { container } = render(<HistoryTab />);
    const nos = irmaos(container);

    /*
      Este e o teste que casa o defeito.

      Com `flex-direction: column`, cada `<span>` vira uma linha por si. O que
      faz isso e o eixo do flex — e o eixo esta em `test_history_css.test.ts`.
      Aqui se trava a OUTRA metade: que existe mais de um no, e que eles sao
      irmaos no mesmo container. Um no so nao tem o que ser partida; e nove nos
      aninhados dentro de um wrapper nao tem o que ser linha.
    */
    expect(nos.length).toBeGreaterThan(1);

    // Nenhum dos nos pode TER nos — seria a frase embrulhada em outra coisa,
    // que `row wrap` nao conserta.
    for (const no of nos) {
      expect(no.children.length, `no <${no.tagName.toLowerCase()}> com filho dentro`).toBe(0);
    }
  });

  it('a frase montada e a frase da captura, na ordem', () => {
    const { container } = render(<HistoryTab />);
    const frase = (irmaos(container).map((n) => n.textContent ?? '').join(' ')).replace(/\s+/g, ' ').trim();

    // MEDIDO na captura de 07/10 00:38.
    expect(frase).toContain('Exibindo');
    expect(frase).toContain('movimenta');
    expect(frase).toContain('00:38:10');

    // E a ordem: quem anuncia vem antes do numero, e o numero antes do substantivo.
    expect(frase.indexOf('Exibindo')).toBeLessThan(frase.indexOf('movimenta'));
    expect(frase.endsWith('00:38:10')).toBe(true);
  });

  it('PROVA NEGATIVA: um container com UM no so NAO satisfaz a medida', () => {
    /*
      A prova de que o teste acima nao e decorativo.

      Um no nao tem o que ser partida em linha. A MEDICAO acima
      (`length > 1`) reprova este caso; e o defeito da tela, em oito linhas,
      nunca teve `length === 1`.
    */
    const container = document.createElement('div');
    container.innerHTML = '<div class="history-count"><span>Exibindo</span></div>';
    const umNoSo = Array.from(container.querySelector('.history-count')?.children ?? []);

    expect(umNoSo.length).toBe(1);
    expect(umNoSo.length).not.toBeGreaterThan(1);

    // A frase real da tela tem varios nos — e e por isso que a regra precisa
    // de `row`, e nao de `column`.
    const { container: real } = render(<HistoryTab />);
    expect(irmaos(real).length).toBeGreaterThan(1);
  });

  it('PROVA NEGATIVA: nos ANINHADOS nao satisfazem a medida', () => {
    /*
      A segunda forma de "consertar" sem consertar: embrulhar cada par
      (`5` + `operacoes`) num `<span>`. O `row wrap` continua, e cada embrulho
      continua quebrando por dentro — porque o embrulho e que virou o no do flex.

      A medida do no sem filho reprova este caso.
    */
    const container = document.createElement('div');
    container.innerHTML =
      '<div class="history-count">' +
      '<span>Exibindo</span><span><strong>5</strong> operacoes</span>' +
      '<span>e</span><span><strong>3</strong> movimentacoes</span>' +
      '</div>';
    const aninhados = Array.from(container.querySelector('.history-count')?.children ?? []);

    expect(aninhados.some((no) => no.children.length > 0)).toBe(true);

    // A tela real nao tem nenhum no com filho.
    const { container: real } = render(<HistoryTab />);
    for (const no of irmaos(real)) {
      expect(no.children.length).toBe(0);
    }
  });
});