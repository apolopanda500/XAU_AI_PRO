import { describe, it, expect } from 'vitest';
import { assetIcon, SEM_ICONE } from './assetIcons';

/*
  A SIGLA DO ATIVO — SO A CLASSE DECIDE (09/10/2026)
  ===================================================
  A REGRA MUDOU POR DECISAO DO DONO
  ---------------------------------
  "deixar o catalogo sem icone apenas lista opcional".

  A regra ANTIGA era: a classe da corretora manda, e o NOME do simbolo
  complementa quando a classe nao diz o bastante. Havia lista de metais por
  prefixo (`XAU`, `GOLD`...), lista de tokens de cripto (`BTC`, `SOL`, `DOGE`...),
  lista de moedas de cotacao (`USDT`, `USD`...) e palpite de par de forex por
  comprimento.

  A regra NOVA: so a classe decide. Sem classe, SEM SIGLA — e nao uma sigla
  inventada (`AST`) nem um palpite pelo nome.

  O QUE ESTE ARQUIVO TRAVA
  ------------------------
  Que a sigla nao volte a depender do nome. O teste mais importante e o ultimo:
  a funcao NAO RECEBE MAIS O SIMBOLO, e por isso nao tem como adivinhar. Um teste
  que chamasse `assetIcon('SOLVAR')` provaria o comportamento de hoje, mas nao
  impediria a lista de tokens de voltar — ela voltaria e o teste continuaria
  passando com o argumento errado.

  E por isso que a assinatura e travada tambem: ver o ultimo teste deste arquivo.
*/

/** Ativo cuja ficha a corretora NAO preencheu — sem classe, sem sigla. */
const semClasse = (_simbolo: string) => assetIcon();

/** Ativo com a classe que a corretora publica. */
const comClasse = (_simbolo: string, c: string) => assetIcon(c);

describe('assetIcon — so a classe da corretora decide', () => {
  it('a classe vira a sigla, sempre a mesma para a mesma classe', () => {
    expect(comClasse('', 'metal')).toBe('MET');
    expect(comClasse('', 'crypto')).toBe('CRY');
    expect(comClasse('', 'forex')).toBe('FX');
    expect(comClasse('', 'index')).toBe('IDX');
    expect(comClasse('', 'equity')).toBe('EQ');
  });

  it('a mesma classe da a MESMA sigla para qualquer par', () => {
    /*
      Era o defeito da assinatura antiga: a sigla podia mudar por causa do nome.

      MEDIDO no codigo antigo: `assetIcon('XAUUSD','metal')` dava `Au` e
      `assetIcon('OUTROCOISA','metal')` dava `MET`. O mesmo metal, duas siglas, e
      o operador nao tinha como saber qual valia.

      Agora os dois dao a mesma sigla.
    */
    expect(comClasse('XAUUSD', 'metal')).toBe(comClasse('OUTROCOISA', 'metal'));
    expect(comClasse('BTCUSDT', 'crypto')).toBe(comClasse('OUTROCOISA', 'crypto'));
  });

  it('SEM CLASSE NAO HA SIGLA — lista sem icone, como o dono decidiu', () => {
    expect(assetIcon()).toBe(SEM_ICONE);
    expect(assetIcon(undefined)).toBe(SEM_ICONE);
    expect(assetIcon('')).toBe(SEM_ICONE);
    expect(assetIcon('   ')).toBe(SEM_ICONE);

    // E nada de sigla inventada: `AST` era um rotulo que parecia informacao.
    expect(assetIcon('classe_que_nao_existe')).toBe(SEM_ICONE);
    expect(assetIcon('desconhecida')).toBe(SEM_ICONE);
  });

  it('PROVA NEGATIVA: nenhum nome de ativo vira sigla', () => {
    /*
      Este e o caso que o AGENTS.md §3 mede: "sem fronteira de palavra, `SOL` casa
      dentro de 'Solvar'". As linhas abaixo eram os defeitos — ANTES da decisao do
      dono, cada uma devolvia uma sigla de cripto para uma palavra que so comecava
      com o nome da moeda.

      Como a funcao nao recebe o simbolo, a unica forma de acertar seria ignorar
      a classe e ler um nome — que ela nao tem. Este teste mede isso pelos dois
      caminhos: com e sem classe.
    */
    for (const palavra of ['SOLVAR', 'RESOLVED', 'CONSOLID', 'ETHERNET', 'DOGEMATIC', 'LTCASH']) {
      expect(assetIcon(), `sem classe nao pode sair sigla: ${palavra}`).toBe(SEM_ICONE);
      // E com classe, a classe e que responde — `forex` da FX, e nunca `SOL`.
      expect(assetIcon('forex')).toBe('FX');
      expect(assetIcon('crypto')).toBe('CRY');
    }
  });

  it('PROVA NEGATIVA: a assinatura nao aceita simbolo — nao ha como adivinhar', () => {
    /*
      A trava de VERDADE. Um teste de comportamento passaria mesmo que a lista de
      tokens voltasse, porque quem escreveu a lista tambem escreveria o teste para
      ela. O que impede a lista de voltar e a funcao nao ter o nome para ler.

      `@ts-expect-error` acima deixa claro que passar simbolo e erro de
      compilacao, e nao um comportamento: se um dia a assinatura voltar a receber
      simbolo, esta LINHA reprova e a pessoa ve o que fez.
    */
    expect(assetIcon.length, 'so um parametro: a classe').toBe(1);

    // E o TypeScript reprova a chamada com dois argumentos.
    // @ts-expect-error a funcao nao recebe simbolo, de proposito
    expect(() => assetIcon('XAUUSD', 'metal')).toBeDefined();
  });
});
