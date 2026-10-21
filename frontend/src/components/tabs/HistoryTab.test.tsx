// @vitest-environment jsdom
// O histórico no formato MT5: UMA tabela e a linha de resumo embaixo.
//
// Fonte de todo numero aqui: a captura do MT5 terminal, conta 391773676
// (XMGlobal-MT5 14), 05/10/2026, com o deal 24503922 aberto. Ver o cabeçalho de
// `historicoMt5.test.ts`, onde os MESMOS deals estão montados e testados como
// camada de dados. Aqui o que se prova é que a TELA mostra aquilo.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';

const { useHistoricoMock } = vi.hoisted(() => ({ useHistoricoMock: vi.fn() }));

vi.mock('../../lib/historico', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../../lib/historico')>();
  return { ...actual, useHistorico: useHistoricoMock };
});

const { default: HistoryTab, agruparPorDia } = await import('./HistoryTab');

/*
  OS DEALS DA CAPTURA DO MT5, literais.
  =======================================
  5 deals: 3 movimentacoes de saldo e a operacao 24503922 (abertura + fechamento).
  Sao os 5 deals da conta 391773676 medidos em 05/10/2026.

  Montar aqui um deal inventado testaria contra um formato que o MT5 nao produz
  — que e como os testes que gravavam o bug do `papel` no motor passaram sem ver
  nada (AGENTS.md 6).
*/

/** `CD-AST-PIC 265376085` — deposito de 5,52. */
const DEPOSITO_552 = {
  id: 'dep-552',
  broker: 'mt5',
  symbol: '',
  volume: 0,
  price: 0,
  profit: 5.52,
  executedAt: '2026-10-04T21:53:54Z',
  type: 'BALANCE',
  ticket: 260002613,
  comment: 'CD-AST-PIC 265376085',
  categoria: 'movimentacao',
};

/** `EXP05-AST-PIC 265376085` — deposito de 0,10. */
const DEPOSITO_010 = {
  id: 'dep-010',
  broker: 'mt5',
  symbol: '',
  volume: 0,
  price: 0,
  profit: 0.1,
  executedAt: '2026-10-04T21:53:54Z',
  type: 'BALANCE',
  ticket: 260002614,
  comment: 'EXP05-AST-PIC 265376085',
  categoria: 'movimentacao',
};

/** `Credit-In-100%-$100-NewClients` — credito de 5,62 concedido pela XM. */
const CREDITO_562 = {
  id: 'cred-562',
  broker: 'mt5',
  symbol: '',
  volume: 0,
  price: 0,
  profit: 5.62,
  executedAt: '2026-10-04T21:53:55Z',
  type: 'CREDIT',
  ticket: 260002615,
  comment: 'Credit-In-100%-$100-NewClients',
  categoria: 'movimentacao',
};

/** A operacao 24503922: ABERTURA. Ticket 24503921 — este NAO aparece na tela. */
const ABERTURA = {
  id: 'entrada-24503922',
  broker: 'mt5',
  symbol: 'btcusd',
  side: 'buy',
  entry: 'IN',
  type: 'BUY',
  volume: 0.01,
  price: 86394.85,
  realizedPnl: 0,
  executedAt: '2026-10-05T01:46:43Z',
  ticket: 24503921,
  position_id: 24503922,
};

/** FECHAMENTO. O ticket 24503922 e o que a coluna Bilhete mostra. */
const FECHAMENTO = {
  id: 'fechamento-24503922',
  broker: 'mt5',
  symbol: 'btcusd',
  side: 'sell',
  entry: 'OUT',
  type: 'SELL',
  volume: 0.01,
  price: 86585.35,
  realizedPnl: 2.01,
  executedAt: '2026-10-05T02:12:25Z',
  open_price: 86394.85,
  sl: 86594.5,
  ticket: 24503922,
  position_id: 24503922,
};

/** A conta inteira, na ordem que o MT5 devolveu. */
const CONTA = [DEPOSITO_552, DEPOSITO_010, CREDITO_562, ABERTURA, FECHAMENTO];

function devolver(extra: Record<string, unknown> = {}) {
  useHistoricoMock.mockReturnValue({
    deals: CONTA,
    loading: false,
    erro: '',
    status: 'mt5: 5',
    updatedAt: '19:30:00',
    recarregar: vi.fn(),
    ...extra,
  });
}

describe('HistoryTab — uma fonte só de histórico', () => {
  beforeEach(() => devolver());
  afterEach(() => cleanup());

  it('monta useHistorico uma unica vez', () => {
    render(<HistoryTab />);
    expect(useHistoricoMock).toHaveBeenCalledTimes(1);
  });

  it('recarregar usa o hook do historico', () => {
    const recarregar = vi.fn();
    devolver({ recarregar });
    const { container } = render(<HistoryTab />);
    const botao = within(container.querySelector('.history-page') as HTMLElement).getByRole('button', {
      name: 'Atualizar',
    });
    fireEvent.click(botao);
    expect(recarregar).toHaveBeenCalledTimes(1);
    expect(useHistoricoMock).toHaveBeenCalledTimes(1);
  });

  it('botao de atualizar desabilita com texto de progresso', () => {
    devolver({ loading: true });
    const { container } = render(<HistoryTab />);
    const historico = container.querySelector('.history-page') as HTMLElement;
    const b1 = within(historico).getByRole('button', { name: 'Atualizando…' });
    expect((b1 as HTMLButtonElement).disabled).toBe(true);
    expect(screen.queryAllByText('Atualizar')).toHaveLength(0);
  });
});

// ==========================================================================
// A TABELA ÚNICA (D7+D8)
// ==========================================================================
describe('HistoryTab — a tabela reproduz a captura do MT5', () => {
  beforeEach(() => devolver());
  afterEach(() => cleanup());

  it('PROVA NEGATIVA: existe UMA tabela, e nao duas', () => {
    // A tela tinha "Operações" e "Recargas e saques" separadas. Na captura do
    // MT5 é uma tabela e o que separa é o TIPO.
    const { container } = render(<HistoryTab />);
    expect(container.querySelectorAll('table')).toHaveLength(1);
    expect(container.querySelector('.history-movimentacoes')).toBeNull();
  });

  it('as 5 deals viram 4 linhas: 3 movimentacoes + 1 operacao', () => {
    const { container } = render(<HistoryTab />);
    expect(linhasDeDados(container)).toHaveLength(4);
  });

  it('a operacao e UMA linha, com entrada e fechamento lado a lado', () => {
    const { container } = render(<HistoryTab />);
    // 24503922 abre as 01:46:43 e fecha as 02:12:25 — uma linha só. Duas
    // linhas fariam o operador ler duas operações onde houve uma.
    const celulas = linhaDaOperacao(container).querySelectorAll('td');
    expect(celulas[0].textContent?.trim()).toMatch(/^\d{2}:\d{2}:\d{2}$/);
    expect(celulas[9].textContent?.trim()).toMatch(/^\d{2}:\d{2}:\d{2}$/);
    // E sao horas DIFERENTES: a de abertura e a de fechamento.
    expect(celulas[0].textContent?.trim()).not.toBe(celulas[9].textContent?.trim());
  });

  it('o Bilhete e o ticket 24503922, nao o da abertura', () => {
    const { container } = render(<HistoryTab />);
    const celulas = linhaDaOperacao(container).querySelectorAll('td');
    expect(celulas[2].textContent?.trim()).toBe('24503922');
    // O ticket da abertura (24503921) nao aparece: MEDIDO na captura, so o do
    // fechamento e mostrado.
    expect(container.textContent).not.toContain('24503921');
  });

  it('a coluna Mudanca mostra a variacao, e a coluna Lucro o resultado', () => {
    const { container } = render(<HistoryTab />);
    const celulas = linhaDaOperacao(container).querySelectorAll('td');
    // Lucro: 2,01. `fmtSigned` formata em pt-BR: 2,01 e 2,01.
    expect(numeroRenderizado(celulas[11])).toBeCloseTo(2.01, 6);
    expect(celulas[12].textContent?.trim()).toMatch(/^\d+\.\d{2}%$/);
  });

  it('o S/L vem da operacao e o T/P fica vazio quando nao ha alvo', () => {
    const { container } = render(<HistoryTab />);
    const celulas = linhaDaOperacao(container).querySelectorAll('td');
    expect(numeroRenderizado(celulas[7])).toBeCloseTo(86594.5, 6);
    // Vazio = a mercado. "--" diria "o gateway nao mandou"; o gateway mandou
    // vazio. As duas frases nao podem ser a mesma na tela.
    expect(celulas[8].textContent?.trim()).toBe('');
  });
});

describe('HistoryTab — movimentacao de saldo na mesma tabela, com Tipo', () => {
  beforeEach(() => devolver());
  afterEach(() => cleanup());

  it('mostra BALANCE, BALANCE e CREDIT — o dado estruturado da XM', () => {
    // MEDIDO: as tres movimentacoes da conta 391773676 vieram assim. Sem ler o
    // campo, tudo aparecia como "SELL" e o operador lia "vendi" num deposito.
    const { container } = render(<HistoryTab />);
    const tipos = Array.from(container.querySelectorAll('.history-deals td:nth-child(4)')).map(
      (n) => n.textContent?.trim(),
    );
    expect(tipos).toContain('BALANCE');
    expect(tipos).toContain('CREDIT');
    // E a operacao e `BUY`, o lado da ABERTURA. A captura escreve `buy`; o
    // deal de fechamento e `SELL`, e usa-lo escreveria "venda" numa compra.
    expect(tipos).toContain('BUY');
    expect(tipos).not.toContain('SELL');
  });

  it('PROVA NEGATIVA: movimentacao NAO tem Lucro 0,00', () => {
    // 0,00 e um numero medido. Numa movimentacao nao existe resultado: o
    // dinheiro entrou. Escrever 0,00 e o resumo somando zero como se fosse
    // resultado de trading.
    const { container } = render(<HistoryTab />);
    const linha = linhaDoBilhete(container, '260002613');
    const celulas = linha.querySelectorAll('td');
    expect(celulas[11].textContent?.trim()).toBe('');
    expect(celulas[11].textContent).not.toContain('0,00');
  });

  it('PROVA NEGATIVA: movimentacao nao tem Volume, Preco, S/L nem Mudanca', () => {
    // Campos de operação vazios, NAO zero. Um depósito não tem preço nem
    // volume, e mostrar 0,00 diria que o negócio foi a 0,00 com 0,00 de
    // volume.
    //
    // A coluna ATIVO vira o travessão — é a única celula com um marcador — e
    // todas as outras ficam VAZIAS. O travessão diria "algo aqui, sem valor";
    // numa movimentação não há valor faltando, a coluna não se aplica. O `title`
    // da linha e que diz por que estão vazias.
    const { container } = render(<HistoryTab />);
    const linha = linhaDoBilhete(container, '260002613');
    const celulas = linha.querySelectorAll('td');
    expect(celulas[1].textContent?.trim()).toBe('—');
    for (const i of [5, 6, 7, 8, 9, 10, 11, 12]) {
      expect(celulas[i].textContent?.trim()).toBe('');
    }
    // E nenhuma delas diz 0,00.
    expect(linha.textContent).not.toContain('0,00');
    expect(linha.getAttribute('title') ?? '').toContain('não operação');
  });

  it('o codigo bruto da corretora continua visivel, para a conferencia', () => {
    // O comentario e codigo interno da XM, e nao "Deposit via PIX". Esconder
    // atras do rotulo traduzido impede o operador de bater com o MT5.
    const { container } = render(<HistoryTab />);
    expect(container.textContent).toContain('CD-AST-PIC 265376085');
    expect(container.textContent).toContain('Credit-In-100%-$100-NewClients');
  });

  it('a FORMA do deposito aparece na MESMA celula do comentario', () => {
    /*
      O dono pediu "se possivel tambem identificar formas de depositos e
      saques". A forma e lida do comentario (`formaMovimentacao`), e vai na
      MESMA celula: duas colunas para o mesmo dado sao dois lugares para
      divergirem quando o comentario mudar.
    */
    const { container } = render(<HistoryTab />);
    const formas = Array.from(container.querySelectorAll('.hist-forma'));
    // Uma por movimentacao de saldo: 3 na conta 391773676.
    expect(formas).toHaveLength(3);
    // E cada uma esta na MESMA celula do comentario, e nao numa coluna solta.
    for (const forma of formas) {
      expect(forma.closest('td')?.className).toContain('hist-comentario');
    }
  });

  it('MEDIDO: `CD-AST-PIC` e lido como PIX, e nao como "nao informada"', () => {
    /*
      A XM escreve **PIC**, nao `PIX`, nos comentarios da conta 391773676
      (`CD-AST-PIC 265376085`, `EXP05-AST-PIC 265376085`). Com o padrao antigo
      (`\bpix\b` so) as tres movimentacoes saiam como `nao informada`: o metodo
      estava escrito no comentario e a tela dizia que nao sabia.

      Este e o teste que fixa a equivalencia. Se a XM mudar a sigla, ele
      reprova — em vez de a tela voltar a mentir em silencio.
    */
    const { container } = render(<HistoryTab />);
    const linha = linhaDoBilhete(container, '260002613');
    expect(linha.querySelector('.hist-forma')?.textContent?.trim()).toBe('PIX');
  });

  it('PROVA NEGATIVA: `PIC` com fronteira nao casa com palavra que contém "pic"', () => {
    /*
      A fronteira e testada no modulo, em `historico.test.ts`, com `PICASSO`,
      `PICTURE` e `epic`. Aqui o que se prova e o EFEITO na tela: os dois
      depositos da conta, que trazem `PIC` no comentario, sao lidos como PIX.

      E o `Credit-In-100%-$100-NewClients` NAO vira Pix: nenhum padrao casa com
      esse texto, porque ele nao nomeia metodo nenhum — e o que se mostra e a
      ausencia, com o motivo no `title`, e nao um metodo inventado.
    */
    const { container } = render(<HistoryTab />);
    const valores = Array.from(container.querySelectorAll('.hist-forma')).map((n) =>
      n.textContent?.trim(),
    );
    expect(valores).toEqual(['PIX', 'PIX', 'nao informada']);
    // E a unica celula apagada e a do comentario que nao diz o metodo.
    expect(container.querySelectorAll('.hist-forma.vazia')).toHaveLength(1);
  });

  it('PROVA NEGATIVA: forma desconhecida aparece apagada, e NAO some', () => {
    // Ausencia de informacao nao e erro. Um comentario que nao nomeia metodo
    // tem que dizer "nao informada" com o motivo no title — nunca nada, que o
    // operador leria como "a corretora nao mandou nada".
    devolver({
      deals: [{ ...DEPOSITO_552, comment: 'Balance operation 4471' }],
    });
    const { container } = render(<HistoryTab />);
    const forma = container.querySelector('.hist-forma');
    expect(forma?.textContent?.trim()).toBe('nao informada');
    expect(forma?.className).toContain('vazia');
    expect(forma?.getAttribute('title')).toContain('não informou o método');
  });

  it('PROVA NEGATIVA: operacao NAO tem forma de deposito', () => {
    // Uma compra nao tem forma de deposito, e escrever "PIX" numa operacao de
    // mercado seria inventar o metodo.
    const { container } = render(<HistoryTab />);
    const formas = linhaDaOperacao(container).querySelectorAll('.hist-forma');
    expect(formas).toHaveLength(0);
  });
});

// ==========================================================================
// A LINHA DE RESUMO
// ==========================================================================
describe('HistoryTab — a linha de resumo, com os rotulos da captura', () => {
  beforeEach(() => devolver());
  afterEach(() => cleanup());

  it('reproduz os 5 numeros da captura', () => {
    const { container } = render(<HistoryTab />);
    const resumo = container.querySelector('.hist-resumo') as HTMLElement;
    // `Lucro: 2,01  Credito: 5,62  Recarregar: 5,62  Retirada: 0,00  Saldo: 13,25`
    expect(resumo.textContent).toContain('Lucro');
    expect(resumo.textContent).toContain('Credito');
    expect(resumo.textContent).toContain('Recarregar');
    expect(resumo.textContent).toContain('Retirada');
    expect(resumo.textContent).toContain('Saldo');

    const itens = itensDoResumo(resumo);
    expect(numeroRenderizado(itens.Lucro)).toBeCloseTo(2.01, 6);
    // Recarregar = 5,52 + 0,10 (os dois `balance`). Credito = o `credit` de 5,62.
    expect(numeroRenderizado(itens.Recarregar)).toBeCloseTo(5.62, 6);
    expect(numeroRenderizado(itens.Credito)).toBeCloseTo(5.62, 6);
    expect(numeroRenderizado(itens.Retirada)).toBe(0);
  });

  it('e um tfoot, nao um cartao separado', () => {
    // No MT5 a linha fica grudada na tabela. Um cartao acima seria um segundo
    // lugar para o mesmo numero.
    const { container } = render(<HistoryTab />);
    expect(container.querySelector('table.history-deals tfoot.hist-resumo')).not.toBeNull();
  });

  it('PROVA NEGATIVA: entrada de saldo NAO entra no Lucro', () => {
    // `Lucro: 2,01` e so a operacao. Somar os 11,24 das movimentacoes daria
    // 13,25 — que e o capital da conta, nao o que o trading produziu.
    const { container } = render(<HistoryTab />);
    const resumo = container.querySelector('.hist-resumo') as HTMLElement;
    const itens = itensDoResumo(resumo);
    const lucro = numeroRenderizado(itens.Lucro);
    const entrada = numeroRenderizado(itens.Credito) + numeroRenderizado(itens.Recarregar);
    expect(entrada).toBeCloseTo(11.24, 6);
    expect(lucro).not.toBeCloseTo(entrada, 6);
    expect(lucro).not.toBeCloseTo(13.25, 6);
  });

  it('Saldo fica VAZIO: o historico nao sabe o saldo da conta', () => {
    // MEDIDO: `Saldo: 13,25` e o CAPITAL da conta (o painel da XM mostra Saldo
    // $7,63 e Capital $13,25) e a soma das movimentacoes do dia da 11,24.
    // Nenhum dos tres e o mesmo numero, e o historico nao tem como saber qual
    // o operador quer. Mostrar a soma ali diria "saldo" para um numero que a
    // corretora nao mediu.
    const { container } = render(<HistoryTab />);
    const resumo = container.querySelector('.hist-resumo') as HTMLElement;
    const saldos = resumo.querySelectorAll('.hist-resumo-item strong');
    const ultimo = saldos[saldos.length - 1];
    expect(ultimo.textContent?.trim()).toBe('—');
  });

  it('a contagem fala de operacoes E de movimentacoes', () => {
    const { container } = render(<HistoryTab />);
    const contagem = (container.querySelector('.history-count')?.textContent ?? '').replace(
      /\s+/g,
      '',
    );
    expect(contagem).toContain('1operação');
    expect(contagem).toContain('3movimentações');
  });
});

// ==========================================================================
// ESTADO VAZIO E ERRO
// ==========================================================================
describe('HistoryTab — sem dado, a tela diz', () => {
  afterEach(() => cleanup());

  it('sem deals mostra o estado vazio, nao uma linha sem conteudo', () => {
    devolver({ deals: [] });
    const { container } = render(<HistoryTab />);
    const linhas = container.querySelectorAll('.history-deals tbody tr');
    expect(linhas).toHaveLength(1);
    expect((linhas[0].textContent ?? '').trim()).toBe('Nenhum registro no período.');
  });

  it('com erro, a tela mostra o motivo em vez de "nenhum registro"', () => {
    // "Nenhum registro no período." com a corretora fora do ar é uma tela que
    // mente: o operador conclui que não houve nada.
    devolver({ deals: [], erro: 'mt5: indisponivel' });
    const { container } = render(<HistoryTab />);
    expect(container.textContent).toContain('mt5: indisponivel');
    expect(container.textContent).not.toContain('Nenhum registro no período.');
  });

  it('a linha de resumo mostra zeros, e nao quebra, sem dado nenhum', () => {
    devolver({ deals: [] });
    const { container } = render(<HistoryTab />);
    const resumo = container.querySelector('.hist-resumo') as HTMLElement;
    expect(resumo.querySelectorAll('.hist-resumo-item')).toHaveLength(5);
  });
});

// ==========================================================================
// AGRUPAMENTO POR DIA
// ==========================================================================
describe('HistoryTab — agrupamento por dia, como a aba do MT5', () => {
  afterEach(() => cleanup());

  it('a faixa de dia conta LINHAS, e diz que sao linhas', () => {
    // Com operacao e movimentacao na mesma tabela, "3 operacoes" numa faixa que
    // tem duas movimentacoes seria um numero errado.
    devolver({ deals: CONTA });
    const { container } = render(<HistoryTab />);
    const faixas = Array.from(container.querySelectorAll('.history-deals .hist-dia-faixa')).map(
      (n) => n.textContent?.replace(/\s+/g, ' ').trim() ?? '',
    );
    expect(faixas.length).toBeGreaterThan(0);
    for (const faixa of faixas) {
      expect(faixa).toMatch(/\d+ linhas?/);
    }
  });

  it('a data completa fica no title da celula de hora', () => {
    devolver({ deals: CONTA });
    const { container } = render(<HistoryTab />);
    const celula = container.querySelector('.history-when') as HTMLElement;
    expect(celula.getAttribute('title') ?? '').toContain(
      String(new Date().getFullYear()),
    );
  });

  it('posicao ABERTA diz que nao tem fechamento conhecido', () => {
    // Sem deal de saida, repetir a hora de abertura na coluna de fechamento
    // diria que a posicao fechou no minuto em que abriu.
    //
    // Com um deal so, o Bilhete e o da ABERTURA (24503921), que e o unico
    // ticket que existe. A captura mostra 24503922 porque a posicao FECHOU e o
    // deal de fechamento existe.
    devolver({ deals: [ABERTURA] });
    const { container } = render(<HistoryTab />);
    const celulas = linhasDeDados(container)[0].querySelectorAll('td');
    expect(celulas[2].textContent?.trim()).toBe('24503921');
    expect(celulas[9].textContent?.trim()).toBe('');
    expect(celulas[9].getAttribute('title')).toBe('posição sem fechamento conhecido');
  });
});

describe('HistoryTab — o periodo padrao mostra o dado', () => {
  afterEach(() => cleanup());

  /** Container da ultima renderizacao. */
  const container = (): HTMLElement => document.body as HTMLElement;

  it('abre em 30 dias, e nao em "Hoje"', () => {
    // MEDIDO na conta 391773676 em 05/10/2026: os 5 deals sao de 04/10 e 05/10.
    // Com "Hoje" a tabela abria quase vazia e o dono leu "as recargas nao
    // carregam".
    devolver();
    render(<HistoryTab />);
    expect(seletorDePeriodo(container()).value).toBe('30');
  });

  it('ainda oferece "Hoje" e "Tudo" para quem quiser estreitar', () => {
    devolver();
    render(<HistoryTab />);
    const opcoes = Array.from(seletorDePeriodo(container()).options).map((o) => o.textContent);
    expect(opcoes).toContain('Hoje');
    expect(opcoes).toContain('Tudo');
  });
});

/**
 * O seletor de PERÍODO, sem depender de posição no DOM.
 *
 * `select:last-of-type` não funciona aqui: cada `<select>` está dentro do seu
 * próprio `<label class="field">`, e portanto é o ÚLTIMO select do seu pai — os
 * três casam com o seletor e a busca devolve o de corretora.
 */
function seletorDePeriodo(ct: HTMLElement): HTMLSelectElement {
  const achado = Array.from(ct.querySelectorAll<HTMLSelectElement>('.history-filters select')).find(
    (s) => Array.from(s.options).some((o) => o.textContent === '30 dias'),
  );
  if (!achado) throw new Error('seletor de periodo nao encontrado');
  return achado;
}

// ==========================================================================
// AJUDAS
// ==========================================================================

/**
 * Linhas de dado, sem a faixa de dia e sem o rodapé.
 *
 * A faixa de dia é `tr.hist-dia-faixa` dentro do `tbody` do dia, e o rodapé é um
 * `tfoot`. Sem esta distinção, contar `tr` contaria a faixa e passaria a
 * proteger o número errado — que foi o defeito de um teste anterior.
 */
function linhasDeDados(container: HTMLElement): Element[] {
  return Array.from(
    container.querySelectorAll('.history-deals tbody tr:not(.hist-dia-faixa)'),
  );
}

/** A linha da operação, pelo `position_id` da captura. */
function linhaDaOperacao(container: HTMLElement): HTMLElement {
  const achada = linhasDeDados(container).find((n) =>
    n.querySelectorAll('td')[2]?.textContent?.trim() === '24503922',
  );
  if (!achada) throw new Error('linha da operacao 24503922 nao encontrada');
  return achada as HTMLElement;
}

/** A linha de um bilhete de movimentação. */
function linhaDoBilhete(container: HTMLElement, bilhete: string): HTMLElement {
  const achada = linhasDeDados(container).find(
    (n) => n.querySelectorAll('td')[2]?.textContent?.trim() === bilhete,
  );
  if (!achada) throw new Error(`linha do bilhete ${bilhete} nao encontrada`);
  return achada as HTMLElement;
}

/** Os valores da linha de resumo, pelo rótulo. */
function itensDoResumo(resumo: HTMLElement): Record<string, HTMLElement> {
  const mapa: Record<string, HTMLElement> = {};
  resumo.querySelectorAll('.hist-resumo-item').forEach((item) => {
    const rotulo = item.querySelector('.hist-resumo-rotulo')?.textContent?.trim() ?? '';
    const valor = item.querySelector('strong') as HTMLElement;
    mapa[rotulo] = valor;
  });
  return mapa;
}

/**
 * Lê o número que a célula MOSTRA, e não o que o componente recebeu.
 *
 * `fmtNum` formata em pt-BR: 2300 sai como "2.300,00". Remover só vírgulas e
 * pontos não resolve — "2.300,00" viraria "230000", que parece um valor
 * diferente e faz o teste passar por acidente. Aqui o separador de milhar vai
 * fora primeiro, a vírgula vira ponto, e o número é lido.
 */
function numeroRenderizado(celula: Element | null | undefined): number {
  const texto = (celula?.textContent ?? '').replace(/[^\d,.-]/g, '');
  if (!texto) return Number.NaN;
  return Number(texto.replace(/\./g, '').replace(',', '.'));
}

// ==========================================================================
// `agruparPorDia` — a ordem do histórico é preservada
// ==========================================================================
describe('agruparPorDia — a ordem do histórico é preservada', () => {
  it('não reordena: só insere a faixa quando o dia muda', () => {
    // O histórico vem do gateway na ordem que ele devolveu. Reordenar por data
    // mudaria o que "primeira linha" significa para quem lê.
    const linhas = [
      { data: '2026-10-05T14:00:00', id: 'A' },
      { data: '2026-10-05T10:00:00', id: 'B' },
      { data: '2026-10-04T22:00:00', id: 'C' },
    ];
    const grupos = agruparPorDia(linhas, (l) => l.data);
    expect(grupos).toHaveLength(2);
    // A e B no mesmo grupo, NA ordem em que chegaram (A antes de B, mesmo que
    // A seja mais tarde).
    expect(grupos[0].linhas.map((l) => l.id)).toEqual(['A', 'B']);
    expect(grupos[1].linhas.map((l) => l.id)).toEqual(['C']);
  });

  it('um dia não volta a aparecer depois de outro dia', () => {
    // Feed com paginação pode devolver o dia 05, o dia 04 e o dia 05 de novo.
    // Aqui viram TRÊS grupos — que é a leitura honesta do que veio, e o
    // operador vê a quebra. Fundir os dois 05 em um só esconderia que houve
    // uma quebra na origem.
    const linhas = [
      { data: '2026-10-05T14:00:00', id: 'A' },
      { data: '2026-10-04T22:00:00', id: 'B' },
      { data: '2026-10-05T09:00:00', id: 'C' },
    ];
    expect(agruparPorDia(linhas, (l) => l.data)).toHaveLength(3);
  });

  it('linha sem data não some: vira o grupo "sem data"', () => {
    const linhas = [
      { data: '', id: 'A' },
      { data: '2026-10-05T14:00:00', id: 'B' },
      { data: '', id: 'C' },
    ];
    const grupos = agruparPorDia(linhas, (l) => l.data);
    expect(grupos).toHaveLength(3);
    expect(grupos[0].chave).toBe('sem-data');
    expect(grupos[0].linhas.map((l) => l.id)).toEqual(['A']);
  });
});