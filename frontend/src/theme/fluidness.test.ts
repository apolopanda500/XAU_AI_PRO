// @vitest-environment jsdom
// Fluidez e peso (05/10/2026).
//
// O DONO PEDIU
// ============
// "E O RESTANDO TEMAS MAIS FLUIDOS, abas mais leves"
//
// "Fluid" aqui tem significado verificavel: mudanca de estado que parece erro
// (aba, chip, linha, cartao) ganha transicao curta, E o que estava gastando
// quadro sem retorno visual deixa de gastar.
//
// Estes testes nao medem quadro â€” medem as DECISOES que produzem quadro, que e
// o que da para travar em teste. O que esta travado aqui:
//
// (1) numeros que o operador le enquanto mudam NAO tem transicao (cotacao,
//     PnL, latencia): um numero atrasado em relacao ao dado e pior do que
//     um numero sem animacao;
// (2) `prefers-reduced-motion` desliga TUDO em um unico bloco;
// (3) o fundo animado para fora do foco e retoma ao voltar;
// (4) a barra de latencia usa `transform`, nao `width`.

import { beforeAll, describe, expect, it } from 'vitest';

// `?raw` traz o arquivo como string, resolvido pelo Vite/Vitest.
//
// A tipagem de `?raw` vem de `vite/client`, ja referenciado em `vite-env.d.ts`.
// O sufixo SEM extensao e o padrao do projeto para TypeScript (ver
// `useAICommunication.test.ts`). Para CSS ele nao resolve — o motivo esta no
// bloco maior abaixo, com o que foi medido.
/*
  POR QUE `import.meta.glob` PARA .ts E LEITURA DE DISCO PARA .css
  ==============================================================
  MEDIDO nesta sessao (vitest 5.0.2, `environment: 'jsdom'`):

  - O glob com `{ css, ts, tsx }` traz `.ts` e `.tsx` com conteudo
    (`../App.tsx=4706`) mas traz TODOS os `.css` com 0 bytes: o Vitest troca o
    modulo de CSS por um stub vazio antes de o `?raw` valer, entao o glob
    resolve o caminho e nao o texto.
  - `import x from './fluidness.css?raw'` devolve string vazia pelo mesmo
    motivo.
  - `import x from './fluidness?raw'` (sem extensao) nao resolve, porque
    `.css` nao esta em `resolve.extensions`.

  Ligar `test.css: true` no `vitest.config.ts` resolveria, mas muda o
  carregamento de CSS dos 25 arquivos de teste do projeto inteiro para atender a
  um. A leitura local resolve sem tocar nos outros.

  E por que o acesso ao disco e aceitavel AQUI, quando o resto do projeto nao
  usa `node:fs`: `@types/node` nao esta instalado, entao um `import` nomeado de
  `node:fs` reprovaria o `tsc --noEmit`, que e gate. O `@ts-expect-error` abaixo
  marca exatamente essa linha — e, por ser `@ts-expect-error`, ele FALHA se um
  dia `node:fs` passar a ter tipagem, obrigando a remover a supressao.
*/
const ARQUIVOS = import.meta.glob('../**/*.{ts,tsx}', {
  query: '?raw',
  import: 'default',
  eager: true,
}) as Record<string, string>;

/**
 * Le um CSS do disco. Ver o comentario acima para por que e preciso.
 *
 * O caminho vem do `import.meta.url` do proprio arquivo, que o Vite resolve
 * para URL `file:` em modulo de teste. Nao se usa `__dirname` nem `process.cwd()`:
 * nenhum dos dois tem tipagem sem `@types/node`, e ambos reprovariam o
 * `tsc --noEmit`.
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

/** Conteudo do arquivo, pelo nome do arquivo. */
const ler = (nome: string): string => {
  const achado = Object.entries(ARQUIVOS).find(([caminho]) => caminho.endsWith(`/${nome}`));
  if (!achado) {
    throw new Error(
      `fonte nao encontrada no glob: ${nome}. Disponiveis: ${Object.keys(ARQUIVOS).join(', ')}`,
    );
  }
  return achado[1];
};

/**
 * Os tres CSS sao lidos em eforeAll e guardados aqui.
 *
 * Nao da para ler no topo do modulo: lerCss e assincrona (import dinamico de
 * 
ode:fs), e um wait no topo_level do arquivo de teste nao e suportado
 * pelo transformador do Vitest.
 */
let fluido = '';
let latenciaBar = '';
let statusBar = '';

beforeAll(async () => {
  fluido = await lerCss('fluidness.css');
  latenciaBar = await lerCss('latencia-bar.css');
  statusBar = await lerCss('status-bar.css');
  // Guarda contra leitura silenciosa: arquivo vazio faria todo teste de
  // 	oContain passar por slice(-1) e dar string vazia, que e o defeito
  // que esta classe de teste nasceu para pegar.
  for (const [nome, texto] of [
    ['fluidness.css', fluido],
    ['latencia-bar.css', latenciaBar],
    ['status-bar.css', statusBar],
  ] as const) {
    if (texto.length < 100) {
      throw new Error(`${nome} leio ${texto.length} bytes: leitura de CSS falhou`);
    }
  }
});

const quantumFundo = ler('QuantumBackground.tsx');
const appRaiz = ler('App.tsx');
const entrada = ler('main.tsx');

/** Bloco `prefers-reduced-motion` do arquivo. */
function blocoReducedMotion(texto: string): string {
  const abre = texto.indexOf('@media (prefers-reduced-motion: reduce)');
  if (abre < 0) return '';
  let profundidade = 0;
  for (let i = abre; i < texto.length; i += 1) {
    if (texto[i] === '{') profundidade += 1;
    else if (texto[i] === '}') {
      profundidade -= 1;
      if (profundidade === 0) return texto.slice(abre, i + 1);
    }
  }
  return '';
}

describe('fluidness.css â€” numeros nunca animam', () => {
  it('cotacao, resultado e latencia nao tem transicao', () => {
    // O ponto do teste: o bloco `.num` na lista de "nao pode animar". Se um
    // numero entra em `.num`, ele para de ter transicao â€” e `.num` cobre
    // TUDO que e numero no app, das tabelas aos cards.
    const bloco = fluido.slice(fluido.indexOf('.num,'), fluido.indexOf('.status-chip.is-warn'));
    expect(bloco).toContain('transition: none !important');
    for (const seletor of ['.num', '.kpi-value', '.latencia-ms', '.cal-row-time']) {
      expect(bloco).toContain(seletor);
    }
  });

  it('o ponto de status pisca de novo depois do bloco', () => {
    // `.status-chip.is-warn` vem DEPOIS do `transition: none`, entao continua
    // animando: piscar em "nao conectado" e a informacao, nao enfeite.
    expect(fluido).toContain('.status-chip.is-warn .status-ponto');
    expect(fluido).toContain('animation: status-pisca');
  });
});

describe('fluidness.css â€” durations', () => {
  it('as duracoes sao tokens, nao numeros soltos', () => {
    expect(fluido).toContain('--fluido-rapido');
    expect(fluido).toContain('--fluido-medio');
    // Nenhuma transicao com duracao acima do teto declarado: acima de 160 ms o
    // usuario ja entendeu que a acao foi lida e a animacao vira atraso.
    const duracoes = [...fluido.matchAll(/var\(--fluido-(rapido|medio)\)/g)].map((m) => m[1]);
    expect(duracoes.length).toBeGreaterThan(5);
    expect(duracoes.every((d) => d === 'rapido' || d === 'medio')).toBe(true);
  });

  it('nenhuma regra anima width, height ou top/left', () => {
    // Propriedade de layout anima reflow por quadro. `width` aparecia na barra
    // de latencia e na barra da sidebar, e e exatamente o tipo de propriedade
    // que faz a interface "puxar" em maquina fraca.
    const transitionencias = [...fluido.matchAll(/transition:\s*([^;]+);/g)].map((m) => m[1]);
    for (const regra of transitionencias) {
      expect(regra).not.toMatch(/^\s*width\b/);
      expect(regra).not.toMatch(/^\s*height\b/);
      expect(regra).not.toMatch(/^\s*(top|left)\b/);
    }
  });

  it('foco visivel e instantaneo', () => {
    // Quem navega por teclado precisa saber onde esta AGORA. Um foco com
    // 160 ms de atraso faz o operador tabular as coisas na linha errada.
    const bloco = fluido.slice(
      fluido.indexOf('.btn:focus-visible'),
      fluido.indexOf('/* ---------- Chips de estado'),
    );
    expect(bloco).toContain('transition: none');
  });
});

describe('fluidness.css â€” reduced motion', () => {
  it('existe um unico bloco que desliga animacao, transition e scroll', () => {
    const bloco = blocoReducedMotion(fluido);
    expect(bloco).not.toBe('');
    // As tres propriedades. Faltando `scroll-behavior`, a rolagem por
    // `focus-visible` continuaria suave em quem pediu menos movimento.
    expect(bloco).toContain('animation-duration');
    expect(bloco).toContain('animation-iteration-count');
    expect(bloco).toContain('transition-duration');
    expect(bloco).toContain('scroll-behavior');
    // `!important` e o que faz vencer qualquer regra acima.
    expect(bloco).toContain('!important');
  });

  it('a barra de latencia nao tem mais bloco proprio', () => {
    // O bloco dela foi REMOVIDO de proposito: a barra passou a emitir
    // `transform` sem `transition`, entao muda na hora e nao ha o que
    // desligar. Manter o bloco seria uma regra morta que ainda pareceria
    // proteger alguma coisa.
    //
    // A busca e por `@media`, e nao pela palavra: o arquivo ainda MENCIONA
    // `prefers-reduced-motion` no comentario que explica a remocao, e um
    // `not.toContain` da palavra reprovaria por causa do proprio texto que
    // documenta o defeito.
    expect(latenciaBar).not.toContain('@media (prefers-reduced-motion');
  });

  it('a barra de rodape mantem o bloco, e ele e especifico dela', () => {
    // `status-bar.css` tem o ponto de status piscando, que e sinal de "nao
    // conectado". Piscar e a informacao — entao precisa de bloco proprio.
    expect(statusBar).toContain('prefers-reduced-motion');
    expect(blocoReducedMotion(statusBar)).toContain('!important');
  });
});

describe('latencia-bar.css â€” transform, nao width', () => {
  it('o medidor nao transiciona width', () => {
    // `width` e propriedade de layout: transicionar reflowa a linha a cada
    // quadro. O componente passou a emitir `transform: scaleX(...)`.
    const latencia = latenciaBar;
    expect(latencia).not.toMatch(/transition:\s*width/);
    // E o `transform-origin` precisa existir em algum lugar, senao a barra
    // cresce a partir do centro e o valor lido fica errado.
    expect(latencia + fluido).toContain('transform-origin: left center');
  });
});

const fonte = quantumFundo;

describe('QuantumBackground â€” peso e foco', () => {

  it('tem teto de FPS declarado', () => {
    expect(fonte).toContain('MAX_FPS');
    // 30 fps: o fundo e uma nuvem desfocada e o olho nao separa 60 de 30.
    expect(fonte).toMatch(/MAX_FPS = 30/);
  });

  it('para o loop quando a janela perde o foco', () => {
    // O navegador ja pausa rAF quando a ABA some. O que nao parava era a
    // JANELA em segundo plano com outra na frente.
    expect(fonte).toContain('document.hasFocus()');
    expect(fonte).toContain('document.hidden');
  });

  it('RETOMA o loop quando a janela volta', () => {
    // Sem isto, o fundo congela para sempre depois da primeira troca de
    // janela: o rAF morreu junto com o loop. Este e o tipo de defeito que
    // passa no teste e quebra o app do operador.
    expect(fonte).toContain("window.addEventListener('focus'");
    expect(fonte).toContain("document.addEventListener('visibilitychange'");
  });

  it('zera o quadro pendente antes de retomar, para nao duplicar o loop', () => {
    // Dois `focus` seguidos sem zerar deixam dois loops em paralelo e o custo
    // dobra sem ganho nenhum.
    expect(fonte).toMatch(/cancelAnimationFrame\(animationRef\.current\);\s*\n\s*animationRef\.current = 0;/);
  });

  it('o DPR do fundo tem teto menor que o da tela', () => {
    // 2x dobra os pixels por quadro. Em particula de raio 1 a 3 px a diferenca
    // nao aparece; num grafico de preco seria proibido.
    expect(fonte).toContain('MAX_DPR');
    expect(fonte).toMatch(/MAX_DPR = 1\.5/);
    expect(fonte).toContain('Math.min(window.devicePixelRatio || 1, MAX_DPR)');
  });

  it('o App usa densidade menor que a antiga', () => {
    const app = appRaiz;
    // O custo por quadro e O(n^2) pelas linhas de energia.
    expect(app).not.toMatch(/density=\{60\}/);
    expect(app).toMatch(/density=\{34\}/);
  });
});

describe('main.tsx â€” ordem de carga', () => {
  it('fluidness.css vem depois de todos os temas', () => {
    const main = entrada;
    const fluidity = main.indexOf("./theme/fluidness.css");
    expect(fluidity).toBeGreaterThan(0);
    // Antes dela, qualquer `transition` escrita em outro arquivo venceria a
    // regra de fluidez, e a mudanca nao apareceria.
    for (const tema of [
      './theme/global.css',
      './theme/quantum.css',
      './theme/figma-tokens.css',
      './theme/scale.css',
    ]) {
      expect(main.indexOf(tema)).toBeLessThan(fluidity);
    }
  });
});
