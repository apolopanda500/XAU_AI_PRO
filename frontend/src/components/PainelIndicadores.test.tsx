// @vitest-environment jsdom
// O PAINEL DE INDICADORES (13/10/2026, ampliado em 25/10/2026)
// ==============================================================
// PEDIDO DO DONO: "lista com botao igual dos modelos para indicadores".
// Cada indicador e um item com nome, parametros, o que mede e botao
// Liga/Desliga — a mesma leitura dos cards de modelo.
//
// O painel NAO desenha: ele chama `onAlternar`, e o dono do grafico conecta
// nas props do `PriceChart`. Os itens abaixo tem consumidor real no grafico
// (EMA/SMA/Bollinger/VWAP pelos `extras`, RSI/MACD/Estocastico pelos paineis
// de sub-canal). Estocastico ganhou botao no ciclo em que ganhou calculo e
// desenho — antes era ROTEIRO, sem calculo nem desenho (AGENTS.md 9).
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import PainelIndicadores from './PainelIndicadores';

const TODOS_DESLIGADOS = {
  ema: false,
  sma: false,
  bollinger: false,
  vwap: false,
  rsi: false,
  macd: false,
  stoch: false,
};

afterEach(() => {
  cleanup();
});

describe('PainelIndicadores — a lista com botao', () => {
  it('PROVA: os sete que funcionam tem botao com estado', () => {
    const alternar = vi.fn();
    render(<PainelIndicadores ativos={{ ...TODOS_DESLIGADOS, ema: true }} onAlternar={alternar} />);

    const ema = screen.getByRole('button', { name: 'Desligar EMA' });
    expect(ema.getAttribute('aria-pressed')).toBe('true');
    expect(ema.textContent).toBe('Ligado');

    for (const nome of ['SMA 20', 'Bollinger', 'VWAP', 'RSI', 'MACD', 'Estocástico']) {
      expect(screen.getByRole('button', { name: `Ligar ${nome}` })).toBeTruthy();
    }
  });

  it('PROVA: clicar chama onAlternar com o id', () => {
    const alternar = vi.fn();
    render(<PainelIndicadores ativos={TODOS_DESLIGADOS} onAlternar={alternar} />);

    fireEvent.click(screen.getByRole('button', { name: 'Ligar RSI' }));
    fireEvent.click(screen.getByRole('button', { name: 'Ligar Bollinger' }));
    fireEvent.click(screen.getByRole('button', { name: 'Ligar Estocástico' }));
    expect(alternar).toHaveBeenNthCalledWith(1, 'rsi');
    expect(alternar).toHaveBeenNthCalledWith(2, 'bollinger');
    expect(alternar).toHaveBeenNthCalledWith(3, 'stoch');
  });

  it('PROVA NEGATIVA: roteiro nao lista indicador que ja ganhou botao', () => {
    // Estocastico ganhou calculo e desenho: saiu do roteiro e entrou na lista
    // com botao. O roteiro nao pode mais listar item que ja tem item com botao.
    const alternar = vi.fn();
    const { container } = render(
      <PainelIndicadores ativos={TODOS_DESLIGADOS} onAlternar={alternar} />,
    );

    expect(container.querySelector('.painel-indicadores-roteiro')).toBeNull();
    expect(screen.getByRole('button', { name: 'Ligar Estocástico' })).toBeTruthy();
  });
});
