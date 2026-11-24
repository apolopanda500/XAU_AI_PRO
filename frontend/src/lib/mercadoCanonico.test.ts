/*
  O MERCADO CANONICO, MEDIDO NO CONSUMIDOR REAL (12/11/2026)
  ==========================================================
  A regra e "o app nao pode mandar um nome de mercado que o gateway recusa".
  Repetir a tabela dentro do teste provaria que a tabela foi escrita —
  nao que ela produz o que o `marketApi` aceita (AGENTS.md 6).

  Por isso o segundo expect de cada caso e medido com
  `normalizeMarketSource('mt5', ...)`, que e o consumidor de verdade: e ele que
  LANCA antes de qualquer requisicao quando o nome nao esta na lista.
*/
import { describe, expect, it } from 'vitest';
import { mercadoCanonico } from './mercadoCanonico';
import { normalizeMarketSource } from './marketApi';

describe('mercadoCanonico', () => {
  it('PROVA: o singular do motor vira o plural que o gateway aceita', () => {
    /*
      MEDIDO no app 1.2.181 (captura 22:40): `auto.market = metal` derrubou o
      catalogo e o grafico caiu para o yahoo. O par esta aqui, lado a lado.
    */
    expect(mercadoCanonico('metal')).toBe('metals');
    expect(normalizeMarketSource('mt5', 'metal')).toBeNull();
    expect(normalizeMarketSource('mt5', mercadoCanonico('metal'))).toEqual({
      broker: 'mt5',
      market: 'metals',
    });
  });

  it('PROVA: toda classe que a corretora publica tem um mercado que o mt5 aceita', () => {
    /*
      As classes sao as de `mercadoDoAtivo` e as do `asset_registry`: se uma
      delas nao tiver mercado, o grafico de um ativo real cai no publico.
      `other` e a classe de "nao classificado" — e o MT5 a aceita como escopo.
    */
    const classes = [
      'forex',
      'metal',
      'index',
      'stock',
      'equity',
      'commodity',
      'bond',
      'crypto',
      'crypto-futures',
      'other',
    ];
    for (const classe of classes) {
      expect(normalizeMarketSource('mt5', mercadoCanonico(classe))).not.toBeNull();
    }
  });

  it('PROVA: espaco e caixa alta nao mudam a resposta', () => {
    // O motor manda o nome do payload, e o payload e texto livre.
    expect(mercadoCanonico(' METAL ')).toBe('metals');
    expect(mercadoCanonico('Metals')).toBe('metals');
    expect(mercadoCanonico('Equity')).toBe('stocks');
  });

  it('PROVA NEGATIVA: nao inventa mercado para o que nao conhece', () => {
    /*
      Nome desconhecido volta aparado, e QUEM RECUSA e o consumidor. Converter
      `cfd` em `metals` "para funcionar" seria a presuncao que o AGENTS.md 3
      proibe — e o operador leria o dado errado com a etiqueta certa.
    */
    expect(mercadoCanonico('cfd')).toBe('cfd');
    expect(normalizeMarketSource('mt5', 'cfd')).toBeNull();
  });

  it('PROVA NEGATIVA: vazio continua vazio, nunca um default', () => {
    /*
      `market` vazio e "ainda nao medido": a tela mostra o aviso e o grafico
      nao consulta com identidade falsa. Um default aqui (`forex`, ou `other`)
      seria o MT5 fixo que o dono mandou remover em 11/10/2026.
    */
    expect(mercadoCanonico('')).toBe('');
    expect(mercadoCanonico(null)).toBe('');
    expect(mercadoCanonico(undefined)).toBe('');
    expect(mercadoCanonico('   ')).toBe('');
    expect(normalizeMarketSource('mt5', mercadoCanonico(''))).toBeNull();
  });
});
