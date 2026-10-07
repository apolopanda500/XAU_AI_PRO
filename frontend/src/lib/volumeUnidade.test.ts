import { describe, it, expect } from 'vitest';
import {
  unidadeDeVolume,
  fichaDoAtivo,
  faixaDoAtivo,
  rotuloQuantidade,
} from './volumeUnidade';
import type { AssetRow } from './brokerCatalog';

/*
  A UNIDADE E A FAIXA DO VOLUME (05/10/2026)
  =========================================
  MEDIDO nas capturas da XM, o mesmo painel com nomes diferentes:

      Bolivar (forex)  ->  "0,01 Lote(s)"
      BTCUSD  (crypto) ->  "0,01 Token(s)"

  Um "Lote" fixo para os dois e umatchi: o operador de BTCUSD leria "0,01 Lote"
  e nao saberia se o numero e contrato ou token.

  A chave e `assetClass`, que `asset_registry` le da HIERARQUIA que a corretora
  publica ("Cryptocurrencies" -> "crypto") - nunca de palavra solta no nome.
*/

const ficha = (extra: Partial<AssetRow> = {}): AssetRow => ({
  symbol: 'BTCUSD',
  displayName: null,
  availability: 'full',
  restrictions: [],
  digits: 2,
  point: 0.01,
  volumeStep: 0.01,
  volumeMin: 0.01,
  volumeMax: 10,
  tradeMode: 4,
  assetClass: 'crypto',
  ...extra,
});

describe('unidadeDeVolume', () => {
  it('crypto e Token(s); as demais classes sao Lote(s)', () => {
    expect(unidadeDeVolume('crypto')).toBe('Token(s)');
    expect(unidadeDeVolume('forex')).toBe('Lote(s)');
    expect(unidadeDeVolume('metal')).toBe('Lote(s)');
    expect(unidadeDeVolume('index')).toBe('Lote(s)');
    expect(unidadeDeVolume('equity')).toBe('Lote(s)');
    expect(unidadeDeVolume('cfd')).toBe('Lote(s)');
  });

  it('PROVA NEGATIVA: sem classe publicada, NAO escreve unidade', () => {
    // Devolver "Lote(s)" aqui seria affirmar a classe sem saber - e a regra do
    // projeto proibe exatamente isso. Ausencia de dado vira ausencia de texto.
    expect(unidadeDeVolume(null)).toBeNull();
    expect(unidadeDeVolume(undefined)).toBeNull();
    expect(unidadeDeVolume('')).toBeNull();
  });

  it('a classe vem do produtor e nao do nome do simbolo', () => {
    // Dois simbolos com nome parecido, classes diferentes pela ficha.
    expect(unidadeDeVolume(ficha({ symbol: 'GOLD', assetClass: 'metal' }).assetClass)).toBe('Lote(s)');
    expect(unidadeDeVolume(ficha({ symbol: 'BTCUSD', assetClass: 'crypto' }).assetClass)).toBe('Token(s)');
  });
});

describe('fichaDoAtivo', () => {
  const catalogo = [ficha({ symbol: 'BTCUSD' }), ficha({ symbol: 'GOLD', assetClass: 'metal' })];

  it('acha pelo simbolo exato, sem diferenciar caixa', () => {
    expect(fichaDoAtivo(catalogo, 'btcusd')?.symbol).toBe('BTCUSD');
    expect(fichaDoAtivo(catalogo, 'gold')?.assetClass).toBe('metal');
  });

  it('PROVA NEGATIVA: simbolo ausente e simbolo vazio dao null, nunca o primeiro', () => {
    // Cair no primeiro item da lista seria o defeito ja medido no par do grafico
    // ("caiu no simbolos[0]" com 1639 ativos). Aqui: null.
    expect(fichaDoAtivo(catalogo, 'ETHUSD')).toBeNull();
    expect(fichaDoAtivo(catalogo, '')).toBeNull();
    expect(fichaDoAtivo(catalogo, 'BTC')).toBeNull();
  });
});

describe('faixaDoAtivo', () => {
  it('usa a faixa que a corretora devolveu', () => {
    const f = faixaDoAtivo(ficha({ volumeMin: 0.001, volumeMax: 5, volumeStep: 0.001 }));
    expect(f).toEqual({ minimo: 0.001, maximo: 5, passo: 0.001, assumido: false });
  });

  it('PROVA NEGATIVA: volume_max MENOR que o padrao e aceito, nao piso', () => {
    // Um teto de corretora abaixo de 10 e real. Treatar 10 como piso aceitaria
    // ordem que o gateway recusa - a pior divergencia: tela aceita, porta nega.
    const f = faixaDoAtivo(ficha({ volumeMax: 0.5 }));
    expect(f.maximo).toBe(0.5);
    expect(f.assumido).toBe(false);
  });

  it('PROVA NEGATIVA: volume_min MENOR que 0,01 e aceito, nao piso', () => {
    // Cripto com minimo 0,001: um piso de 0,01 rejeitaria ordem valida.
    const f = faixaDoAtivo(ficha({ volumeMin: 0.001 }));
    expect(f.minimo).toBe(0.001);
  });

  it('ficha sem os campos assume E avisa, em vez de fingir que e da corretora', () => {
    const f = faixaDoAtivo(ficha({ volumeMin: null, volumeMax: null }));
    expect(f.minimo).toBe(0.01);
    expect(f.assumido).toBe(true);
  });

  it('ficha inexistente assume E avisa', () => {
    expect(faixaDoAtivo(null).assumido).toBe(true);
    expect(faixaDoAtivo(null).minimo).toBe(0.01);
  });

  it('zero e negativo vindos da corretora caem no fallback, e isso e sinalizado', () => {
    // `volume_min = 0` nao e uma faixa utilizavel. Assumir e avisar e melhor que
    // gerar um input cujo min e 0, que aceitaria volume zero.
    const f = faixaDoAtivo(ficha({ volumeMin: 0, volumeMax: -1 }));
    expect(f.minimo).toBe(0.01);
    expect(f.assumido).toBe(true);
  });
});

describe('rotuloQuantidade', () => {
  it('o rotulo usa a unidade da ficha, em minusculo para o aria-label', () => {
    expect(rotuloQuantidade('Token(s)', 0.01)).toBe('Quantidade em token(s)');
    expect(rotuloQuantidade('Lote(s)', 0.01)).toBe('Quantidade em lote(s)');
  });

  it('PROVA NEGATIVA: sem classe, o rotulo nao mente sobre o dado', () => {
    // O aria-label precisa existir para o teste de acessibilidade e para o
    // operador com leitor de tela, entao ele tem um padrao. O que nao pode
    // acontecer e o rotulo afirmar "Token(s)" sem classe nenhuma.
    expect(rotuloQuantidade(null, 0.01)).toBe('Quantidade em lote(s)');
    expect(rotuloQuantidade(null, 0.01)).not.toContain('token');
  });
});