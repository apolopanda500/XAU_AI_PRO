import { describe, expect, it } from 'vitest';
import { chaveDia, horaDaLinha, stampDaLinha } from './horaServidor';

/*
  A HORA DO HISTORICO TEM DE BATER COM O MT5 (23/10/2026).

  MEDIDO: o deal do MT5 carrega a hora de PAREDE do servidor (UTC+3 nesta
  conta) codificada como epoch. O gateway publica `time_server` no formato do
  MT5 e `time` em ISO/UTC. A tela usa `time_server` quando existe; sem ele cai
  no fuso da maquina, que e o certo para cripto.

  A prova NEGATIVA: `horaDaLinha` tem de devolver `01:46:43` e NAO o valor
  deslocado pelo fuso da maquina (`22:46:43` do dia anterior em UTC-3). Se o
  helper ignorasse `horarioServidor`, o teste reprovaria.
*/

const linha = {
  horario: '2026-10-05T01:46:43Z',
  horarioServidor: '2026.10.05 01:46:43',
};

describe('hora do servidor no historico', () => {
  it('usa o carimbo do MT5, e nao o fuso da maquina', () => {
    expect(horaDaLinha(linha)).toBe('01:46:43');
    expect(stampDaLinha(linha)).toBe('2026.10.05 01:46:43');
  });

  it('sem carimbo do servidor, cai no fuso da maquina (cripto)', () => {
    const cripto = { horario: '2026-10-05T01:46:43Z', horarioServidor: '' };
    // O valor depende do fuso de quem roda o teste; o que se prova e que a
    // funcao NAO devolve o carimbo inventado do MT5.
    expect(horaDaLinha(cripto)).not.toBe('2026.10.05 01:46:43');
    expect(stampDaLinha(cripto)).not.toContain('.');
  });

  it('horario ausente continua vazio, sem data inventada', () => {
    expect(horaDaLinha({ horario: '', horarioServidor: '' })).toBe('');
    expect(stampDaLinha({ horario: '', horarioServidor: '' })).toBe('');
  });
});

describe('chaveDia', () => {
  it('le o carimbo do MT5 sem passar por Date', () => {
    expect(chaveDia('2026.10.05 01:46:43')).toBe('2026-10-05');
  });

  it('nao joga carimbo do MT5 em "sem-data"', () => {
    expect(chaveDia('2026.10.05 23:59:59')).not.toBe('sem-data');
  });

  it('continua aceitando ISO', () => {
    expect(chaveDia('2026-10-05T01:46:43Z')).toMatch(/^2026-10-0[45]$/);
  });

  it('vazio e texto invalido viram "sem-data"', () => {
    expect(chaveDia('')).toBe('sem-data');
    expect(chaveDia('nao-e-data')).toBe('sem-data');
  });
});
