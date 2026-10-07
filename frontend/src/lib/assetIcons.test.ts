import { describe, it, expect } from 'vitest';
import { assetIcon } from './assetIcons';

/*
  A ICONE DO ATIVO — A CLASSE MANDA, O NOME SO COMPLEMENTA (06/10/2026)
  ======================================================================
  O DEFEITO
  --------
  A funcao filtrava por PALAVRA no simbolo, na ordem dos `if`, sem fronteira:

      if (/BTC/.test(text)) return 'BTC';
      if (/SOL/.test(text)) return 'SOL';

  MEDIDO:
  1. `/SOL/` casa dentro de `SOLVAR`, `RESOLVED`, `CONSOLID` — e o AGENTS.md 3
     nomeia esse caso como o defeito: "sem fronteira de palavra, `SOL` casa
     dentro de 'Solvar'".
  2. A `assetClass` que a CORRETORA publica era testada na NONA posicao, e as
     oito primeiras decisoes eram so por palavra. Um ativo cujo nome tivesse
     `BTC` e cuja classe fosse `metal` virava `BTC` — a hierarquia da ficha,
     que e a fonte da verdade, perdia para o nome.

  O QUE ESTE ARQUIVO TRAVA
  =======================
  Que nenhum par muda de icone por estar dentro de outra palavra, e que a
  classe da corretora vence o nome quando os dois discordam.
*/

/** Ativo cuja ficha a corretora NAO preencheu. */
const semClasse = (s: string) => assetIcon(s);

/** Ativo com a classe que a corretora publica. */
const comClasse = (s: string, c: string) => assetIcon(s, c);

describe('assetIcon — a classe da corretora manda', () => {
  it('metal pela ficha vira a sigla do metal', () => {
    expect(comClasse('XAUUSD', 'metal')).toBe('Au');
    expect(comClasse('XAGUSD', 'metal')).toBe('Ag');
    expect(comClasse('GOLD', 'metal')).toBe('Au');
    expect(comClasse('SILVER', 'metal')).toBe('Ag');
  });

  it('PROVA NEGATIVA: a classe vence o nome quando os dois discordam', () => {
    /*
    Este e o defeito central. `assetClass === 'metal'` era a NONA condicao, e as
    oito primeiras eram so por palavra: um simbolo com `BTC` no nome e classe
    `metal` virava `BTC`.

    Com a hierarquia, o nome da corretora vence: e a ficha que diz o que o ativo
    e, e um nome engana.
    */
    expect(comClasse('GOLD', 'metal')).toBe('Au');
    expect(comClasse('SILVER', 'metal')).toBe('Ag');
    // Um nome que PARECE cripto, com classe que diz forex: o par de forex tem
    // tres letras, e o operador precisa ver `BTC` na posicao da moeda, nao a
    // sigla do ativo cripto.
    expect(comClasse('BTCUSD', 'forex')).toBe('BTC');
  });

  it('cripto pela ficha usa o par sem o sufixo de cotacao', () => {
    expect(comClasse('BTCUSDT', 'crypto')).toBe('BTC');
    expect(comClasse('ETHUSDT', 'crypto')).toBe('ETH');
    expect(comClasse('SOLUSDT', 'crypto')).toBe('SOL');
    // Com barra e com ponto: o sufixo e unidade, nao ativo.
    expect(comClasse('SOL/USDT', 'crypto')).toBe('SOL');
    expect(comClasse('BTC.perp', 'crypto')).toBe('BTC');
  });

  it('forex pela ficha devolve as tres letras do par', () => {
    expect(comClasse('EURUSD', 'forex')).toBe('EUR');
    expect(comClasse('GBPUSD', 'forex')).toBe('GBP');
    expect(comClasse('XAUUSD', 'forex')).toBe('XAU');
  });

  it('as outras classes tem sigla propria', () => {
    expect(comClasse('US30', 'index')).toBe('IDX');
    expect(comClasse('AAPL', 'equity')).toBe('EQ');
    expect(comClasse('CLZ6', 'future')).toBe('FUT');
  });

  it('PROVA NEGATIVA: SOL nao casa dentro de palavra que contem "sol"', () => {
    /*
    A prova negativa que faltava no codigo antigo. `\bSOL\b` casa em `SOLVAR`,
    `RESOLVED` e `CONSOLID`: `S` e inicio de palavra em todas, e o `\b` final
    falha sem impedir a casada — o filtro agrupava `SOL` e nao exigia que o
    token ACABASSE ali.

    A forma que funciona e `^TOKEN$` sobre o ativo ja separado do sufixo de
    cotacao, que e o que `soAtivo` faz.
    */
    expect(semClasse('SOLVAR')).not.toBe('SOL');
    expect(semClasse('RESOLVED')).not.toBe('SOL');
    expect(semClasse('CONSOLID')).not.toBe('SOL');
    expect(comClasse('SOLVAR', 'crypto')).not.toBe('SOL');
    // E o par de verdade continua sendo Solana — o filtro corrigido nao pode
    // ter derrubado o ativo legitimo junto com o falso positivo.
    expect(comClasse('SOLUSDT', 'crypto')).toBe('SOL');
  });

  it('PROVA NEGATIVA: nenhuma sigla de cripto vaza para outra palavra', () => {
    // O mesmo defeito de `SOL` nas outras: `ETH` dentro de `ETHERNET`? Nao, mas
    // `LINK` dentro de `LINKUSD` sim — e `MAT` dentro de `MATIC`. O que
    // interessa e que nenhuma palavra composta vire cripto.
    expect(semClasse('ETHERNET')).not.toBe('ETH');
    expect(semClasse('DOGEMATIC')).not.toBe('DOGE');
    expect(semClasse('LTCASH')).not.toBe('LTC');
  });

  it('sem classe, o nome ainda serve — com token inteiro', () => {
    /*
    Este e o caminho de recurso, e ele tem de funcionar: nem toda rota manda a
    ficha.

    MEDIDO: `\bXAU\b` nao casa `XAUUSD` — depois de `XAU` vem `U`, que e letra, e
    o `\b` final falha. O ouro caia em `XAU` (as tres letras cruas). O filtro de
    metal e por INICIO, entao `XAUUSD` da `Au`.

    E `EURUSD` sem classe da `EUR`, a moeda de base: as tres ULTIMAS letras sao
    uma moeda de cotacao (`USD`), que e o que distingue um par de uma palavra.
    `SOLVAR` tambem tem seis letras e devolve o nome inteiro, porque `VAR` nao e
    moeda.
    */
    expect(semClasse('XAUUSD')).toBe('Au');
    expect(semClasse('BTCUSDT')).toBe('BTC');
    expect(semClasse('EURUSD')).toBe('EUR');
    // E o caso que o comprimento sozinho nao separa.
    expect(semClasse('SOLVAR')).toBe('SOLVAR');
  });

  it('PROVA NEGATIVA: simbolo vazio nunca vira sigla de cripto', () => {
    // String vazia casando com `.*` seria um `BTC` fantasma no rodape.
    expect(assetIcon('')).toBe('AST');
    expect(assetIcon('   ')).toBe('AST');
    // E com a classe, o vazio nao pode IGNORAR a ficha: MEDIDO,
    // `assetIcon('', 'crypto')` devolvia `AST` porque o `return` de vazio estava
    // antes da leitura da classe.
    expect(assetIcon('', 'crypto')).toBe('CRY');
    expect(assetIcon('', 'metal')).toBe('MET');
    expect(assetIcon('', 'index')).toBe('IDX');
  });

  it('nunca devolve vazio: a coluna tem largura constante', () => {
    /*
    O operador nao pode ler a diferenca entre "vazio" e "nao sei". Por isso a
    funcao devolve SEMPRE texto — inclusive para um ativo que nao esta em
    nenhuma lista, onde ela devolve o NOME INTEIRO em vez de recortar tres
    letras (ver o comentario da emergencia em `assetIcons.ts`).
    */
    for (const simbolo of ['', 'BTCUSDT', 'XAUUSD', '???', '123', 'A', 'ATIVO-NAO-CONHECIDO']) {
      for (const classe of ['', 'metal', 'crypto', 'forex', 'index', 'classe-inexistente']) {
        expect(assetIcon(simbolo, classe).length).toBeGreaterThan(0);
      }
    }
  });

  it('PROVA NEGATIVA: ativo desconhecido mostra o NOME, nao tres letras', () => {
    /*
    MEDIDO: o recorte de emergencia devolvia `SOL` para `SOLVAR`, `ETH` para
    `ETHERNET` e `DOG` para `DOGEMATIC` — a sigla de cripto aparecia para uma
    palavra que so COMECAVA com o nome da moeda. O corte de tres letras era a
    fronteira que faltava.
    */
    expect(semClasse('ATIVO-NAO-CONHECIDO')).not.toBe('ATI');
    expect(semClasse('ATIVO-NAO-CONHECIDO')).toBe('ATIVO');
    // E um nome que so comeca com sigla tambem nao vira sigla.
    expect(semClasse('ETHEREUM-FUND')).not.toBe('ETH');
    expect(semClasse('SOLANA')).not.toBe('SOL');
  });

  it('PROVA NEGATIVA: classe desconhecida NAO vira cripto por default', () => {
    // Um `else` que devolvesse `CRY` faria um indice com classe mal escrita
    // virar cripto — e o operador leria o icone errado sem ter como saber.
    expect(comClasse('US30', 'classe-que-nao-existe')).not.toBe('CRY');
  });
});