// @vitest-environment jsdom
// Seletor de ativo do painel de modelos.
//
// O bug corrigido aqui: o backend de /api/ai/predict le APENAS
// symbol + timeframe e ignora model_id (fastapi_gateway.py). O painel mandava
// `symbol = selectedSymbol || 'XAUUSD'`, entao escolher um modelo de BTCUSD
// ainda mandava XAUUSD: a previsao saia do modelo errado ou falhava, e a tela
// só parecia funcionar em XAUUSD.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

vi.mock('../lib/notify', () => ({ notify: vi.fn() }));

const { default: RobotModelPanel } = await import('./RobotModelPanel');
const { useAppStore } = await import('../hooks/useAppStore');

const MODELOS = [
  { id: 'XAUUSD_H1', symbol: 'XAUUSD', timeframe: 'H1', accuracy: 0.71, edge: 0.11, pkl_present: true, publicable: true },
  { id: 'XAUUSD_H4', symbol: 'XAUUSD', timeframe: 'H4', accuracy: 0.66, edge: 0.07, pkl_present: true, publicable: true },
  { id: 'BTCUSD_H1', symbol: 'BTCUSD', timeframe: 'H1', accuracy: 0.62, edge: 0.04, pkl_present: true, publicable: true },
  { id: 'BTCUSD_H4', symbol: 'BTCUSD', timeframe: 'H4', accuracy: 0.58, edge: 0.03, pkl_present: true, publicable: true },
  { id: 'EURUSD_H1', symbol: 'EURUSD', timeframe: 'H1', accuracy: 0.6, edge: 0.05, pkl_present: true, publicable: true },
];

const chamadas: string[] = [];
const fetchMock = vi.fn(async (url: string) => {
  chamadas.push(String(url));
  if (String(url).includes('/api/ai/trained')) {
    return { ok: true, json: async () => ({ models: MODELOS, cpu_threads: 4 }) };
  }
  return { ok: true, json: async () => ({ signal: 'BUY', confidence: 81, available: true }) };
});

function montar() {
  return render(<RobotModelPanel />);
}

describe('RobotModelPanel — ativo e modelo coerentes', () => {
  beforeEach(() => {
    chamadas.length = 0;
    fetchMock.mockClear();
    vi.stubGlobal('fetch', fetchMock);
    useAppStore.setState({ selectedSymbol: '' });
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('lista so os ativos que tem modelo, com XAUUSD na frente', async () => {
    montar();
    const ativo = await screen.findByLabelText('Ativo do robo') as HTMLSelectElement;
    await waitFor(() => expect(ativo.options.length).toBe(3));
    expect(ativo.value).toBe('XAUUSD');
    expect([...ativo.options].map((o) => o.value)).toEqual(['XAUUSD', 'BTCUSD', 'EURUSD']);
  });

  it('envia o symbol do ativo escolhido, nao o XAUUSD do store', async () => {
    montar();
    const ativo = await screen.findByLabelText('Ativo do robo') as HTMLSelectElement;
    await waitFor(() => expect(ativo.options.length).toBe(3));
    fireEvent.change(ativo, { target: { value: 'BTCUSD' } });

    await waitFor(() => {
      const modelo = screen.getByLabelText('Modelo do robo') as HTMLSelectElement;
      expect(modelo.value).toBe('BTCUSD_H1');
    });

    fireEvent.click(screen.getByRole('button', { name: /Prever BTCUSD/ }));
    await waitFor(() => expect(chamadas.some((u) => u.includes('/api/ai/predict'))).toBe(true));

    const previsao = chamadas.find((u) => u.includes('/api/ai/predict')) ?? '';
    expect(previsao).toContain('symbol=BTCUSD');
    expect(previsao).toContain('timeframe=H1');
    expect(previsao).not.toContain('symbol=XAUUSD');
  });

  it('trocar de ativo nao deixa o modelo do ativo anterior', async () => {
    montar();
    const ativo = await screen.findByLabelText('Ativo do robo') as HTMLSelectElement;
    await waitFor(() => expect(ativo.options.length).toBe(3));
    fireEvent.change(ativo, { target: { value: 'BTCUSD' } });
    await waitFor(() => expect((screen.getByLabelText('Modelo do robo') as HTMLSelectElement).value).toBe('BTCUSD_H1'));

    fireEvent.change(ativo, { target: { value: 'EURUSD' } });
    await waitFor(() => expect((screen.getByLabelText('Modelo do robo') as HTMLSelectElement).value).toBe('EURUSD_H1'));
    expect(useAppStore.getState().selectedSymbol).toBe('EURUSD');
  });
});
