// @vitest-environment jsdom
// Mesa XM+MT5: ticket manual SEM seletor de corretora (o defeito que tirou a
// ordem manual da aba em 2026-09-30). Opera o escopo ativo, exige confirmacao,
// e manda volume/sl/tp + confirm:true para /api/trade/order.
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import MesaXM from './MesaXM';

const chamadas: Array<{ url: string; body: Record<string, unknown> }> = [];

vi.mock('../hooks/queries', () => ({
  useAutoState: () => ({
    data: { ativo: false, simbolo: 'GOLD', timeframe: 'H1', broker: 'mt5', market: 'metals', ciclo: 0 },
  }),
}));

vi.mock('./LatenciaBar', () => ({ default: () => <div data-testid="latencias" /> }));

function renderMesa() {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <MesaXM />
    </QueryClientProvider>,
  );
}

describe('MesaXM', () => {
  beforeEach(() => {
    chamadas.length = 0;
    window.localStorage.setItem('xau-active-account', 'mt5:metals');
    vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body ?? '{}'));
      chamadas.push({ url: String(url), body });
      if (String(url).includes('/api/universal/quotes')) {
        return { ok: true, json: async () => ({ quotes: [{ price: 4140.6 }] }) };
      }
      return { ok: true, json: async () => ({ ok: true }) };
    });
    vi.stubGlobal('confirm', () => true);
  });
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('nao tem seletor de corretora nem de mercado', async () => {
    renderMesa();
    await screen.findByText(/GOLD/);
    expect(screen.queryByLabelText(/corretora/i)).toBeNull();
    expect(screen.queryByLabelText(/mercado/i)).toBeNull();
  });

  it('comprar envia volume, sl, tp e confirm para /api/trade/order', async () => {
    const { container } = renderMesa();
    await screen.findByText(/GOLD/);
    fireEvent.change(screen.getByLabelText('Quantidade em lotes'), { target: { value: '0.01' } });
    fireEvent.change(screen.getByLabelText('Stop loss'), { target: { value: '4130' } });
    fireEvent.change(screen.getByLabelText('Take profit'), { target: { value: '4150' } });
    fireEvent.click(container.querySelector('.mesa-enviar') as HTMLButtonElement);
    await waitFor(() => expect(chamadas.some((c) => c.url.includes('/api/trade/order'))).toBe(true));
    const ordem = chamadas.find((c) => c.url.includes('/api/trade/order'))!;
    expect(ordem.body.side).toBe('BUY');
    expect(ordem.body.volume).toBe(0.01);
    expect(ordem.body.sl).toBe(4130);
    expect(ordem.body.tp).toBe(4150);
    expect(ordem.body.confirm).toBe(true);
    expect(ordem.body.request_id).toBeTruthy();
  });

  it('vender troca o lado', async () => {
    const { container } = renderMesa();
    await screen.findByText(/GOLD/);
    fireEvent.click(screen.getByRole('button', { name: 'Vender' }));
    fireEvent.change(screen.getByLabelText('Quantidade em lotes'), { target: { value: '0.01' } });
    fireEvent.change(screen.getByLabelText('Stop loss'), { target: { value: '4150' } });
    fireEvent.change(screen.getByLabelText('Take profit'), { target: { value: '4130' } });
    fireEvent.click(container.querySelector('.mesa-enviar') as HTMLButtonElement);
    await waitFor(() => expect(chamadas.some((c) => c.url.includes('/api/trade/order'))).toBe(true));
    const ordem = chamadas.find((c) => c.url.includes('/api/trade/order'))!;
    expect(ordem.body.side).toBe('SELL');
  });

  it('mostra a barra de latencias ao vivo', async () => {
    renderMesa();
    await screen.findByTestId('latencias');
  });
  it('os presets de distancia preenchem SL e TP', async () => {
    // O dono pediu "tp sl facil de configurar". O preset tem que PREENCHER os
    // campos: o operador ve o resultado e ajusta, em vez de aceitar numero
    // magico que ele nao escolheu.
    const { container } = renderMesa();
    await screen.findByText(/GOLD/);
    const passo = 4140.6 * 0.001; // 0,1% do preco
    const esperadoSl = Number((passo * 1).toPrecision(6));
    const esperadoTp = Number((passo * 3).toPrecision(6));
    fireEvent.click(screen.getByRole('button', { name: '1:3' }));
    await waitFor(() => {
      expect((screen.getByLabelText('Stop loss') as HTMLInputElement).value).toBe(String(esperadoSl));
    });
    expect((screen.getByLabelText('Take profit') as HTMLInputElement).value).toBe(String(esperadoTp));
    // E o botao nao trava os campos: o operador ainda ajusta.
    const sl = screen.getByLabelText('Stop loss') as HTMLInputElement;
    expect(sl.readOnly).toBe(false);
    expect(container.querySelectorAll('.mesa-presets button').length).toBe(4);
  });

  it('o passo da distancia muda com o ativo, e nao e um numero fixo', async () => {
    // Um "passo" fixo seria 0,2% no ouro e 900% no EURUSD. O preset tem que
    // sair da ESCALA do preco.
    const { container } = renderMesa();
    await screen.findByText(/GOLD/);
    const emOuro = screen.getByText(/passo/);
    expect(emOuro.textContent).toContain('4.14'); // 0,1% de 4140,6
    fireEvent.click(screen.getByRole('button', { name: '1:1' }));
    await waitFor(() => expect(container.querySelector('.mesa-presets-passo')).toBeTruthy());
  });

  it('o lote aceita de 0.01 a 10 e recusa fora da faixa', async () => {
    // O dono definiu 0,01 como minimo e 10,00 como maximo. O input e a
    // validacao tem que dizer a MESMA faixa: se divergirem, a tela aceita e
    // o gateway recusa.
    renderMesa();
    await screen.findByText(/GOLD/);
    const campo = screen.getByLabelText('Quantidade em lotes') as HTMLInputElement;
    expect(campo.min).toBe('0.01');
    expect(campo.max).toBe('10');
  });

  it('o botao de enviar repete o lado do clique final', async () => {
    // "Comprar" e "Vender" aparecem duas vezes: o botao de LADO e o de ENVIAR.
    // O de enviar e o que o operador clica com pressa, e precisa da MESMA cor
    // do lado escolhido — senao ele envia oposto do que pensou.
    const { container } = renderMesa();
    await screen.findByText(/GOLD/);
    const enviar = () => container.querySelector('.mesa-enviar') as HTMLButtonElement;
    expect(enviar().className).toContain('is-buy');
    fireEvent.click(screen.getByRole('button', { name: 'Vender' }));
    expect(enviar().className).toContain('is-sell');
  });
});
