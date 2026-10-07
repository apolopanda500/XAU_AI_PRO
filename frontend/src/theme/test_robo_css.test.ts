// @vitest-environment jsdom
// A folha CSS da página ROBÔ existe, é carregada e define as classes usadas.
//
// ESTE E O TESTE DO DEFEITO QUE QUEBROU A ABA
// =============================================
// Em 05/10/2026 a `MesaXM` foi apagada e o `import './mesa-xm.css'` foi junto —
// o componente apagado era o ÚNICO que carregava a folha. O painel novo usava as
// classes `mesa-*` e ficou sem NENHUMA regra: ticket desmontado, botão sem cor,
// campos empilhados. A aba ficou impossível de operar.
//
// A suíte passou. Nenhum teste verificava o CSS, e o vitest não verifica por
// conta própria: em jsdom folha de estilo não é aplicada.
//
// ESTE ARQUIVO FECHA A METADE QUE FALTA
// =======================================
// `RobotTabs.test.tsx` trava a ESTRUTURA e as CLASSES. Aqui é travado o IMPORT
// e o CONTEÚDO da folha.
//
// Só um dos dois passing deixa o defeito voltar:
//   - folha existe mas ninguém importa → a aba desconfigura (o que aconteceu);
//   - folha é importada mas não define a classe → a aba desconfigura igual.

import { describe, expect, it } from 'vitest';

/*
 * `?raw` devolve o FONTE como STRING, e o acesso é direto, sem `.default`.
 *
 * IMPORT ESTÁTICO, e não `await import(...)`
 * ==========================================
 * Com `?raw`, `await import('./a?raw')` devolve `{ default: string }` — o
 * objeto, não a string. `x.includes(...)` seria `undefined` e todo `expect`
 * com `toContain`/`toMatch` falharia acusando o componente de não usar uma
 * classe que ele usa. Foi o que aconteceu na primeira versão deste arquivo.
 *
 * `import x from './a?raw'` dá a string. É o padrão do projeto: ver
 * `useAICommunication.test.ts`.
 */
import painel from '../components/OperacaoAutomatica?raw';
import pagina from '../components/RobotTabs?raw';
import seletor from '../components/SeletorModelo?raw';
import grafico from '../components/AcompanharModelos?raw';
import entrada from '../main?raw';

/**
 * Lê um CSS do disco.
 *
 * `?raw` em CSS NÃO funciona aqui: o vitest troca o módulo de CSS por um stub
 * vazio antes de o `?raw` valer, e a folha volta com 0 bytes. Medido nesta
 * sessão: `import x from './robo.css?raw'` devolve string vazia, e
 * `import.meta.glob('*.css', { query: '?raw' })` traz todas as folhas com 0.
 *
 * Por isso `node:fs`. O `@ts-expect-error` é necessário porque `@types/node`
 * não está instalado neste projeto e um `import` nomeado quebraria o
 * `tsc --noEmit`, que é gate. Por ser `@ts-expect-error`, ele FALHA se um dia
 * `node:fs` passar a ter tipagem — obrigando a remover a supressão.
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

/** As 6 áreas do ticket, cada uma com `grid-area` própria no CSS. */
const AREAS = ['preco', 'lote', 'volume', 'protecao', 'presets', 'enviar'];

describe('robo.css — a folha da pagina existe e e substancial', () => {
  it('nao esta vazia', async () => {
    // Folha vazia é o mesmo defeito de folha órfã: o código parece correto e
    // a tela não tem estilo nenhum.
    const folha = await lerCss('robo.css');
    expect(folha.length).toBeGreaterThan(1500);
  });

  it('e a página E o painel a importam', () => {
    // Os dois. A página monta os blocos e a folha a aplica; se só um importa,
    // a página abre com o CSS de outro lugar herdado do `global.css` e o
    // ticket fica do tamanho do texto.
    expect(pagina).toMatch(/import\s+['"].*robo\.css['"]/);
    expect(painel).toMatch(/import\s+['"].*robo\.css['"]/);
  });
});

describe('robo.css — toda classe usada pelo ticket tem regra', () => {
  it('cada grid-area do ticket existe como regra', async () => {
    const folha = await lerCss('robo.css');
    for (const area of AREAS) {
      expect(folha, `falta a regra .robo-ticket-${area}`).toContain(`.robo-ticket-${area}`);
    }
  });

  it('o painel usa exatamente as classes que a folha define', async () => {
    // Se o painel trocar o nome de uma classe sem atualizar o CSS, o defeito
    // volta pelo outro lado: classe sem regra = elemento sem estilo.
    const folha = await lerCss('robo.css');
    for (const area of AREAS) {
      expect(painel, `a folha define robo-ticket-${area}, o painel nao usa`).toContain(
        `robo-ticket-${area}`,
      );
    }
  });

  it('o botao AUTO tem estado ligado e desligado', async () => {
    // A cor do botão é o que diz se o motor está rodando. Sem os dois
    // estados, o operador liga sem ver que ligou.
    const folha = await lerCss('robo.css');
    expect(folha).toContain('.robo-ticket-enviar.is-off');
    expect(folha).toContain('.robo-ticket-enviar.is-on');
    expect(painel).toContain("autoAtivo ? 'is-on' : 'is-off'");
  });

  it('toda classe do seletor de par tem regra', async () => {
    // O bloco "Ativo e periodo" entrou depois. Sem regra, os dois <select>
    // empilham em largura cheia e o operador perde a leitura do par.
    const folha = await lerCss('robo.css');
    for (const c of ['robo-par', 'robo-par-linha', 'robo-par-ativo', 'robo-par-modelo']) {
      expect(folha, `falta a regra .${c}`).toContain(`.${c}`);
      expect(seletor, `a folha define .${c}, o seletor nao usa`).toContain(c);
    }
  });
});

/*
  O DONO PEDIU DUAS VEZES QUE A ABA FOSSE MENOS
  ===============================================
  "apenas os tres blocos... nao poluir tela"
  "nada de prever tabela de previsao — isso nao ajuda em nada, o que importa e
   operar, ordens ao vivo, grafico operacional"
*/
/*
  Remove os COMENTARIOS antes de casar o texto.

  Sem isto o teste acusou o PROPRIO arquivo: o comentario que EXPLICA por que a
  previsao saiu ("o botao 'Prever' saiu") casa com `/Prever/i`, e o teste falha
  acusando codigo que nao existe. O sinal nao e a palavra: e o que o componente
  FAZ, entao a verificacao e sobre o codigo sem comentario.
*/
function semComentarios(fonte: string): string {
  return fonte
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/(^|[^:])\/\/.*$/gm, '$1');
}

describe('robo — o que foi removido nao volta sem querer', () => {
  it('o seletor de par NAO tem previsao nem botao de prever', async () => {
    // O componente anterior (`RobotModelPanel`) tinha os dois. Ele foi trocado
    // pelo `SeletorModelo`, que so escolhe par.
    await lerCss('robo.css');
    const codigo = semComentarios(seletor);
    expect(codigo).not.toMatch(/Prever/i);
    expect(codigo).not.toMatch(/Previsao|previsao/);
  });

  it('o grafico NAO tem tabela de sinais', async () => {
    // Os sinais continuam como MARCADORES no candle. A tabela repetia os
    // mesmos numeros abaixo dos botoes de operar.
    await lerCss('robo.css');
    const codigo = semComentarios(grafico);
    expect(codigo).not.toMatch(/dense-grid/);
    expect(codigo).not.toMatch(/Confiança/);
  });

  it('a pagina nao importa painel de previsao', async () => {
    await lerCss('robo.css');
    expect(pagina).not.toContain('RobotModelPanel');
  });
});

describe('robo.css — a pagina e uma coluna que nao encavilita', () => {
  it('a pagina e flex column com gap', async () => {
    // A ordem dos blocos é a que o dono pediu. `flex column` + `gap` é o que
    // impede um bloco de passar por cima do outro — que foi o sintoma da
    // versão quebrada.
    const folha = await lerCss('robo.css');
    expect(folha).toMatch(/\.robo\s*\{[^}]*flex-direction:\s*column/);
    expect(folha).toMatch(/\.robo\s*\{[^}]*gap:/);
  });

  it('o cabecalho "ROBÔ" nao esta mais na pagina', async () => {
    /*
    O cabecalho saiu a pedido do dono (06/10/2026): a barra lateral ja escreve
    `ROBÔ` em todas as paginas, e o cabecalho repetia o titulo mais uma frase
    que explicava o que a tela ja mostra. Alem disso eram DOIS `h1` na mesma
    pagina — o `h1` do cabecalho e o titulo da primeira secao — e dois `h1` sao
    ambiguidade para quem navega por leitor de tela.

    Este teste trava a REMOCAO: `.robo-cabecalho` nao pode voltar na folha nem
    no componente. Sem ele, voltar o `<header>` e acrescentar CSS de volta, e a
    ordem dos blocos continua passando.
    */
    /*
    O teste procura a REGRA, e nao a PALAVRA: `/^\s*\.robo-cabecalho[^{]*\{/`
    casa um seletor de CSS, e nao um comentario.

    A diferenca nao e preciosismo. A folha tem um comentario que DIZ que a
    regra saiu e por que — e sem comentarios desse tipo, a proxima pessoa que
    mexer aqui reintroduz o cabecalho sem saber que ele foi pedido para fora.
    Um teste que reprovasse o comentario obrigaria a apagar a explicacao, que
    e exatamente o oposto do que o AGENTS.md 11 pede.
    */
    const folha = await lerCss('robo.css');
    expect(folha).not.toMatch(/^\s*\.robo-cabecalho[^{]*\{/m);
    // E o componente tambem nao tem o elemento.
    expect(pagina).not.toMatch(/<header className="robo-cabecalho">/);
  });

  it('o botao AUTO tem regra propria no topo', async () => {
    /*
    O botao subiu do rodape do ticket para o `section-head`. Ele carrega
    `grid-area: enviar` do grid do ticket, e no topo nao ha grid: sem uma regra
    propria ele herda `min-height: 44px` e `min-width: 148px` de quando era um
    bloco do rodape, e volta a ser o maior elemento da fileira — que e parte do
    que escondia o controle.
    */
    const folha = await lerCss('robo.css');
    expect(folha).toMatch(/\.robo-auto-topo\s*\{[^}]*grid-area:\s*auto/);
    expect(folha).toMatch(/\.robo-auto-topo\s*\{[^}]*margin-inline-start:\s*auto/);
  });

  it('o grid do ticket declara as 6 areas em area, sem sobrando', async () => {
    // Uma área no `grid-template-areas` sem elemento que a use deixa um buraco
    // na faixa — e um elemento com `grid-area` sem declaração na folha não é
    // posicionado, cai no auto e empurra o resto.
    const folha = await lerCss('robo.css');
    const bloco = folha.slice(folha.indexOf('.robo-ticket {'), folha.indexOf('.robo-ticket-lote'));
    for (const area of AREAS) {
      expect(bloco, `grid-template-areas sem '${area}'`).toContain(area);
    }
  });

  it('o botao desce inteiro em janela estreita', async () => {
    // O elemento que não pode ficar estreito é o botão AUTO: é onde o clique
    // errado custa dinheiro.
    const folha = await lerCss('robo.css');
    const estreito = folha.slice(folha.indexOf('@media (max-width: 860px)'));
    expect(estreito).toMatch(/\.robo-ticket-enviar\s*\{[^}]*width:\s*100%/);
  });
});

describe('A mesa nao volta nem pelo CSS', () => {
  it('nenhuma fonte da pagina IMPORTA mesa-xm.css', () => {
    // O nome da folha antiga se chamava "mesa" porque a mesa era a tela. Tirá-la
    // da tela não muda o nome do CSS, e deixar o prefixo seria manter na
    // origem do estilo o nome de uma coisa que o dono mandou remover.
    //
    // A busca é por `import`, e não pela palavra solta: `RobotTabs.tsx` e
    // `OperacaoAutomatica.tsx` citam `mesa-xm.css` nos COMENTÁRIOS que
    // documentam por que ela saiu. Um teste que accuse menção em comentário
    // proíbe documentar o defeito, e o próximo vai recriar a dependência sem
    // conseguir escrever por quê.
    for (const fonte of [pagina, painel, entrada]) {
      const fonteSemComentario = fonte
        .replace(/\/\*[\s\S]*?\*\//g, '')
        .replace(/\/\/[^\n]*/g, '');
      expect(fonteSemComentario).not.toMatch(/mesa-xm\.css/);
    }
  });

  it('as fontes documentam por que a folha antiga saiu', () => {
    // Comentário que some no primeiro refactor é comentário perdido. Este
    // teste é bobo de propósito: ele existe para o texto ficar.
    expect(pagina).toMatch(/mesa/);
    expect(painel).toMatch(/mesa/);
  });

  it('a folha nova nao tem nenhuma regra mesa-', async () => {
    const folha = await lerCss('robo.css');
    expect(folha).not.toMatch(/^\s*\.mesa-/m);
  });

  it('fluidness.css continua carregado, porque define os tokens', () => {
    // `fluidness.css` declara `--fluido-*`. Sem o import em `main.tsx`, os
    // tokens não existem e `var(--fluido-medio)` cai para nada.
    expect(entrada).toMatch(/import\s+['"].*fluidness\.css['"]/);
  });
});
