// @vitest-environment jsdom
// O PAINEL DE INDICADORES (13/10/2026, ampliado em 25/10/2026)
// ==============================================================
// PEDIDO DO DONO: "lista com botao igual dos modelos para indicadores".
// Cada indicador e um item com nome, parametros, o que mede e botao
// Liga/Desliga — a mesma leitura dos cards de modelo.
//
// O painel NAO desenha: ele chama `onAlternar`, e o dono do grafico conecta
// nas props do `PriceChart`. Os seis itens abaixo tem consumidor real no
// grafico; Estocastico aparece como ROTEIRO (texto, nunca botao): sem calculo
// nem desenho, botao seria o controle que parece funcionar e nao funciona
// (AGENTS.md 9).
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
};

afterEach(() => {
  cleanup();
});

describe('PainelIndicadores — a lista com botao', () => {
  it('PROVA: os seis que funcionam tem botao com estado', () => {
    const alternar = vi.fn();
    render(<PainelIndicadores ativos={{ ...TODOS_DESLIGADOS, ema: true }} onAlternar={alternar} />);

    const ema = screen.getByRole('button', { name: 'Desligar EMA' });
    expect(ema.getAttribute('aria-pressed')).toBe('true');
    expect(ema.textContent).toBe('Ligado');

    for (const nome of ['SMA 20', 'Bollinger', 'VWAP', 'RSI', 'MACD']) {
      expect(screen.getByRole('button', { name: `Ligar ${nome}` })).toBeTruthy();
    }
  });

  it('PROVA: clicar chama onAlternar com o id', () => {
    const alternar = vi.fn();
    render(<PainelIndicadores ativos={TODOS_DESLIGADOS} onAlternar={alternar} />);

    fireEvent.click(screen.getByRole('button', { name: 'Ligar RSI' }));
    fireEvent.click(screen.getByRole('button', { name: 'Ligar Bollinger' }));
    expect(alternar).toHaveBeenNthCalledWith(1, 'rsi');
    expect(alternar).toHaveBeenNthCalledWith(2, 'bollinger');
  });

  it('PROVA NEGATIVA: o roteiro nao tem botao', () => {
    // Estocastico ainda nao tem calculo nem desenho. Se um dia ganhar botao
    // aqui sem o dono do grafico conectar, este teste reprova — e com razao:
    // seria controle sem consumidor.
    const alternar = vi.fn();
    const { container } = render(
      <PainelIndicadores ativos={TODOS_DESLIGADOS} onAlternar={alternar} />,
    );

    const botoes = Array.from(container.querySelectorAll('button')).map((b) => b.textContent);
    expect(botoes).toHaveLength(6);
    const roteiro = container.querySelector('.painel-indicadores-roteiro')!;
    expect(roteiro.querySelector('button')).toBeNull();
    expect(roteiro.textContent).toContain('Estocástico');
  });
});
