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
    renderMesa();
    await screen.findByText(/GOLD/);
    fireEvent.change(screen.getByLabelText('Quantidade em lotes'), { target: { value: '0.01' } });
    fireEvent.change(screen.getByLabelText('Stop loss'), { target: { value: '4130' } });
    fireEvent.change(screen.getByLabelText('Take profit'), { target: { value: '4150' } });
    fireEvent.click(screen.getByRole('button', { name: 'Enviar ordem' }));
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
    renderMesa();
    await screen.findByText(/GOLD/);
    fireEvent.click(screen.getByRole('button', { name: 'Vender' }));
    fireEvent.change(screen.getByLabelText('Quantidade em lotes'), { target: { value: '0.01' } });
    fireEvent.change(screen.getByLabelText('Stop loss'), { target: { value: '4150' } });
    fireEvent.change(screen.getByLabelText('Take profit'), { target: { value: '4130' } });
    fireEvent.click(screen.getByRole('button', { name: 'Enviar ordem' }));
    await waitFor(() => expect(chamadas.some((c) => c.url.includes('/api/trade/order'))).toBe(true));
    const ordem = chamadas.find((c) => c.url.includes('/api/trade/order'))!;
    expect(ordem.body.side).toBe('SELL');
  });

  it('mostra a barra de latencias ao vivo', async () => {
    renderMesa();
    await screen.findByTestId('latencias');
  });
});
