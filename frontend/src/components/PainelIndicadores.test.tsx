// @vitest-environment jsdom
// O PAINEL DE INDICADORES (13/10/2026)
// =====================================
// PEDIDO DO DONO: "lista com botao igual dos modelos para indicadores".
// Cada indicador e um item com nome, parametros, o que mede e botao
// Liga/Desliga — a mesma leitura dos cards de modelo.
//
// O painel NAO desenha: ele chama `onAlternar`, e o dono do grafico conecta
// nas props do `PriceChart`. Bollinger e Estocastico aparecem como ROTEIRO
// (texto, nunca botao): sem calculo nem desenho, botao seria o controle que
// parece funcionar e nao funciona (AGENTS.md 9).
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import PainelIndicadores from './PainelIndicadores';

afterEach(() => {
  cleanup();
});

describe('PainelIndicadores — a lista com botao', () => {
  it('PROVA: os tres que funcionam tem botao com estado', () => {
    const alternar = vi.fn();
    render(<PainelIndicadores ativos={{ ema: true, rsi: false, macd: false }} onAlternar={alternar} />);

    const ema = screen.getByRole('button', { name: 'Desligar EMA' });
    expect(ema.getAttribute('aria-pressed')).toBe('true');
    expect(ema.textContent).toBe('Ligado');

    const rsi = screen.getByRole('button', { name: 'Ligar RSI' });
    expect(rsi.getAttribute('aria-pressed')).toBe('false');

    expect(screen.getByRole('button', { name: 'Ligar MACD' })).toBeTruthy();
  });

  it('PROVA: clicar chama onAlternar com o id', () => {
    const alternar = vi.fn();
    render(<PainelIndicadores ativos={{ ema: false, rsi: false, macd: false }} onAlternar={alternar} />);

    fireEvent.click(screen.getByRole('button', { name: 'Ligar RSI' }));
    expect(alternar).toHaveBeenCalledTimes(1);
    expect(alternar).toHaveBeenCalledWith('rsi');
  });

  it('PROVA NEGATIVA: o roteiro nao tem botao', () => {
    // Bollinger e Estocastico ainda nao tem calculo nem desenho. Se um dia
    // ganharem botao aqui sem o dono do grafico conectar, este teste reprova
    // — e com razao: seria controle sem consumidor.
    const alternar = vi.fn();
    const { container } = render(
      <PainelIndicadores ativos={{ ema: false, rsi: false, macd: false }} onAlternar={alternar} />,
    );

    const botoes = Array.from(container.querySelectorAll('button')).map((b) => b.textContent);
    expect(botoes).toHaveLength(3);
    const roteiro = container.querySelector('.painel-indicadores-roteiro')!;
    expect(roteiro.querySelector('button')).toBeNull();
    expect(roteiro.textContent).toContain('Bollinger');
    expect(roteiro.textContent).toContain('Estocástico');
  });
});
