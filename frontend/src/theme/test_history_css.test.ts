import { describe, expect, it } from 'vitest';

/*
  A CONTAGEM DO HISTORICO NAO SE PARTE EM OITO LINHAS (09/10/2026)
  =================================================================
  MEDIDO na captura de 07/10 00:38, no app instalado, aba "Historico",
  no rodape do filtro:

      Exibindo
      5
      operacoes
      e
      3
      movimentacoes
      12 registros
      00:38:10

  Oito palavras, uma embaixo da outra, com a janela de 1456px. Nao era falta
  de espaco: "movimentacoes" cabe folgada nos ~130px que a caixa tinha.

  A CAUSA
  =======
  `frontend/src/theme/global.css`, regra `.history-count`:

      .history-count {
        display: flex;
        flex-direction: column;   <-- a frase virou coluna
        gap: 4px;
      }

  O JSX (`HistoryTab.tsx`) escreve os itens como IRMAOS de uma frase: `Exibindo`,
  o numero, `operacoes`, `e`, o numero, `movimentacoes`, `· 12 registros`,
  `· 00:38:10`. Sao oito nos de um unico enunciado, e o `gap: 4px` era espaco
  ENTRE eles — espaco de linha. Com `column`, cada `<span>` vira uma linha por
  si e o `gap` vira altura.

  E E A MESMA ARMADILHA DO TICKET (07/10/2026 §1.7), com outro formato: ali a
  coluna de `minmax(0, ...)` colapsou; aqui a coluna `auto` do grid espremeu a
  caixa ate a largura da maior palavra. Nas duas, a coluna de protecao e a que
  perde, porque o grid serve primeiro quem tem conteudo intrinseco.

  POR QUE ISTO NAO E UM TESTE DE LAYOUT
  =======================================
  `jsdom` nao calcula largura: `offsetWidth` e `0` para tudo, e um teste que
  medisse `getComputedStyle(...).flexDirection` passaria com o defeito na tela
  — o AGENTS.md §6 na sua forma mais facil de cair. O que se trava aqui e a
  REGRA, que e o que produz o comportamento. E o caminho inteiro (o JSX
  escrevendo os nos) fica em `HistoryTab.conta.test.tsx`.

  COMO LER O CSS NESTE PROJETO
  ============================
  `import x from './global.css?raw'` devolve STRING VAZIA no vitest: o vitest
  troca o modulo de CSS por um stub antes do `?raw` resolver. MEDIDO — `len: 0`.
  Um `expect(css.length).toBeGreaterThan(0)` teria passado sem verificar nada.
  A forma que funciona e `node:fs` por `await import` dinamico, e ja esta
  documentada em `test_robo_ticket_css.test.ts`.
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

/**
 * O corpo de uma regra.
 *
 * Sem isto, um `.history-count` renomeado faria `corpo()` devolver string vazia
 * e os `toMatch` reprovariam por motivo errado — e o agente seguinte buscaria
 * um bug de CSS num teste de CSS.
 */
const corpo = (css: string, nome: string): string =>
  css.match(new RegExp(`^\\s*\\.${nome}[^{]*\\{([^}]*)\\}`, 'm'))?.[1] ?? '';

/** O valor de uma propriedade dentro de um corpo de regra. */
const propriedade = (corpoRegra: string, nome: string): string =>
  corpoRegra.match(new RegExp(`(?:^|[;{\\s])${nome}\\s*:\\s*([^;}]+)`, 'i'))?.[1]?.trim() ?? '';

/**
 * O eixo principal que a regra declara, normalizado.
 *
 * `flex-flow: row wrap` e `flex-direction: row` valem a mesma coisa; `column`
 * NAO vale, e e exatamente o defeito. Normalizar aqui e o que permite a prova
 * negativa de comparar regra antiga com regra nova pela MESMA medida.
 */
const eixoPrincipal = (corpoRegra: string): string =>
  (propriedade(corpoRegra, 'flex-flow') || propriedade(corpoRegra, 'flex-direction')).split(/\s+/)[0];

/** O piso (`minmax(<min>, ...>`) da coluna que recebe a contagem. */
const pisoDaColunaDaContagem = (grade: string): number | null => {
  const m = grade.match(/minmax\(\s*([\d.]+)(px|rem|em)?\s*,\s*auto\s*\)/);
  return m ? Number(m[1]) : null;
};

describe('a contagem do historico e uma frase, e a frase fica na linha', () => {
  it('a folha que este arquivo mede NAO esta vazia', async () => {
    /*
      A PROVA DE QUE O `?raw` NAO ENTROU. Com a folha chegando vazia, todo
      `toMatch` abaixo reprova por motivo errado — ou pior, passa.
    */
    const css = await lerCss('global.css');
    expect(css.length).toBeGreaterThan(10000);
    expect(css).toContain('.history-count');
    expect(css).toContain('.history-filters');
  });

  it('PROVA: `.history-count` tem fluxo em LINHA, nunca em coluna', async () => {
    /*
      A PROVA DE QUE A REGRA ESTA.

      `flex-direction: column` transformava oito nos de uma frase em oito
      linhas, com o `gap: 4px` virando altura.
    */
    const contagem = corpo(await lerCss('global.css'), 'history-count');
    expect(contagem.length).toBeGreaterThan(0);
    expect(eixoPrincipal(contagem), `.history-count em eixo ${eixoPrincipal(contagem)}`).toBe('row');
  });

  it('PROVA: quando faltar espaco, a quebra e NO ITEM, nunca dentro da palavra', async () => {
    /*
      `column` quebrava a palavra; `row` sem `wrap` estouraria a caixa. O que
      segura a frase e o `wrap`: a quebra cai na fronteira entre os irmaos.
    */
    const contagem = corpo(await lerCss('global.css'), 'history-count');
    const fluxo = propriedade(contagem, 'flex-flow');
    expect(fluxo, `.history-count sem flex-flow`).toContain('row');
    expect(fluxo, `.history-count sem wrap`).toContain('wrap');
    // E `align-items: baseline`, para numero e palavra compartilharem a linha
    // de base em vez de o numero ficar pendurado.
    expect(propriedade(contagem, 'align-items')).toBe('baseline');
  });

  it('PROVA NEGATIVA: a regra antiga, em COLUNA, REPROVA esta mesma medida', async () => {
    /*
      A prova de que as duas medicoes acima nao sao decorativas.

      A MESMA funcao `eixoPrincipal`, aplicada a regra COMO ESTAVA:
    */
    const regraAntiga = '.history-count { display: flex; flex-direction: column; gap: 4px; }';
    // A regra antiga mede `column` — e a medida acima exige `row`.
    expect(eixoPrincipal(regraAntiga)).toBe('column');
    expect(eixoPrincipal(regraAntiga)).not.toBe('row');
    // Ela tambem nao tinha `wrap`: `column` nao precisa, e por isso o texto
    // empilhava em vez de quebrar em item inteiro.
    expect(propriedade(regraAntiga, 'flex-flow')).not.toContain('wrap');
    // E a regra nova mede `row`.
    expect(eixoPrincipal(corpo(await lerCss('global.css'), 'history-count'))).toBe('row');
  });

  it('PROVA: a coluna da contagem no grid tem PISO, e nao `min(0)`', async () => {
    /*
      MEDIDO: a caixa ficou com ~130px — o bastante para "movimentacoes" e
      nada mais. A coluna era `auto` puro, sem piso, e o grid serve primeiro as
      colunas com conteudo intrinseco: as de filtro enchem a linha e a da
      contagem, que nao tem piso, e a que sobra.

      E a MESMA regra do ticket (07/10 §1.7): coluna de protecao com piso
      explicito, nunca `min(0)`.
    */
    const grade = corpo(await lerCss('global.css'), 'history-filters');
    expect(grade).toMatch(/grid-template-columns/);
    expect(grade).not.toMatch(/minmax\(\s*0\s*,\s*auto\s*\)/);
    const piso = pisoDaColunaDaContagem(grade);
    expect(piso, 'a coluna da contagem nao tem piso').not.toBeNull();
    expect(Number(piso)).toBeGreaterThan(0);
  });

  it('PROVA NEGATIVA: `auto` puro e `minmax(0, auto)` REPROVAM o piso', async () => {
    /*
      As duas formas como a coluna podia ficar sem garantia, medidas com a MESMA
      funcao que a medicao acima usa:

        `auto` puro      -> `pisoDaColunaDaContagem` devolve `null` -> reprova
        `minmax(0,auto)` -> piso `0` -> reprova (`toBeGreaterThan(0)` falha)
    */
    const semPiso = 'grid-template-columns: 1fr 1.3fr 1.4fr auto;';
    expect(pisoDaColunaDaContagem(semPiso)).toBeNull();

    const comZero = 'grid-template-columns: 1fr 1.3fr 1.4fr minmax(0, auto);';
    expect(Number(pisoDaColunaDaContagem(comZero))).toBe(0);
    expect(Number(pisoDaColunaDaContagem(comZero))).not.toBeGreaterThan(0);

    // E a regra que esta no arquivo tem piso de verdade.
    const real = corpo(await lerCss('global.css'), 'history-filters');
    expect(Number(pisoDaColunaDaContagem(real))).toBeGreaterThan(0);
  });

  it('o numero em destaque nao e TITULO perdido dentro da frase', async () => {
    /*
      O `strong` era 20px dentro de uma frase de 12px. Com `align-items:
      baseline` isso desalinha a linha de base e o numero passa a parecer um
      titulo solto no meio do enunciado. O destaque continua no peso e na cor,
      que e o que o operador precisa ver sem esticar a frase.
    */
    const forte = corpo(await lerCss('global.css'), 'history-count strong');
    const tamanho = Number(propriedade(forte, 'font-size').replace('px', ''));
    expect(tamanho).toBeGreaterThan(0);
    expect(tamanho, 'numero de 20px desalinha a frase').toBeLessThan(20);
  });

  it('as regras que este arquivo mede EXISTEM todas', async () => {
    /*
      Sem isto, um `.history-count` renomeado faria `corpo()` devolver string
      vazia, e os `toMatch` acima reprovariam por motivo errado.
    */
    const css = await lerCss('global.css');
    for (const nome of ['history-filters', 'history-count', 'history-count strong']) {
      expect(temRegra(css, nome), `falta a regra .${nome}`).toBe(true);
    }
  });
});