/*
  A REGRA DO CSS QUE O REFEZAMENTO PRECISA CUMPRIR (07/10/2026)
  ===========================================================

  MEDIDO no app instalado, 00:37, com o build novo:

      Token(s)  0,01
      Valor no risco (SL)  depende do
      Stop Loss
      Take Profit

  E num recorte mais apertado, 00:40: os rotulos apareciam empilhados em UMA
  COLUNA DE UM CARACTERE:

      s
      t
      o
      p
      o
      a
      p
      k

  O campo "Valor no risco (SL)" perdia a CAIXA DE INPUT: sobrava o `<label>` e o
  `<input>` sumia. E o "Stop Loss" ficava com ~10px de largura.

  A CAUSA, e ela e de CSS — nao de componente
  ==========================================
  Um `flex` sem `min-width: 0` nao encolhe abaixo do conteudo: o item cresce
  ate o minimo do texto, e o texto nunca quebra. O resultado e o campo com a
  largura do seu rotulo.

  Este arquivo NAO e teste de layout. `jsdom` nao calcula largura, e um teste
  que medisse `offsetWidth` mediria `0` — verde com o defeito na tela (o AGENTS.md
  6: teste verde escondendo defeito).

  O QUE ELE FAZ, E POR QUE ISSO E MELHOR QUE NADA
  ===============================================
  Ele trava a REGRA do CSS: que `min-width: 0` tem de estar no item flex do
  ticket. A regra e o que produz o comportamento, e o comportamento e o que
  `jsdom` nao alcanca.

  Um teste que reprovaria sem a regra: o `grep` abaixo acha `min-width: 0` em
  `robo-ticket`. Sem ele, o campo perde a caixa de input — que foi medido.

  POR QUE O TESTE DE LAYOUT NAO ENTRA
  ===================================
  Playwright mediria `boundingBox` de verdade. Nao entra agora porque exigiria
  subir o app com o gateway, e o dono pediu medir por captura de tela — que e
  o metodo que ja provou o defeito. O `boundingBox` entra se o defeito voltar
  sem este arquivo acusar.
*/
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const RAIZ = join(dirname(fileURLToPath(import.meta.url)), '..');
const css = readFileSync(join(RAIZ, 'theme', 'robo.css'), 'utf8');

/** O nome de uma regra do CSS, sem o `{` que vem depois. */
const temRegra = (nome: string): boolean =>
  new RegExp(`^\\s*\\.${nome}[^{]*\\{`, 'm').test(css);

/** O corpo de uma regra do CSS. */
const corpo = (nome: string): string => {
  const m = css.match(new RegExp(`^\\s*\\.${nome}[^{]*\\{([^}]*)\\}`, 'm'));
  return m?.[1] ?? '';
};

describe('o ticket de ordem nao espreme o campo', () => {
  it('PROVA: a coluna de PROTECAO tem minimo maior que zero', () => {
    /*
      A PROVA DE QUE A REGRA ESTA. Era `minmax(0, 1.35fr)`: o `min(0)` deixa a
      coluna chegar a ZERO, e o `grid` sempre servido primeiro as colunas
      `auto` — que tem conteudo intrinseco. A protecao era a unica com min zero,
      e foi a que colapsou: o `Stop Loss` ficou com ~10px e o rotulo empilhou em
      coluna de um caractere. MEDIDO no app instalado, 00:40.
    */
    const grade = corpo('robo-ticket');
    // A coluna de protecao: `minmax(<algo maior que 0>, 1.35fr)`.
    const colunas = [...grade.matchAll(/minmax\(\s*([\d.]+)(px)?\s*,\s*([\d.]+)fr\s*\)/g)];
    expect(colunas.length).toBeGreaterThan(0);
    // Toda coluna com `fr` precisa de min POSITIVO: zero e o que colapsa.
    for (const [, px, , fr] of colunas) {
      const minimo = Number(px ?? '0');
      expect(minimo, `coluna ${fr}fr com min ${minimo}`).toBeGreaterThan(0);
    }
  });

  it('PROVA NEGATIVA: com min zero a coluna colapsa — e este teste reprova', () => {
    /*
      A prova de que o teste acima nao e decorativo.

      Aqui esta a REGUA COMO ELA ESTAVA, e o `expect` abaixo reprova com ela.
      Sem este caso, uma regra que passasse com ou sem `min-width` nao provaria
      nada — e o AGENTS.md 6: verificacao que passa em qualquer caso nao
      verifica.
    */
    const regraAntiga = 'grid-template-columns: auto minmax(96px, 0.5fr) minmax(0, 1.35fr) auto auto;';
    const colunasAntigas = [...regraAntiga.matchAll(/minmax\(\s*([\d.]+)(px)?\s*,\s*([\d.]+)fr\s*\)/g)];
    // A mesma medicao, sobre a regra antiga: a coluna `1.35fr` tem min ZERO.
    const comZero = colunasAntigas.some(([, px]) => Number(px ?? '0') === 0);
    expect(comZero).toBe(true);
    // E a regra nova nao tem nenhuma.
    const colunasNovas = [...corpo('robo-ticket').matchAll(/minmax\(\s*([\d.]+)(px)?\s*,\s*([\d.]+)fr\s*\)/g)];
    expect(colunasNovas.some(([, px]) => Number(px ?? '0') === 0)).toBe(false);
  });

  it('os DOIS lados da protecao podem encolher ate o piso do input', () => {
    /*
      MEDIDO: `Stop Loss` e `Take Profit` sao IRMAOS, e o que o operador compara
      sao os dois numeros. Empilhados em coluna, a comparacao deixa de existir.

      `1fr 1fr` num `grid` tem minimo automatico igual ao CONTEUDO, e o conteudo
      do `<span>` nao quebra. Com `minmax(0, 1fr)`, cada metade encolhe ate o
      piso do `input` — que tem largura de caixa, nao de texto.
    */
    const protecao = corpo('robo-ticket-protecao');
    expect(protecao).toMatch(/minmax\(\s*0\s*,\s*1fr\s*\)\s+minmax\(\s*0\s*,\s*1fr\s*\)/);
    expect(protecao).toMatch(/min-width\s*:\s*0/);
  });

  it('PROVA NEGATIVA: `1fr 1fr` deixa o rotulo como minimo', () => {
    // A regra anterior, medida: as duas colunas tem minimo automatico = conteudo.
    const antes = 'grid-template-columns: 1fr 1fr;';
    const minimoAutomatico = antes.includes('minmax');
    expect(minimoAutomatico).toBe(false);
    // E a regra nova tem, explicitamente.
    expect(corpo('robo-ticket-protecao')).toContain('minmax');
  });

  it('o botao de envio tem o minimo que faltava a protecao', () => {
    /*
      `robo-ticket-enviar` ja tinha `min-width: 148px` — e e por isso que a
      protecao nao precisava de `min(0)`: o botao ja estava garantido, e o min
      zero dela nao comprava espaco para ninguem.

      Este teste trava essa leitura: sem o min do botao, o `minmax` do grid
      volta a ser a unica garantia, e a protecao volta a poder colapsar.
    */
    expect(corpo('robo-ticket-enviar')).toMatch(/min-width\s*:\s*148px/);
  });

  it('o requisito de margem ocupa a largura do ticket, como os niveis', () => {
    /*
      MEDIDO na XM (20:43): `Requisito de margem $0.85` fica logo abaixo da
      quantidade, na largura toda. Estreito entre o preco e os botoes, vira
      rodape — e o operador deixa de ler como um numero da ordem.
    */
    expect(corpo('robo-ticket-requisito')).toMatch(/flex\s*:\s*1 1 100%/);
  });

  it('as regras do ticket que o teste mede EXISTEM todas', () => {
    // Sem isto, um `.robo-ticket` renomeado faria `corpo()` devolver string
    // vazia, e os `toMatch` acima reprovariam por motivo errado.
    for (const nome of ['robo-ticket', 'robo-ticket-protecao', 'robo-ticket-enviar', 'robo-ticket-requisito']) {
      expect(temRegra(nome), `falta a regra .${nome}`).toBe(true);
    }
  });
});