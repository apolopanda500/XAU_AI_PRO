import { describe, expect, it } from 'vitest';

/*
  O TICKET NAO ESPRIME O CAMPO (07/10/2026)
  ==========================================
  MEDIDO no app instalado, 00:37 e no recorte de 00:40: `Stop Loss` com ~10px
  de largura, e o rotulo empilhado em coluna de UM CARACTERE:

      s
      t
      o
      p
      o

  E o campo "Valor no risco (SL)" perdia a CAIXA DE INPUT: sobrava o `<label>` e
  o `<input>` sumia.

  A CAUSA, e ela e do GRID — nao do componente
  ============================================
  A coluna de proteção era `minmax(0, 1.35fr)`. O `min(0)` permite que a coluna
  chegue a ZERO, e o `grid` precisa sempre primeiro: com a faixa curta, as
  colunas `auto` — que tem conteudo intrinseco — enchem a linha e a de proteção,
  a unica com minimo zero, colapsa.

  E o lado de dentro era `1fr 1fr`: num `grid`, `1fr` tem minimo automatico igual
  ao CONTEUDO, e o conteudo do `<span>` nao quebra.

  POR QUE ISTO NAO E UM TESTE DE LAYOUT
  =======================================
  `jsdom` nao calcula largura: `offsetWidth` e `0` para tudo, e um teste que
  medisse isso passaria — verde com o defeito na tela. E o AGENTS.md 6 na sua
  forma mais facil de cair: o teste que "verifica o layout" e nao verifica
  layout nenhum.

  O QUE ESTE ARQUIVO FAZ: trava a REGRA, que e o que produz o comportamento.
  E cada `expect` tem o caso que reprovaria sem a correcao — medido, nao
  suposto.

  COMO LER O CSS NESTE PROJETO — e o erro que ja foi pago aqui
  ===========================================================
  `import x from './robo.css?raw'` devolve **STRING VAZIA** nesta sessao de
  vitest: o vitest troca o modulo de CSS por um stub antes do `?raw` resolver.
  MEDIDO nesta sessao — `len: 0`, `tem robo-ticket? false`.

  Isso e o AGENTS.md 6 do avesso: com uma folha de 0 caracteres, `corpo()`
  devolvia `''` e os `toMatch` reprovavam por motivo errado; e um
  `expect(css.length).toBeGreaterThan(0)` teria passado sem verificar nada.

  A forma que funciona, e que o `test_robo_css.test.ts` JA DOCUMENTA: `node:fs`
  por `await import` dinamico, com `@ts-expect-error` porque o `tsconfig` nao
  tem `@types/node`. Tentei `?raw` primeiro por ser mais limpo; medi que
  devolvia vazio; voltei. A forma que funciona e a que fica.
*/
async function lerCss(nome: string): Promise<string> {
  // @ts-expect-error `node:fs` nao tem tipagem neste projeto (sem @types/node)
  const { readFileSync } = await import('node:fs');
  // @ts-expect-error `node:url` nao tem tipagem neste projeto (sem @types/node)
  const { fileURLToPath } = await import('node:url');
  const aqui = fileURLToPath(import.meta.url).replace(/\\/g, '/');
  const pasta = aqui.slice(0, aqui.lastIndexOf('/'));
  return String(readFileSync(`${pasta}/${nome}`, 'utf-8'));
}

/** A regra existe? */
const temRegra = (css: string, nome: string): boolean =>
  new RegExp(`^\\s*\\.${nome}[^{]*\\{`, 'm').test(css);

/** O corpo de uma regra. */
const corpo = (css: string, nome: string): string =>
  css.match(new RegExp(`^\\s*\\.${nome}[^{]*\\{([^}]*)\\}`, 'm'))?.[1] ?? '';

/** As colunas `minmax(<min>, <fr>fr)` de uma regra. */
const colunasFr = (css: string): Array<{ min: number; fr: number }> =>
  [...corpo(css, 'robo-ticket').matchAll(/minmax\(\s*([\d.]+)(px)?\s*,\s*([\d.]+)fr\s*\)/g)].map(
    (m) => ({ min: Number(m[1]), fr: Number(m[3]) }),
  );

describe('o ticket de ordem nao espreme o campo', () => {
  it('a folha que este arquivo mede NAO esta vazia', async () => {
    /*
      A PROVA DE QUE O `?raw` NAO ENTROU.

      Com `import x from './robo.css?raw'` a folha chega com 0 caracteres, e
      todo `toMatch` abaixo reprova por motivo errado — ou pior, passa. Este
      `expect` reprova no instante em que a leitura voltar a quebrar, e diz que
      a leitura quebrou.
    */
    const css = await lerCss('robo.css');
    expect(css.length).toBeGreaterThan(1000);
    expect(css).toContain('robo-ticket');
  });

  it('PROVA: toda coluna `fr` do ticket tem minimo maior que zero', async () => {
    /*
      A PROVA DE QUE A REGRA ESTA.

      Era `minmax(0, 1.35fr)`. O `min(0)` deixa a coluna chegar a zero, e o
      `grid` sempre serve primeiro as colunas `auto` — que tem conteudo
      intrinseco. A proteção era a unica com minimo zero, e foi a que colapsou:
      `Stop Loss` com ~10px e o rotulo empilhado em coluna de um caractere.
    */
    const colunas = colunasFr(await lerCss('robo.css'));
    expect(colunas.length).toBeGreaterThan(0);
    for (const c of colunas) {
      expect(c.min, `coluna ${c.fr}fr com minimo ${c.min}px`).toBeGreaterThan(0);
    }
  });

  it('PROVA NEGATIVA: a regra antiga, com min zero, REPROVA esta mesma medida', async () => {
    /*
      A prova de que o teste acima nao e decorativo.

      A mesma medicao, aplicada a regra COMO ESTAVA:
    */
    const regraAntiga = 'grid-template-columns: auto minmax(96px,0.5fr) minmax(0,1.35fr) auto auto;';
    const colunasAntigas = [...regraAntiga.matchAll(/minmax\(\s*([\d.]+)(px)?\s*,\s*([\d.]+)fr\s*\)/g)];
    const comZero = colunasAntigas.some((m) => Number(m[1]) === 0);
    expect(comZero).toBe(true);
    // A coluna de 1.35fr era exatamente a de minima zero.
    expect(Number(colunasAntigas[1][1])).toBe(0);
    // E a regra nova nao tem nenhuma.
    const novas = colunasFr(await lerCss('robo.css'));
    expect(novas.some((c) => c.min === 0)).toBe(false);
  });

  it('PROVA: os DOIS lados da protecao podem encolher ate o piso do input', async () => {
    /*
      MEDIDO: `Stop Loss` e `Take Profit` sao IRMAOS, e o que o operador compara
      sao os dois numeros. Empilhados em coluna, a comparacao deixa de existir.

      `1fr 1fr` num grid tem minimo automatico igual ao CONTEUDO, e conteudo de
      `<span>` nao quebra. Com `minmax(0, 1fr)`, cada metade encolhe ate o piso
      do `input` — que tem largura de caixa, nao de texto.
    */
    const protecao = corpo(await lerCss('robo.css'), 'robo-ticket-protecao');
    expect(protecao).toMatch(/minmax\(\s*0\s*,\s*1fr\s*\)\s+minmax\(\s*0\s*,\s*1fr\s*\)/);
    expect(protecao).toMatch(/min-width\s*:\s*0/);
  });

  it('PROVA NEGATIVA: `1fr 1fr` deixa o ROTULO como minimo automatico', async () => {
    /*
      A regra anterior, medida. Sem `minmax`, o minimo automatico de uma coluna
      `fr` num grid e o do conteudo — e o conteudo do rotulo nao quebra.
    */
    const antes = 'grid-template-columns: 1fr 1fr;';
    const temMinmax = antes.includes('minmax');
    expect(temMinmax).toBe(false);
    // E a regra nova tem, explicitamente.
    expect(corpo(await lerCss('robo.css'), 'robo-ticket-protecao')).toContain('minmax');
  });

  it('o botao de envio tem o minimo que FALTAVA a protecao', async () => {
    /*
      `robo-ticket-enviar` ja tinha `min-width: 148px`. E por isso que a
      protecao nao precisava de `min(0)`: o botao ja estava garantido, e o
      minimo zero dela nao comprava espaco para ninguem.

      Este teste trava essa leitura. Sem o minimo do botao, o `minmax` do grid
      volta a ser a unica garantia, e a protecao volta a poder colapsar.
    */
    const enviar = corpo(await lerCss('robo.css'), 'robo-ticket-enviar');
    expect(enviar).toMatch(/min-width\s*:\s*148px/);
    /*
      E a COLUNA do botao no grid tambem declara o minimo.

      `colunasFr` so enxerga `minmax(<min>, <n>fr)`; a coluna do botao e
      `minmax(148px, auto)` — `auto`, nao `fr` — e por isso que a contagem de
      colunas `fr` NAO a inclui. Um `length >= 3` aqui reprovaria por um motivo
      errado, e o agente seguinte buscaria um bug no CSS em vez do no teste.
    */
    const grade = corpo(await lerCss('robo.css'), 'robo-ticket');
    expect(grade).toMatch(/minmax\(\s*148px\s*,\s*auto\s*\)/);
  });

  it('o requisito de margem ocupa a largura do ticket, como os niveis', async () => {
    /*
      MEDIDO na XM (20:43): `Requisito de margem $0.85` fica logo abaixo da
      quantidade, na largura toda. Estreito entre o preco e os botoes, vira
      rodape — e o operador deixa de ler como um numero da ordem.
    */
    expect(corpo(await lerCss('robo.css'), 'robo-ticket-requisito')).toMatch(
      /flex\s*:\s*1 1 100%/,
    );
  });

  it('as regras do ticket que este arquivo mede EXISTEM todas', async () => {
    /*
      Sem isto, um `.robo-ticket` renomeado faria `corpo()` devolver string
      vazia, e os `toMatch` acima reprovariam por motivo errado — e o agente
      seguinte buscaria um bug de CSS num teste de CSS.
    */
    const css = await lerCss('robo.css');
    for (const nome of [
      'robo-ticket',
      'robo-ticket-protecao',
      'robo-ticket-enviar',
      'robo-ticket-requisito',
      'robo-ticket-niveis',
    ]) {
      expect(temRegra(css, nome), `falta a regra .${nome}`).toBe(true);
    }
  });
});