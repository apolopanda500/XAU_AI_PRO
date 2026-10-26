// @vitest-environment jsdom
/*
  CARTEIRA: O RESULTADO ABERTO APARECE, E COM O SINAL (23/10/2026)

  MEDIDO antes: `loadPortfolio` somava `profit` das posicoes em `Row.pnl`, mas
  NENHUMA coluna lia esse campo. O operador via saldo, disponivel, moeda e
  numero de posicoes — e o resultado aberto, que e o numero que diz se a conta
  esta ganhando, ficava calculado e invisivel.

  Pior: o formatador exigia `n >= 0`. Como `--` nesta app significa "o gateway
  nao mandou", uma posicao perdedora aparecia exatamente igual a uma conta sem
  dados. O sinal e a informacao; esconder o negativo e o defeito.

  Este arquivo mede os dois: o campo RENDERIZADO e o SINAL. A prova negativa e
  a segunda posicao (perdedora) — se o numero voltar a passar por um formatador
  que rejeita negativo, ela vira `--` e o teste reprova.
*/
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const { default: PortfolioHomeSafe } = await import('./PortfolioHomeSafe');

function respostaConta(broker: string) {
  if (broker === 'mt5') {
    return {
      saldo: -12.5,
      disponivel: 40,
      posicoes: [
        { profit: 10 },
        { profit: -35 },
      ],
    };
  }
  if (broker === 'binance') {
    return { saldo: 250, disponivel: 250, posicoes: [{ profit: 12 }] };
  }
  return { saldo: 0, disponivel: 0, posicoes: [] };
}

const fetchMock = vi.fn(async (url: string | URL) => {
  const texto = String(url);
  const broker = /broker=([a-z0-9]+)/.exec(texto)?.[1] ?? '';
  const dados = respostaConta(broker);
  if (texto.includes('/api/universal/account')) {
    return {
      ok: true,
      json: async () => ({
        ok: true,
        account: { balance: dados.saldo, available: dados.disponivel, currency: 'USD' },
      }),
    };
  }
  return { ok: true, json: async () => ({ ok: true, positions: dados.posicoes }) };
});

function renderizar() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <PortfolioHomeSafe />
    </QueryClientProvider>,
  );
}

function linhaDe(nome: string): HTMLElement {
  const linhas = Array.from(document.querySelectorAll('tbody tr'));
  const achada = linhas.find((linha) => linha.textContent?.includes(nome));
  if (!achada) throw new Error(`linha ${nome} ausente`);
  return achada as HTMLElement;
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  fetchMock.mockClear();
});

describe('Carteira — resultado aberto', () => {
  it('tem coluna propria e mostra o resultado com o sinal', async () => {
    renderizar();
    await waitFor(() => expect(linhaDe('MT5').textContent).toContain('-25,00'));

    // A coluna existe no cabecalho; sem ela o numero nao tem onde aparecer.
    expect(screen.getByText('Resultado aberto')).toBeTruthy();
  });

  it('posicao perdedora NAO vira "--": o sinal e a informacao', async () => {
    renderizar();
    await waitFor(() => expect(linhaDe('MT5').textContent).toContain('-25,00'));
    const celula = linhaDe('MT5').querySelector('td.neg');
    expect(celula?.textContent).toBe('-25,00');
  });

  it('resultado positivo leva "+" e classe pos', async () => {
    renderizar();
    await waitFor(() => expect(linhaDe('Binance').textContent).toContain('+12,00'));
    expect(linhaDe('Binance').querySelector('td.pos')?.textContent).toBe('+12,00');
  });

  it('saldo negativo aparece como numero, nao como ausencia', async () => {
    renderizar();
    await waitFor(() => expect(linhaDe('MT5').textContent).toContain('-12,50'));
    expect(linhaDe('MT5').textContent).not.toContain('--');
  });
});
