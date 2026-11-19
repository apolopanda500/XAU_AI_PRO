import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import OrderTicketPro from './OrderTicketPro';

/*
  A BOLETA NAO PODE ENVIAR O QUE O RISKGATE RECUSARIA.

  Cada caso aqui e uma das travas do AGENTS.md §4: simbolo vazio e recusa com
  motivo, Stop Loss zero e recusa, modo somente leitura nao envia, e o risco
  em dinheiro so existe quando a corretora informou o contrato (§9 — numero
  inventado e pior que numero ausente).

  PROVA NEGATIVA junto de cada trava: o caso que DEVERIA passar tambem esta
  testado, senao um componente que nunca envia estaria "verde".
*/
const base = {
  symbol: 'ATIVO',
  bid: 1.1,
  ask: 1.1001,
  digits: 4,
  point: 0.0001,
  ficha: { contractSize: 100000 },
  balance: 10_000,
  somenteLeitura: false,
};

const pontos = (rotulo: RegExp, valor: string) => {
  const campo = screen.getByLabelText(rotulo);
  fireEvent.change(campo, { target: { value: valor } });
};

describe('OrderTicketPro — travas de risco', () => {
  afterEach(cleanup);
  it('simbolo vazio e recusa com motivo, e o botao fica desabilitado', () => {
    render(<OrderTicketPro {...base} symbol="" />);
    expect(screen.getByText(/Sem simbolo/i)).toBeTruthy();
    const botao = screen.getByRole('button', { name: /SEM ENVIO/i }) as HTMLButtonElement;
    expect(botao.disabled).toBe(true);
  });

  it('sem Stop Loss a boleta recusa antes de qualquer clique', () => {
    render(<OrderTicketPro {...base} />);
    expect(screen.getByText(/Stop Loss obrigatorio/i)).toBeTruthy();
  });

  it('modo somente leitura aparece no selo e bloqueia o envio', () => {
    const enviar = vi.fn();
    render(<OrderTicketPro {...base} somenteLeitura onSolicitarOrdem={enviar} />);
    expect(screen.getAllByText('SOMENTE LEITURA').length).toBeGreaterThan(0);
    expect(screen.getByText(/SOMENTE LEITURA: o envio esta desligado/i)).toBeTruthy();
    const botao = screen.getByRole('button', { name: /SOMENTE LEITURA/i }) as HTMLButtonElement;
    expect(botao.disabled).toBe(true);
    fireEvent.click(botao);
    expect(enviar).not.toHaveBeenCalled();
  });

  it('sem executor autorizado o botao anuncia SEM ENVIO', () => {
    render(<OrderTicketPro {...base} />);
    expect(screen.getByRole('button', { name: /SEM ENVIO/i })).toBeTruthy();
  });

  it('sem contrato da corretora o risco nao vira numero', () => {
    render(<OrderTicketPro {...base} ficha={null} />);
    pontos(/Stop Loss \(pontos\)/i, '20');
    expect(screen.getByText(/depende do contrato/i)).toBeTruthy();
  });

  it('PROVA: com contrato, SL e confirmacao a ordem e emitida com os niveis certos', () => {
    const enviar = vi.fn();
    render(<OrderTicketPro {...base} onSolicitarOrdem={enviar} />);

    pontos(/Stop Loss \(pontos\)/i, '20');
    pontos(/Take Profit \(pontos\)/i, '40');

    // COMPRA a mercado: entrada = ask (1.1001). SL = 1.1001 - 20*0.0001 = 1.0981.
    // Volume padrao 0,01 lote: risco = 0,002 * 0,01 * 100.000 = 2,00 USD.
    expect(screen.getByText('1:2.00')).toBeTruthy();

    fireEvent.click(screen.getByRole('checkbox'));
    const botao = screen.getByRole('button', { name: /ENVIAR COMPRA/i }) as HTMLButtonElement;
    expect(botao.disabled).toBe(false);
    fireEvent.click(botao);

    expect(enviar).toHaveBeenCalledTimes(1);
    const ordem = enviar.mock.calls[0][0];
    expect(ordem.symbol).toBe('ATIVO');
    expect(ordem.lado).toBe('COMPRA');
    expect(ordem.pontosSL).toBe(20);
    expect(ordem.pontosTP).toBe(40);
    expect(ordem.sl).toBeCloseTo(1.0981, 6);
    expect(ordem.tp).toBeCloseTo(1.1041, 6);
    expect(ordem.riscoEstimado).toBeCloseTo(2, 6);
  });

  it('PROVA NEGATIVA: sem marcar a confirmacao o envio nao acontece', () => {
    const enviar = vi.fn();
    render(<OrderTicketPro {...base} onSolicitarOrdem={enviar} />);
    pontos(/Stop Loss \(pontos\)/i, '20');
    const botao = screen.getByRole('button', { name: /ENVIAR COMPRA/i }) as HTMLButtonElement;
    expect(botao.disabled).toBe(true);
    fireEvent.click(botao);
    expect(enviar).not.toHaveBeenCalled();
  });

  it('risco acima do limite informado bloqueia a ordem', () => {
    // Risco de 2 USD em saldo de 10.000 = 0,02%. Limite informado: 0,01%.
    render(<OrderTicketPro {...base} limiteRiscoPct={0.01} />);
    pontos(/Stop Loss \(pontos\)/i, '20');
    expect(screen.getByText(/acima do limite de 0.01%/i)).toBeTruthy();
  });
});
