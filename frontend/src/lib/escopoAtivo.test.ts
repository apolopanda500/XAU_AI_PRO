// @vitest-environment jsdom
// SEM CONTA GRAVADA, SEM ESCOPO (11/10/2026, decisao do dono: nada de MT5 fixo).
// =============================================================================
// MEDIDO: `escopoAtivo()` devolvia `mt5:forex` sem a chave gravada — e a aba
// ROBO inteira nascia falando MT5: cabecalho da operacao automatica, fonte do
// grafico, catalogo do seletor e faixa de mercado, tudo antes de o operador
// escolher qualquer corretora.
//
// E o AGENTS.md §3 pelo outro lado: nenhuma corretora pode ser o caminho
// presumido. Vazio aqui e "escolha a corretora/conta" em cada leitor — nunca
// um padrao silencioso.
import { beforeEach, describe, expect, it } from 'vitest';
import {
  CHAVE_CONTA_ATIVA,
  CHAVE_CONTA_ID,
  contaAtivaId,
  definirEscopoAtivo,
  escopoAtivo,
  limparEscopoAtivo,
} from './escopoAtivo';

beforeEach(() => {
  window.localStorage.removeItem(CHAVE_CONTA_ATIVA);
  window.localStorage.removeItem(CHAVE_CONTA_ID);
});

describe('escopoAtivo — sem conta gravada, sem escopo', () => {
  it('PROVA: sem a chave, volta vazio — nao mt5:forex', () => {
    expect(escopoAtivo()).toEqual({ broker: '', market: '' });
  });

  it('PROVA NEGATIVA: o default antigo era mt5, e nao pode voltar', () => {
    // Sem este caso, devolver `mt5:forex` de novo passaria — e a ROBO
    // inteira voltaria a nascer falando MT5 sem ninguem escolher.
    const escopo = escopoAtivo();
    expect(escopo.broker).not.toBe('mt5');
    expect(escopo.market).not.toBe('forex');
  });

  it('conta gravada volta igual — o escolhido vence', () => {
    definirEscopoAtivo('mt5', 'metals');
    expect(escopoAtivo()).toEqual({ broker: 'mt5', market: 'metals' });
  });

  it('mercado incompativel com a corretora cai no primeiro dela, nao em forex', () => {
    // `compatibleMarket`: a lista e da corretora ESCOLHIDA. Presumir `forex`
    // para uma exchange seria o mesmo defeito com outra letra.
    definirEscopoAtivo('binance', 'forex');
    expect(escopoAtivo()).toEqual({ broker: 'binance', market: 'crypto-spot' });
  });
});

// O ID DA CONTA, AO LADO DO ESCOPO (22/10/2026)
// =============================================================================
// MEDIDO: duas contas MT5 ativas (real e demo) e `xau-active-account` guardando
// so `broker:market` — o ID se perdia na ativacao, o motor recusava
// "account_id e obrigatorio" e nao existia jeito de fazer a escolha. Chave
// separada de proposito: o formato de `xau-active-account` e contrato travado
// em oito componentes.
describe('contaAtivaId — a escolha de conta anda ao lado do escopo', () => {
  it('ativar com ID grava as duas chaves', () => {
    definirEscopoAtivo('mt5', 'forex', 'mt5:forex:Demo');
    expect(escopoAtivo()).toEqual({ broker: 'mt5', market: 'forex' });
    expect(contaAtivaId()).toBe('mt5:forex:Demo');
  });

  it('ativar SEM ID apaga o ID anterior — escolha velha nao sobrevive', () => {
    // PROVA NEGATIVA: sem esta remocao, o motor operaria a conta ERRADA em
    // silencio depois de o operador trocar de conexao por um caminho que nao
    // manda ID. Sem ID o motor cai na resolucao unica (ou recusa com motivo).
    definirEscopoAtivo('mt5', 'forex', 'mt5:forex:Demo');
    definirEscopoAtivo('mexc', 'crypto-spot');
    expect(contaAtivaId()).toBe('');
  });

  it('sem escolha nenhuma, volta vazio — nunca um ID presumido', () => {
    expect(contaAtivaId()).toBe('');
  });

  it('limpar a conta apaga o ID junto', () => {
    definirEscopoAtivo('mt5', 'forex', 'mt5:forex:Demo');
    limparEscopoAtivo();
    expect(escopoAtivo()).toEqual({ broker: '', market: '' });
    expect(contaAtivaId()).toBe('');
  });
});
