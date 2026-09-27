// @vitest-environment jsdom
// Testes do bloqueio progressivo do PIN.
//
// O bug corrigido aqui: o contador vivia em useState dentro do LockScreen, entao
// fechar e reabrir o app devolvia as 5 tentativas. O estado passou a ser
// persistido, com espera crescente por ciclo de falhas.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  CHAVE_LOCKOUT,
  MAX_TENTATIVAS,
  backoffMs,
  estaBloqueado,
  formatarEspera,
  lerLockout,
  limparFalhas,
  registrarFalha,
  tentativasRestantes,
} from './lockout';

const AGORA = 1_800_000_000_000;

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  vi.useRealTimers();
});

describe('contagem de tentativas', () => {
  it('comeca com todas as tentativas disponiveis', () => {
    expect(lerLockout()).toEqual({ falhas: 0, bloqueadoAte: 0 });
    expect(tentativasRestantes({ falhas: 0, bloqueadoAte: 0 })).toBe(MAX_TENTATIVAS);
  });

  it('decremente a cada erro', () => {
    let estado = lerLockout();
    estado = registrarFalha(estado, AGORA);
    expect(tentativasRestantes(estado)).toBe(MAX_TENTATIVAS - 1);
    estado = registrarFalha(estado, AGORA);
    expect(tentativasRestantes(estado)).toBe(MAX_TENTATIVAS - 2);
  });
});

describe('persistencia entre reaberturas', () => {
  it('o contador sobrevive a fechar e reabrir o app', () => {
    registrarFalha(lerLockout(), AGORA);
    registrarFalha(lerLockout(), AGORA);

    // Simula uma nova sessao: o estado e lido do storage, nao de useState.
    const reaberto = lerLockout();
    expect(reaberto.falhas).toBe(2);
    expect(tentativasRestantes(reaberto)).toBe(MAX_TENTATIVAS - 2);
  });

  it('o bloqueio ja aplicado continua valendo apos reabrir', () => {
    let estado = lerLockout();
    for (let i = 0; i < MAX_TENTATIVAS; i++) estado = registrarFalha(estado, AGORA);

    // "Reabrir" o app 10s depois nao pode liberar o PIN.
    const reaberto = lerLockout();
    expect(estaBloqueado(reaberto, AGORA + 10_000)).toBe(true);
  });

  it('limpar apos desbloqueio zera o estado e apaga o registro', () => {
    let estado = lerLockout();
    for (let i = 0; i < MAX_TENTATIVAS; i++) estado = registrarFalha(estado, AGORA);

    estado = limparFalhas();
    expect(estado).toEqual({ falhas: 0, bloqueadoAte: 0 });
    expect(localStorage.getItem(CHAVE_LOCKOUT)).toBeNull();
    expect(estaBloqueado(estado, AGORA)).toBe(false);
  });
});

describe('espera progressiva', () => {
  it('nao bloqueia antes de completar o ciclo', () => {
    expect(backoffMs(0)).toBe(0);
    expect(backoffMs(MAX_TENTATIVAS - 1)).toBe(0);
    expect(backoffMs(MAX_TENTATIVAS)).toBe(30_000);
  });

  it('dobra a cada ciclo e tem teto', () => {
    expect(backoffMs(MAX_TENTATIVAS * 2)).toBe(60_000);
    expect(backoffMs(MAX_TENTATIVAS * 3)).toBe(120_000);
    expect(backoffMs(MAX_TENTATIVAS * 20)).toBe(30 * 60_000);
  });

  it('libera quando a espera termina', () => {
    let estado = lerLockout();
    for (let i = 0; i < MAX_TENTATIVAS; i++) estado = registrarFalha(estado, AGORA);
    expect(estaBloqueado(estado, AGORA + 29_999)).toBe(true);
    expect(estaBloqueado(estado, AGORA + 30_000)).toBe(false);
  });
});

describe('estado corrompido', () => {
  it('trata conteudo invalido como zerado em vez de quebrar', () => {
    localStorage.setItem(CHAVE_LOCKOUT, '{nao é json');
    expect(lerLockout()).toEqual({ falhas: 0, bloqueadoAte: 0 });
  });

  it('rejeita numeros ausentes ou nao finitos', () => {
    localStorage.setItem(CHAVE_LOCKOUT, JSON.stringify({ falhas: 'dez' }));
    expect(lerLockout().falhas).toBe(0);
    localStorage.setItem(CHAVE_LOCKOUT, JSON.stringify({ falhas: 3 }));
    expect(lerLockout().bloqueadoAte).toBe(0);
  });
});

describe('formatacao da espera', () => {
  it('mostra segundos e minutos', () => {
    expect(formatarEspera(30_000)).toBe('30s');
    expect(formatarEspera(90_000)).toBe('1min 30s');
  });
});
