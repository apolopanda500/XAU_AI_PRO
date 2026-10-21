// @vitest-environment jsdom
// NENHUM ICONE DA INTERFACE E UM GLIFO (09/10/2026)
// =============================================
// MEDIDO pelo dono: "tem icones no grafico mas nao da pra ver nada".
//
// MEDIDO no codigo, o grafico usava `⌁` `⊞` `⊟` `⤢` — glifos de "tipografia
// matematica" e de "setas", que a fonte que o app declara NAO tem. Glifo
// ausente vira caractere de substituted: um quadrado do tamanho de uma letra.
// Para o operador, o botao fica vazio.
//
// O MESMO defeito estava em tres paineis, com `⌁` `⏻` `◷`.
//
// Este teste e a TRAVA: ele le o fonte e reprova se um glifo voltar. Sem ele, o
// proximo icone acrescentado como caractere repete o defeito em silencio, que
// e como o original passou: o botao existia, o `title` estava certo, e a tela
// mostrava um quadrado.
import { describe, expect, it } from 'vitest';

/**
 * O QUE PROVOCA O DEFEITO.
 *
 * Nao e "caractere nao-ASCII": o ponto medio, o travessao e as aspas curvas
 * aparecem em todo o texto da interface e sao legiveis. E o bloco dos glifos
 * decorativos — matematica, geometria, formas de bloco, setas e emoji — que a
 * fonte do Windows nao garante.
 */
/**
 * OS GLIFOS QUE SUMIRAM, MEDIDOS UM A UM.
 *
 * A primeira versao desta trava cobria o bloco inteiro U+2190–U+2BFF e
 * REPROVOU no `✓` do "Sem SL/TP", no `▾` da barra de status e no `★` das
 * estrelas. Sao caracteres que as fontes do Windows tem e que o operador le
 * normalmente. A trava estava errada, nao o codigo — a regra certa e "nenhum
 * icone pode depender de glifo", nao "nenhum glifo e proibido".
 *
 * Entao a lista e dos glifos que ESTE projeto mediu quebrarem. Se um icone
 * novo falhar, o glifo entra aqui com o defeito que ele produziu.
 */
const GLIFOS_QUE_QUEBRAM = /[⌁⊞⊟⤢⏻◷⏦⊠⌗⋔⧘⇱⇲]/u;

/** Emoji sao o outro caso medido: cor e dois caracteres de largura. */
const EMOJI = /[\u{1F000}-\u{1FAFF}]/u;

/** Onde um icone pode estar. Fora daqui, texto normal nao interessa. */
const ARQUIVOS_DE_ICONE = [
  // `components/charts/BarraFerramentas.tsx` e `components/charts/IconesGrafico.tsx`
  // sairam em 11/10/2026 (decisao do dono: o grafico e para colocar ordens).
  // A ausencia deles e travada no ultimo caso deste arquivo.
  'components/Icones.tsx',
  'components/ConnectedDevicesPanel.tsx',
  'components/ExitAppButton.tsx',
  'components/LatenciaBar.tsx',
];

/**
 * `node:fs` nao tem tipagem neste projeto, e a leitura de disco e a unica forma
 * de medir o FONTE — que e onde o glifo nasceria. O mesmo caminho usado em
 * `lib/portas.test.ts`, que mede o fonte pelo mesmo motivo.
 */
const lerFonte = async (relativo: string): Promise<string> => {
  // @ts-expect-error `node:fs` nao tem tipagem neste projeto
  const { readFileSync } = await import('node:fs');
  return String(readFileSync(new URL(relativo, import.meta.url), 'utf-8'));
};

/** O `tsx` inteiro, menos comentarios — o codigo e o que e renderizado. */
const codigoSemComentarios = (fonte: string): string => {
  let fora = '';
  let i = 0;
  while (i < fonte.length) {
    const dois = fonte.slice(i, i + 2);
    if (dois === '/*') {
      const fim = fonte.indexOf('*/', i + 2);
      i = fim === -1 ? fonte.length : fim + 2;
      continue;
    }
    if (dois === '//') {
      const fim = fonte.indexOf('\n', i);
      i = fim === -1 ? fonte.length : fim;
      continue;
    }
    fora += fonte[i];
    i += 1;
  }
  return fora;
};

describe('os icones da interface sao DESENHADOS, nunca glifos', () => {
it('o codigo de icone nao tem nenhum glifo decorativo', async () => {
    const achados: string[] = [];
    for (const relativo of ARQUIVOS_DE_ICONE) {
      const codigo = codigoSemComentarios(await lerFonte(relativo));
      codigo.split('\n').forEach((linha, i) => {
        const glifo = linha.match(GLIFOS_QUE_QUEBRAM) ?? linha.match(EMOJI);
        if (glifo) achados.push(`${relativo}:${i + 1}  ${glifo[0]}  ${linha.trim().slice(0, 70)}`);
      });
    }
    expect(
      achados,
      `glifo decorativo no codigo de icone:\n${achados.join('\n')}`,
    ).toEqual([]);
  });

  it('PROVA NEGATIVA: a trava accuses um glifo de verdade', () => {
    /*
      Um teste que nunca reprova nao e uma trava. Este verifica que o REGOE
      reconhece os glifos do defeito original e nao acusa o texto normal da
      interface — porque uma trava que acusa o ponto medio e do mesmo defeito:
      o proximo agente desliga a trava em vez de corrigir.
    */
    // Os glifos que estavam no codigo e sairam como quadrado, um a um.
    for (const glifo of ['⌁', '⊞', '⊟', '⤢', '⏻', '◷']) {
      expect(GLIFOS_QUE_QUEBRAM.test(`rotulo: '${glifo}'`), `nao acusou ${glifo}`).toBe(true);
    }
    // E o emoji, que e o outro defeito medido.
    expect(EMOJI.test("'📡'")).toBe(true);

    // Texto normal em portugues, com acento, ponto e aspas curvas. E os glifos
    // que o Windows TEM e o app usa de proposito: `✓` no "Sem SL/TP", `▾` na
    // barra de status, `★` nas estrelas, `×` e `−` em numeros e fechar.
    for (const texto of [
      'BTCUSD · H1 · MT5',
      'margem indisponível — o motor não foi ligado',
      'Carregando XAU AI PRO…',
      '“Sem tradução no dicionário”',
      '×',
      '✓ Sem SL/TP',
      '−0,50',
      '★',
      '▾',
      '‹ ›',
    ]) {
      expect(
        GLIFOS_QUE_QUEBRAM.test(texto) || EMOJI.test(texto),
        `acusou texto normal: ${texto}`,
      ).toBe(false);
    }
  });

  it('os componentes de icone exportam SVG, e nao texto', async () => {
    /*
      Um icone que devolve texto e um icone que sumiu. Isto mede a saida, e nao
      o texto do fonte: e o texto que renderiza que some.
    */
    const componentes = ['IconeDispositivo', 'IconeEnergia', 'IconeRelogio', 'IconeSinal'];
    const fonte = await lerFonte('components/Icones.tsx');
    for (const nome of componentes) {
      const assinatura = new RegExp(`export function ${nome}\\(`, 'u');
      expect(assinatura.test(fonte), `falta o componente ${nome}`).toBe(true);
    }
    // Todo SVG precisa de viewBox, senao nao escala e some em janela pequena.
    const svgs = fonte.match(/<svg[^>]*>/gu) ?? [];
    expect(svgs.length).toBeGreaterThanOrEqual(componentes.length);
    for (const svg of svgs) {
      expect(svg, `svg sem viewBox: ${svg}`).toContain('viewBox=');
      // O `aria-hidden` evita que o leitor de tela leia o desenho E o texto.
      expect(svg).toContain('aria-hidden');
    }
  });

  it('PROVA NEGATIVA: um icone sem aria-hidden seria reprovado', () => {
    const svgSemOcultar = '<svg viewBox="0 0 24 24" width="14" height="14">';
    expect(svgSemOcultar).not.toContain('aria-hidden');
    // E o regex realmente pega o atributo quando ele existe.
    expect('<svg viewBox="0 0 24 24" aria-hidden="true">').toContain('aria-hidden');
  });

  it('a barra de edicao do grafico nao volta: os arquivos sairam', async () => {
    /*
      11/10/2026, decisao do dono: o grafico e para colocar ordens, nao para
      editar/estudar/analisar. A barra de ferramentas de desenho saiu com os
      icones dela (`BarraFerramentas.tsx`, `IconesGrafico.tsx`, `desenhos.ts`).

      Este caso trava a REMOCAO, nao o conteudo: recriar qualquer um dos tres
      arquivos sem a tela que os usava seria o defeito de volta pela porta dos
      fundos — e nenhum outro teste reclamaria, porque nada mais os importa.
    */
    // @ts-expect-error `node:fs` nao tem tipagem neste projeto
    const { existsSync } = await import('node:fs');
    for (const relativo of [
      'components/charts/BarraFerramentas.tsx',
      'components/charts/IconesGrafico.tsx',
      'components/charts/desenhos.ts',
    ]) {
      const url = new URL(relativo, import.meta.url);
      expect(existsSync(url), `${relativo} voltou`).toBe(false);
    }
  });
});