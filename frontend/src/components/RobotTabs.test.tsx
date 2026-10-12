// @vitest-environment jsdom
// Abas ROBÔ reconstruída (05/10/2026). Sem mesa.
//
// O DONO PEDIU
// ============
// "deletar aba e reconstruir sem mesa apenas:
//    CABECALHO EM CIMA, OPERACAO AUTOMATICO COMANDOS,
//    GRAFICO OPERACIONAL AO VIVO EMBAIXO, MINITERMINAL AO VIVO"
//
// A VERSÃO ANTERIOR ESTAVA DESCONFIGURADA
// =========================================
// A `MesaXM` foi apagada e o `import './mesa-xm.css'` foi junto — o componente
// apagado era o único que carregava a folha. O painel novo usava as classes
// `mesa-*` e ficou sem NENHUMA regra: ticket desmontado, botão sem cor, campos
// empilhados.
//
// Dois testes cobrem os dois lados do mesmo defeito:
//   - este arquivo: a ESTRUTURA da página e as CLASSES do ticket;
//   - `src/theme/test_mesa_css.test.ts`: o IMPORT da folha.
//
// Só um dos dois passing deixa o defeito voltar. A folha existir não prova que
// ela é carregada; a folha ser carregada não prova que as classes batem.
//
// ESTES TESTES TAMBÉM TRAVAM A AUSÊNCIA DE MESA
// ================================================
// `mesa-xm.css` e as classes `mesa-*` não podem reaparecer: o dono mandou
// remover a mesa, e deixar o nome dela no estilo seria o mesmo defeito da folha
// órfã — código que parece vivo e não é.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const estado = vi.hoisted(() => ({
  auto: { ativo: false, simbolo: 'GOLD', timeframe: 'H1' } as Record<string, unknown>,
  ws: true,
  chamadas: [] as Array<{ url: string; body: Record<string, unknown> }>,
  /**
   * O preco que `/api/universal/quotes` devolve. `null` e a corretora sem
   * cotacao — e o cenario que trava o painel hoje, e por isso precisa ser
   * representavel num teste.
   */
  preco: 4140.6 as number | null,
}));

vi.mock('../hooks/queries', () => ({
  useAutoState: () => ({ data: estado.auto }),
}));

vi.mock('../hooks/useAppStore', () => ({
  useAppStore: (seletor: (s: unknown) => unknown) => seletor({ wsConnected: estado.ws }),
}));

/*
 * `?raw` devolve o FONTE do componente sem executá-lo. É o que permite ler as
 * linhas `className` e o `import` de CSS sem subir a árvore de React.
 *
 * IMPORT ESTÁTICO, e não `await import(...)`
 * ==========================================
 * Com `?raw` o Vite cria um módulo cujo default É a string. Então:
 *   - `import x from './a?raw'`  →  `x` é a string;          funciona.
 *   - `await import('./a?raw')` →  devolve `{ default: string }`; `x` seria o
 *     objeto, e `x.includes(...)` seria `undefined`, fazendo todo `expect` com
 *     `toContain`/`toMatch` passar a falhar sem mensagem util.
 *
 * Foi exatamente o que aconteceu: o teste acusou "o painel nao usa a classe"
 * num painel que USA. Não era o painel.
 *
 * O padrão é do projeto: ver `useAICommunication.test.ts`.
 */
import painel from './OperacaoAutomatica?raw';
import { zerarIaLigada } from '../hooks/useIaLigada';
const { default: OperacaoAutomatica, recusaDePlano } = await import(
  '../components/OperacaoAutomatica'
);
const { default: RobotTabs } = await import('../components/RobotTabs');

// Os dois blocos externos sês blocos externos são mockados: este arquivo testa a ESTRUTURA da
// página e o TICKET. Gráfico e terminal têm arquivos próprios.
vi.mock('./UniversalLiveTerminal', () => ({ default: () => <div data-testid="painel-mini" /> }));
vi.mock('./AcompanharModelos', () => ({ default: () => <div data-testid="painel-grafico" /> }));
/*
  `SeletorModelo` NAO e mockado, de proposito (05/10/2026).
  =========================================================
  Ele virou parte da operacao automatica, e este teste precisa enxergar isso de
  verdade. Se fosse mockado, "o seletor esta dentro da operacao automatica"
  passaria conferindo o mock -- e o mock nao sabe nada de onde ele esta.
*/
vi.mock('./SeletorModelo', async (importOriginal) => {
  const real = await importOriginal<typeof import('./SeletorModelo')>();
  return { default: real.default };
});

function renderPainel() {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <OperacaoAutomatica />
    </QueryClientProvider>,
  );
}

/**
 * O ticket está montado.
 *
 * Não usa `findByText('GOLD')`: o par e o timeframe ficam no mesmo `<span>`
 * ("GOLD H1"), entao o texto e partido em nos e o matcher por string isolada
 * nunca acha. O botao AUTO e o marcador que existe uma vez, com nome estavel.
 */
function ticketMontado() {
  return waitFor(() =>
    expect(document.querySelector('.robo-ticket-enviar')).toBeTruthy(),
  );
}

/**
 * O ticket montado E o padrao 1:1 já derivado do preço ao vivo.
 *
 * POR QUE ISTO EXISTE (10/10/2026)
 * ================================
 * MEDIDO: `sl_preco`/`tp_preco` no corpo do `/api/auto/config` vinham `undefined`
 * de forma INTERMITENTE (1 em ~8 rodadas da suíte inteira), e a asserção
 * `expect(cfg.body.sl_preco).toBeCloseTo(4136.46, 2)` reprovava com
 * "expected undefined ... NaN". Não é produto quebrado: desde 07/10 o SL/TP é
 * OPCIONAL, e `ligar()` só põe `sl_preco` no corpo quando `slN > 0` — se o
 * preset 1:1 ainda não derivou, o corpo sai corretamente sem o campo.
 *
 * A cadeia é assíncrona e tem vários elos:
 *   `/api/universal/quotes` -> `preco` -> `passo` (useMemo) -> `entrada`
 *     -> `useEffect` do 1:1 -> `setSl`/`setTp`.
 * O `ticketMontado()` espera só o BOTÃO existir, que acontece antes de o preço
 * chegar. Clicar no AUTO nesse meio enviava o corpo sem `sl_preco`. Sob a
 * suíte carregada (66 arquivos, event loop ocupado) o efeito do 1:1 atrasava e
 * a corrida aparecia — a assinatura de teste que lê o instante errado.
 *
 * A SOLUÇÃO é esperar o efeito do 1:1 TER ACONTECIDO, não o botão existir.
 * O `<p role="status">` só escreve "1:1 padrão · SL ... · TP ..." DEPOIS de
 * `setSl`/`setTp` (mesma linha do `setStatus`, em `OperacaoAutomatica` ~457).
 * Esperar por esse texto é esperar o estado que o caso declara que mede — e a
 * trava não afrouxa: o corpo continua tendo de trazer 4136.46 / 4144.74.
 */
function ticketComPadrao11() {
  return waitFor(() =>
    expect(document.querySelector('[role="status"]')?.textContent ?? '').toMatch(
      /1:1/,
    ),
  );
}

beforeEach(() => {
  estado.auto = { ativo: false, simbolo: 'GOLD', timeframe: 'H1' };
  estado.ws = true;
  estado.chamadas = [];
  estado.preco = 4140.6;
  window.localStorage.setItem('xau-active-account', 'mt5:metals');
  vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
    const body = JSON.parse(String(init?.body ?? '{}'));
    estado.chamadas.push({ url: String(url), body });
    if (String(url).includes('/api/universal/quotes')) {
      return {
        ok: true,
        json: async () => ({ quotes: estado.preco === null ? [] : [{ price: estado.preco }] }),
      };
    }
    return { ok: true, json: async () => ({ ok: true }) };
  });
});

/*
  ZERA O INTERRUPTOR DA IA — NO `beforeEach`, E NAO SO NO `afterEach` (10/10/2026)
  ==============================================================================
  O `useIaLigada` ȁ store de MODULO e nao esta mockado neste arquivo — entao
  ele ȁ o store real, compartilhado com o `useIaLigada.test.tsx` (e com
  qualquer arquivo que renderize `OperacaoAutomatica`) no MESMO worker.

  MEDIDO: o reset so no `afterEach` NAO fechava o vazamento. O `afterEach`
  roda DEPOIS de cada teste, mas o PRIMEIRO teste deste arquivo ja podia
  nascer com `ligada: true` deixado por outro arquivo que rodou antes — e o
  teste "AUTO aplica o 1:1 PADRAO e liga o motor" reprovava. Era
  INTERMITENTE (1 em 3 rodadas da suite inteira, medido em 10/10/2026: uma
  rodada 873/874 com este arquivo falhando, a seguinte 874/874), que ȁ a
  assinatura de estado compartilhado entre arquivos: depende da ordem que o
  runner escolhe, nao de teste fraco.

  A causa ȁ de PRODUTO? Nao. MEDIDO em `OperacaoAutomatica.tsx`: o handler do
  AUTO (`ligar()`, linha ~592) nao le `iaLigada` — o interruptor da IA ȁ
  inferencia, e o toggle AUTO ȁ o motor; sao independentes. O que vazava era
  so o ESTADO DE TESTE.

  Zerar no `beforeEach` ȁ o que fecha: cada teste comeca do estado que
  DECLAROU, nao do que o arquivo anterior deixou. Quem precisa do interruptor
  ligado dentro de um caso liga de novo — e ȁ o que o `useIaLigada.test.tsx`
  faz. O `afterEach` continua, como rede para o que rodar depois.
*/
beforeEach(() => {
  zerarIaLigada();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  zerarIaLigada();
});

describe('RobotTabs — a ordem que o dono pediu', () => {
  it('sub-abas com operacao, modelos, risco e operacoes', () => {
      /*
      SUB-ABAS (10/10/2026)
      =====================
      O dono pediu sub-abas na aba ROBÔ para separar Operação, Modelos, Risco
      e Operações. A página agora tem uma nav de sub-abas no topo, seguida do
      conteúdo da sub-aba ativa, seguido do gráfico (sempre visível).
      */
      const { container } = render(<RobotTabs />);
      const nav = container.querySelector('.robo-sub-abas');
      expect(nav).toBeTruthy();
      const abas = Array.from(nav!.querySelectorAll('.robo-sub-aba')).map(
        (b) => b.textContent,
      );
      expect(abas).toEqual(['Operação', 'Modelos', 'Risco', 'Operações']);
    });

  it('operacao automatica, grafico e miniterminal, nessa ordem', () => {
      /*
      O CABECALHO "OPERAÇÃO / ROBÔ" SAIU (06/10/2026)
      ================================================
      Este teste contava QUATRO filhos e o primeiro era `<header>`. Agora a
      página tem sub-abas no topo, o conteúdo da sub-aba ativa, e o gráfico
      sempre visível embaixo.

      O dono pediu para remover. E o motivo se sustenta: a barra lateral ja
      escreve `ROBÔ` em todas as paginas, e o cabecalho repetia o titulo mais
      uma frase explicando o que a tela logo abaixo faz sozinha. Alem do lugar
      ocupado, eram DOIS `h1` na mesma pagina — o titulo do cabecalho e o
      `h2`/`h1` da primeira seção — e dois `h1` sao ambiguidade para quem navega
      por leitor de tela, nao enfase.

      O que subiu no lugar: o botao `AUTO SIM`/`AUTO NAO`, que estava no
      RODAPE do ticket e e a acao principal da pagina. Ver o teste do botao no
      topo, em `RobotTabs.test.tsx`.
      */
      const { container } = render(<RobotTabs />);
      const filhos = Array.from(container.querySelectorAll('.robo > *'));
      // O primeiro e a nav de sub-abas, o segundo e o conteúdo da sub-aba ativa
      // (Operação), e o terceiro e o gráfico (sempre visível).
      expect(filhos).toHaveLength(3);
      expect(filhos[0].classList.contains('robo-sub-abas')).toBe(true);
      expect(filhos[1].getAttribute('aria-label')).toBe('Operação automática');
      expect(filhos[2].getAttribute('data-testid')).toBe('painel-grafico');
    });

    it('PROVA NEGATIVA: o cabecalho "ROBÔ" nao volta para a pagina', () => {
      /*
      Este e o teste que trava a REMOÇÃO do cabeçalho. Sem ele, voltar o
      `<header>` e so acrescentar uma linha — e ninguem reclama, porque a
      ordem dos blocos continua certa.
      */
      const { container } = render(<RobotTabs />);
      expect(container.querySelector('.robo-cabecalho')).toBeNull();
      // E o texto repetido nao aparece em lugar nenhum da pagina.
      expect(container.textContent ?? '').not.toContain('OPERAÇÃO');
    });

    it('o botao AUTO fica no TOPO, dentro do bloco de operação automática', () => {
      /*
      MEDIDO na captura: o botao vivia no rodape do ticket, embaixo de `passo`,
      dos presets e dos campos. Ligar o motor e a acao principal da pagina.

      Aqui a assercao e de POSICAO no DOM, e nao de texto: um botao que
     continue exista no rodape e seja tambem renderizado no topo passaria num teste
      que procurasse so pelo rotulo.
      */
      const { container } = render(<RobotTabs />);
      const auto = container.querySelector('[aria-label="Operação automática"]');
      expect(auto).toBeTruthy();
      // O botao esta DENTRO da secao de operação automática.
      expect(auto!.querySelector('.robo-auto-topo')).toBeTruthy();
      // E nao existe mais nenhum botao AUTO fora dela (o do rodape saiu).
      expect(container.querySelectorAll('.robo-ticket-enviar')).toHaveLength(1);
    });

    it('NAO tem mais o bloco separado de escolha de par', () => {
      // Este e o teste que trava a REMOÇÃO. Sem ele, voltar o bloco é só
      // importar um componente e nenhum teste reclama.
      const { container } = render(<RobotTabs />);
      expect(container.querySelector('[data-testid="painel-par"]')).toBeNull();
      expect(String(RobotTabs)).not.toContain('SeletorModelo');
      expect(String(RobotTabs)).not.toContain('painel-par');
    });

    it('o seletor de modelo esta DENTRO da operacao automatica', () => {
      // "operacao automatica completa com modelos": onde o automatico e ligado
      // e onde o modelo e escolhido. Sao o mesmo lugar.
      const { container } = renderPainel();
      // O campo existe de verdade, com o rotulo real do seletor.
      expect(
        container.querySelector('[aria-label="Modelo do robo"]'),
      ).toBeTruthy();
    });

    it('o par tem UM lugar so para ser escolhido, e e aqui', () => {
      // MEDIDO (05/10/2026): com o par apenas LIDO no painel e escolhido na
      // barra inferior, o Robô virou beco sem saida — sem par nao ha o que
      // desenhar no grafico nem o que operar. A escolha voltou para ca, dentro
      // da operacao automatica, alimentada pelo CATALOGO da corretora.
      const { container } = renderPainel();
      const seletor = container.querySelector('[aria-label="Par para operar"]') as HTMLSelectElement;
      expect(seletor).toBeTruthy();
      expect(seletor.tagName).toBe('SELECT');
      // E nao e mais uma leitura: `.robo-par-leitura` sumiu.
      expect(container.querySelector('.robo-par-leitura')).toBeNull();
    });

    it('a recusa ao ligar o AUTO aponta para o campo que esta nesta tela', () => {
      // A mensagem antiga mandava escolher o ativo na aba Inteligencia
      // Artificial — instrucao impossivel, porque o bloco que fazia a escolha
      // nao existia mais.
      //
      // Confere no FONTE do arquivo (`?raw`, variavel `painel`), e nao em
      // `String(Componente)`: o fonte compilado tem os comentarios removidos e
      // nao diz nada sobre o texto que o operador le. Aqui o que importa e a
      // LITERAL de texto, e para isso serve o fonte do arquivo.
      // `String(Componente)` era ler o codigo errado.
      expect(painel).toContain('Par para operar');
      // A frase que mandava para outra aba nao pode existir como texto de tela.
      expect(painel).not.toContain('Escolha o ativo na aba');
      expect(painel).not.toContain('antes de ligar o motor');
    });

  /*
    O DONO PEDIU DUAS VEZES QUE A ABA FOSSE MENOS:
    "apenas os tres blocos... nao poluir tela"
    "nada de prever tabela de previsao — isso nao ajuda em nada, o que importa
     e operar, ordens ao vivo, grafico operacional"
  */
  it('NAO tem painel de previsao nem botao de prever', () => {
    const fonte = painel + String(RobotTabs);
    // `PainelModelo` e o componente que tinha a tabela de previsao e o botao
    // "Prever". Ele saiu da aba; o seletor de par entrou no lugar.
    expect(fonte).not.toContain('RobotModelPanel');
    expect(fonte).not.toContain('Previsao');
    // E a pagina nao importa nenhum painel de previsao.
    expect(screen.queryByRole('button', { name: /prever/i })).toBeNull();
  });

  it('o grafico vem antes do miniterminal', () => {
    // Quem opera configura, confere no grafico e so entao olha o que ficou
    // aberto. Inverter mostra a posicao antes do grafico que a justifica.
    // O grafico mora na sub-aba Operacao (11/10/2026: um grafico so), e o
    // mini terminal so aparece quando a sub-aba "Operações" está ativa.
    const { container } = render(<RobotTabs />);
    const grafico = container.querySelector('[data-testid="painel-grafico"]');
    expect(grafico).toBeTruthy();
    // A sub-aba padrao e a Operacao, e e nela que o grafico esta.
    const subAbaAtiva = container.querySelector('.robo-sub-aba.ativa');
    expect(subAbaAtiva?.textContent).toBe('Operação');
  });

  it('a pagina tem a classe robo e nao usa a antiga', () => {
    const { container } = render(<RobotTabs />);
    expect(container.querySelector('.robo')).toBeTruthy();
    // `robot-page` era a classe da versao com sub-abas. Duas classes de pagina
    // significam duas folhas brigando pelo mesmo espaco.
    expect(container.querySelector('.robot-page')).toBeNull();
  });
});

describe('OperacaoAutomatica — as classes do ticket', () => {
  it('importa a folha da pagina', () => {
    // A linha exata que sumiu na versao quebrada.
    expect(painel).toMatch(/import\s+['"].*robo\.css['"]/);
  });

  it('usa classes robo- e nenhuma mesa-', () => {
    // A folha antiga se chamava "mesa" porque a mesa era a tela. Tira-la da
    // tela nao muda o nome do CSS, e deixar o prefixo seria manter na origem
    // do estilo o nome de uma coisa que o dono mandou remover.
    const classes = [...painel.matchAll(/className=\{?["'`]([^"'`]+)["'`]/g)]
      .map((m) => m[1])
      .join(' ');
    expect(classes).not.toMatch(/\bmesa-/);
    expect(painel).not.toMatch(/mesa-xm\.css/);
  });

  it('o bloco do ticket NAO existe mais na tela', () => {
    /*
    DECISAO DO DONO, 08/10/2026: o bloco `Token(s)` / `Valor no risco (SL)` /
    `Preco Quantidade` / `Stop Loss` / `Take Profit` / `passo 1:1..1:4` foi
    REMOVIDO da aba ROBÔ.

    MEDIDO na captura de 08/10 19:36 que motivou: `Stop loss (-2,00 USD) 2,00` e
    `Alvo (+2,00 USD) 2,00` saiam com VALOR FIXO, e as tres linhas de ordem
    sairam em 75670,29 / 75470,29 / 75270,29 — exatamente +200,00 e -200,00 em
    volta do preco. Um painel que parece configuravel e escreve numero fixo.

    Este caso nao e "o grid quebrou": e a REGRA nova. As seis areas do
    `grid-template-areas` nao existem porque os seis controles nao existem. E
    o `robo.css` ainda define as classes — uma folha com regra sem elemento e
    sobra, e `test_robo_css.test.ts` mede isso pelo outro lado.
    */
    renderPainel();
    expect(document.querySelector('.robo-ticket')).toBeNull();
    for (const area of ['lote', 'volume', 'protecao', 'presets']) {
      expect(
        document.querySelector(`.robo-ticket-${area}`),
        `a area .robo-ticket-${area} nao deveria mais estar na tela`,
      ).toBeNull();
    }
  });

  it('o botao AUTO mostra o estado, nao o lado', async () => {
    renderPainel();
    await ticketMontado();
    const botao = screen.getByRole('switch', { name: 'Operação automática' });
    expect(botao.textContent).toContain('NÃO');
    expect(botao.className).toContain('is-off');
    // "Comprar"/"Vender" aqui prometeriam algo que o painel nao decide: o lado
    // e do modelo.
    expect(screen.queryByRole('button', { name: /^Comprar/ })).toBeNull();
    expect(screen.queryByRole('button', { name: /^Vender/ })).toBeNull();
  });
});

describe('OperacaoAutomatica — a logica que ja funcionava', () => {
  it('AUTO aplica o 1:1 PADRAO e liga o motor, sem o operador digitar nada', async () => {
    /*
    O QUE MUDOU (06/10/2026)
    ========================
    Este teste afirmava que o primeiro clique no AUTO era RECUSADO com
    "Preencha SL e TP". Era o defeito que o dono reportou: um botao que so
    funciona depois de tres passos, e o painel sem preco nenhum para o
    operador calcular o numero.

    Agora o painel se configura: assim que o preco ao vivo chega, SL e TP
    nascem em 1:1. Ouro a 4.140,60, passo 0,1% = 4,1406:
    SL = 4.136,46 · TP = 4.144,74.

    O primeiro clique ja liga. E o valor preenchido fica VISIVEL no input — o
    app nao esconde o numero que vai mandar.

    O QUE MUDOU EM 08/10/2026 (decisao do dono): o bloco do ticket saiu da tela,
    entao nao ha mais input onde o valor fique visivel. Este caso deixou de
    medir o input e passou a medir o CORPO — que e onde o numero realmente
    viaja. E o preco: sem campo, o valor que o motor recebe deixa de ser
    conferivel na tela, e isso fica registrado aqui, nao escondido.
    */
    renderPainel();
    await ticketMontado();
    // Espera o preset 1:1 derivar o SL/TP do preço ao vivo ANTES de clicar —
    // senão o corpo sai sem `sl_preco` (ver `ticketComPadrao11`). A trava não
    // afrouxa: o corpo abaixo continua tendo de trazer 4136.46 / 4144.74.
    await ticketComPadrao11();
    const auto = screen.getByRole('switch', { name: 'Operação automática' });
    fireEvent.click(auto);
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(true),
    );
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/start'))).toBe(true),
    );
    const cfg = estado.chamadas.find((c) => c.url.includes('/api/auto/config'))!;
    expect(cfg.body.lote).toBe(0.01);
    expect(cfg.body.simbolo).toBe('GOLD');
    // PRECO, e nao distancia: e o que `MotorAuto` le (auto_engine.py:152).
    expect(cfg.body.sl_preco).toBeCloseTo(4136.46, 2);
    expect(cfg.body.tp_preco).toBeCloseTo(4144.74, 2);
  });

  it('o painel NAO tem onde o operador escrever o risco — e o padrao 1:1 manda', async () => {
    /*
    DECISAO DO DONO, 08/10/2026: o bloco do ticket saiu. Este caso exigia que o
    que o operador digitasse NAO fosse sobrescrito pelo padrao.

    Sem campo, nao ha o que sobrescrever. E o padrao continua mandando 1:1 — o
    que o dono mediu como problema foi o painel PARECER configuravel e escrever
    valor fixo, nao o padrao em si.

    Este caso agora trava a REGRA nova: o padrao 1:1 vai no corpo, e nao existe
    input para divergir dele.
    */
    renderPainel();
    await ticketMontado();
    expect(screen.queryByLabelText('Stop loss')).toBeNull();
    expect(screen.queryByLabelText('Take profit')).toBeNull();
    // O corpo abaixo exige `sl_preco`/`tp_preco` derivados do 1:1, então o
    // preset tem de ter rodado antes do clique (ver `ticketComPadrao11`).
    await ticketComPadrao11();
    fireEvent.click(screen.getByRole('switch', { name: 'Operação automática' }));
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(true),
    );
    const cfg = estado.chamadas.find((c) => c.url.includes('/api/auto/config'))!;
    expect(Number(cfg.body.sl_preco)).toBeCloseTo(4136.46, 2);
    expect(Number(cfg.body.tp_preco)).toBeCloseTo(4144.74, 2);
  });

  it('sem preco ao vivo o AUTO nao manda SL zero — manda sem os campos', async () => {
    /*
    Sem cotacao nao existe nivel. Mandar `sl_preco: 0` seria recusado pelo motor
    com um motivo generico, e o operador culparia a corretora por um numero que
    o painel inventou.

    MEDIDO em 07/10/2026: este caso afirmava que o painel nao chamava
    `/api/auto/config` sem preco. Com SL/TP opcionais (decisao do dono), o painel
    passa a chamar — e o que ele NAO pode fazer e mandar `sl_preco: 0`.
    O campo ausente e o que significa "sem protecao"; zero e um numero.
    */
    estado.preco = null;
    renderPainel();
    await ticketMontado();
    const auto = screen.getByRole('switch', { name: 'Operação automática' });
    fireEvent.click(auto);
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(true),
    );
    const cfg = estado.chamadas.find((c) => c.url.includes('/api/auto/config'));
    expect(cfg).toBeTruthy();
    expect((cfg!.body as Record<string, unknown>).sl_preco).toBeUndefined();
    expect((cfg!.body as Record<string, unknown>).tp_preco).toBeUndefined();
    expect((cfg!.body as Record<string, unknown>).sl_valor).toBeUndefined();
    expect((cfg!.body as Record<string, unknown>).tp_valor).toBeUndefined();
    // O que continua obrigatorio, presente:
    expect((cfg!.body as Record<string, unknown>).lote).toBeTruthy();
    expect((cfg!.body as Record<string, unknown>).simbolo).toBeTruthy();
  });

  it('PROVA NEGATIVA: o corpo LEVA sl_preco e tp_preco derivados do 1:1', async () => {
    // Sem este caso, uma correcao que so apagasse os dois campos passaria.
    // Antes media o que o operador DIGITAVA; agora mede o que o padrao PRODUZ,
    // porque o input saiu (decisao do dono, 08/10/2026).
    renderPainel();
    await ticketMontado();
    // Espera o 1:1 derivar os niveis antes do clique (ver `ticketComPadrao11`):
    // sem isso o corpo pode sair sem `sl_preco` e o caso reprova NaN.
    await ticketComPadrao11();
    const auto = screen.getByRole('switch', { name: 'Operação automática' });
    fireEvent.click(auto);
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(true),
    );
    const cfg = estado.chamadas.find((c) => c.url.includes('/api/auto/config'));
    const corpo = cfg!.body as Record<string, unknown>;
    expect(Number(corpo.sl_preco)).toBeCloseTo(4136.46, 2);
    expect(Number(corpo.tp_preco)).toBeCloseTo(4144.74, 2);
  });

  it('NAO envia ordem manual', async () => {
    // A ordem manual vive no grafico, no painel de `AcompanharModelos`. Aqui
    // seria duplicacao — e o bloco do ticket saiu, entao nem ha botao aqui.
    const { container } = renderPainel();
    await ticketMontado();
    expect(container.querySelector('.robo-ticket-enviar')).toBeTruthy();
    fireEvent.click(container.querySelector('.robo-ticket-enviar') as HTMLButtonElement);
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(true),
    );
    expect(estado.chamadas.some((c) => c.url.includes('/api/trade/order'))).toBe(false);
  });

  it('PROVA NEGATIVA: sem campo de quantidade NAO ha como mandar lote fora da faixa', async () => {
    /*
    Antes este caso digitava `50` num campo de lote e esperava a recusa
    "Volume entre 0.01 e 10". O campo saiu (decisao do dono, 08/10/2026), entao
    a faixa nao pode mais ser violada por digITACAO.

    O que este caso trava agora: o campo nao existe, e o AUTO liga com o lote
    padrao, que a ficha da corretora define.
    */
    renderPainel();
    await ticketMontado();
    expect(screen.queryByLabelText(/Quantidade em/)).toBeNull();
    fireEvent.click(screen.getByRole('switch', { name: 'Operação automática' }));
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/start'))).toBe(true),
    );
    const cfg = estado.chamadas.find((c) => c.url.includes('/api/auto/config'))!;
    expect(cfg.body.lote).toBe(0.01);
  });

  it('AUTO ligado desliga pelo stop', async () => {
    estado.auto = { ativo: true, simbolo: 'GOLD', timeframe: 'H1' };
    renderPainel();
    await ticketMontado();
    const auto = screen.getByRole('switch', { name: 'Operação automática' });
    expect(auto.textContent).toContain('SIM');
    expect(auto.className).toContain('is-on');
    fireEvent.click(auto);
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/stop'))).toBe(true),
    );
    // Desligar nao pode mandar config: seria religar com outro lote.
    expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(false);
  });

  it('os presets 1:1..1:4 SAIRAM da tela, e o 1:1 padrao continua no corpo', async () => {
    /*
    DECISAO DO DONO, 08/10/2026: o bloco do ticket saiu, e com ele o
    `passo` e os quatro botoes `1:1 1:2 1:3 1:4`.

    O texto longo deste caso foi preservado de proposito: ele documenta um
    defeito REAL que aconteceu e que nao pode voltar — o preset escrevia
    DISTANCIA onde o motor le PRECO (`auto_engine.py:152`), e `sl_preco: 4.14`
    em ouro e um stop invalido. Esse defeito nao existe mais porque o preset nao
    existe; o que este caso trava agora e a ausencia dele.
    */
    renderPainel();
    await ticketMontado();
    for (const nome of ['1:1', '1:2', '1:3', '1:4']) {
      expect(screen.queryByRole('button', { name: nome })).toBeNull();
    }
    expect(screen.queryByText(/^passo /)).toBeNull();
    // E o padrao 1:1 continua sendo o que vai para o motor.
    fireEvent.click(screen.getByRole('switch', { name: 'Operação automática' }));
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(true),
    );
    const cfg = estado.chamadas.find((c) => c.url.includes('/api/auto/config'))!;
    expect(Number(cfg.body.sl_preco)).toBeCloseTo(4136.46, 2);
    expect(Number(cfg.body.tp_preco)).toBeCloseTo(4144.74, 2);
  });

  it('PROVA NEGATIVA: sem preco ao vivo o AUTO nao manda SL zero', async () => {
    /*
    Sem preco nao existe nivel. Um padrao que mandasse 0 faria o motor recusar
    com motivo generico, e o operador culparia a corretora por um numero que o
    painel inventou (AGENTS.md 9). Antes isso era medido pelos inputs vazios;
    agora e medido pelo CORPO, que e onde o numero viaja.
    */
    estado.preco = null;
    renderPainel();
    await ticketMontado();
    fireEvent.click(screen.getByRole('switch', { name: 'Operação automática' }));
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(true),
    );
    const cfg = estado.chamadas.find((c) => c.url.includes('/api/auto/config'));
    const corpo = cfg!.body as Record<string, unknown>;
    expect(corpo.sl_preco === undefined || Number(corpo.sl_preco) > 0).toBe(true);
  });
});

describe('OperacaoAutomatica — sem conexao NAO envia ordem (05/10/2026)', () => {
  /*
    MEDIDO na captura da XM de 21:27: com "Ligacao perdida, estamos a tentar
    reconectar" no ar, o painel inteiro fica cinza e o botao `Colocar ordem` fica
    desabilitado. A XM RECUSA a ordem nesse estado.

    Antes, este painel so desabilitava com `ocupado` (requisicao em voo): com o
    websocket caido o botao continuava clicavel e o operador podia ligar o motor
    sem linha. Botao habilitado que falha na porta e o pior desfecho — o
    operador acha que enviou.
  */

  afterEach(() => {
    estado.ws = true;
  });

  it('PROVA NEGATIVA: com o websocket caido, o botao AUTO fica desabilitado', async () => {
    estado.ws = false;
    renderPainel();
    await ticketMontado();
    const auto = screen.getByRole('switch', { name: 'Operação automática' });
    expect((auto as HTMLButtonElement).disabled).toBe(true);
    expect(auto.textContent).toContain('SEM CONEXAO');
  });

  it('PROVA NEGATIVA: com a linha caida, NENHUMA chamada sai para o gateway', async () => {
    /*
      Este teste nao procura a mensagem de status, e a MEDIDA que explica por
      que: em jsdom (e em qualquer navegador) um botao `disabled` NAO dispara
      `click`. A primeira versao deste teste exigia a mensagem e falhava — e a
      falha era informative: o `disabled` ja e a barreira.

      A guarda dentro de `alternar` continua existindo para o caminho que o
      `disabled` nao cobre: acionamento por codigo, por automacao ou por um
      `dispatchEvent` sintetico. Aqui o que se prova e a propriedade que
      importa: com a conexao perdida, nada chega ao gateway.
    */
    estado.ws = false;
    renderPainel();
    await ticketMontado();
    fireEvent.click(screen.getByRole('switch', { name: 'Operação automática' }));
    await waitFor(() => {
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(false);
    });
    expect(estado.chamadas.some((c) => c.url.includes('/api/auto/start'))).toBe(false);
    expect(estado.chamadas.some((c) => c.url.includes('/api/auto/stop'))).toBe(false);
    expect(estado.chamadas.some((c) => c.url.includes('/api/trade/order'))).toBe(false);
  });

  it('o title do botao diz QUE falta conexao, e nao um erro generico', async () => {
    estado.ws = false;
    renderPainel();
    await ticketMontado();
    const auto = screen.getByRole('switch', { name: 'Operação automática' });
    expect(auto.getAttribute('title')).toMatch(/[Ll]igacao perdida/);
  });

  it('PROVA NEGATIVA: com a conexao de volta, o botao volta a ficar clicavel', async () => {
    // A trava nao pode colar: um botao que so desabilita nao tem volta.
    estado.ws = false;
    renderPainel();
    await ticketMontado();
    expect((screen.getByRole('switch', { name: 'Operação automática' }) as HTMLButtonElement).disabled).toBe(true);

    cleanup();
    estado.ws = true;
    renderPainel();
    await ticketMontado();
    expect((screen.getByRole('switch', { name: 'Operação automática' }) as HTMLButtonElement).disabled).toBe(false);
  });
});

/*
  SUB-ABAS DUPLICADAS (11/10/2026)
  ================================
  O dono reportou "sub abas duplicadas" nas capturas da ultima sessao. MEDIDO
  em `RobotTabs.tsx` antes da correcao: a sub-aba Risco renderizava o painel
  INTEIRO de novo — segundo botao AUTO, segundo "Par para operar", segundo
  bloco de IA — e a tabela de modelos treinados aparecia DUAS vezes na mesma
  tela (dentro da sub-aba Operacao, em `OperacaoAutomatica`, e de novo na
  sub-aba Modelos).

  E o AGENTS.md 5 na tela: dois lugares com o mesmo dado, e o operador sem
  saber qual dos dois manda.

  Estes casos sao as travas. O primeiro e de PROVA NEGATIVA: se o painel
  voltar para a sub-aba Risco, ele reprova.
*/
describe('RobotTabs — cada sub-aba mostra UMA coisa só (11/10/2026)', () => {
  it('PROVA NEGATIVA: a sub-aba Risco nao monta o painel de operação de novo', async () => {
    const { container } = render(<RobotTabs />);
    // Na Operação existe exatamente UM interruptor AUTO. O seletor é a
    // classe do botão: `aria-label="Operação automática"` também carrega a
    // SEÇÃO (o wrapper do painel), então contar por ele leria dois elementos
    // mesmo com um botão só — assinatura de teste que lê o campo errado.
    expect(container.querySelectorAll('.robo-auto-topo')).toHaveLength(1);

    fireEvent.click(screen.getByRole('tab', { name: 'Risco' }));
    await waitFor(() =>
      expect(container.querySelector('[aria-label="Controle de risco"]')).toBeTruthy(),
    );

    // ...e na de Risco nao existe NENHUM: nem a seção, nem o botão AUTO.
    expect(container.querySelector('[aria-label="Operação automática"]')).toBeNull();
    expect(container.querySelectorAll('.robo-auto-topo')).toHaveLength(0);
    expect(screen.queryByRole('switch', { name: 'Operação automática' })).toBeNull();
    // O que a aba promete é o que ela tem: os campos de limite, abertos.
    expect(container.querySelector('[aria-label="Confiança mínima (%)"]')).toBeTruthy();
  });

  it('PROVA NEGATIVA: a tabela de modelos so e montada na sub-aba Modelos', async () => {
    const { container } = render(<RobotTabs />);
    // Operação: o painel usa o SELETOR de modelo, não a tabela de modelos.
    expect(container.querySelector('[aria-label="Modelos treinados"]')).toBeNull();

    fireEvent.click(screen.getByRole('tab', { name: 'Modelos' }));
    await waitFor(() =>
      expect(container.querySelector('[aria-label="Modelos treinados"]')).toBeTruthy(),
    );
  });

  it('declarar limite na sub-aba Risco aplica SEM ligar o motor', async () => {
    const { container } = render(<RobotTabs />);
    fireEvent.click(screen.getByRole('tab', { name: 'Risco' }));
    await waitFor(() =>
      expect(container.querySelector('[aria-label="Controle de risco"]')).toBeTruthy(),
    );
    fireEvent.change(container.querySelector('[aria-label="Confiança mínima (%)"]') as HTMLElement, {
      target: { value: '72' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Aplicar limites ao motor' }));
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(true),
    );
    const cfg = estado.chamadas.find((c) => c.url.includes('/api/auto/config'))!;
    expect(cfg.body.confianca_minima).toBe(72);
    // A gaveta de risco nao e um segundo caminho para ligar o motor.
    expect(estado.chamadas.some((c) => c.url.includes('/api/auto/start'))).toBe(false);
    expect(estado.chamadas.some((c) => c.url.includes('/api/trade/order'))).toBe(false);
  });

  it('os campos de risco mostram o que o MOTOR ja guarda', async () => {
    /*
    MEDIDO antes da correcao: o motor guardava `confianca_minima = 72` e a
    sub-aba Risco abria com o campo VAZIO ("nao declarada") — cada aba era uma
    instancia separada do painel, e o que existia do outro lado nao aparecia.
    O operador via limite apagado.
    */
    estado.auto = {
      ativo: false,
      simbolo: 'GOLD',
      timeframe: 'H1',
      limites: { confianca_minima: 72, max_operacoes_dia: 5 },
    };
    const { container } = render(<RobotTabs />);
    fireEvent.click(screen.getByRole('tab', { name: 'Risco' }));
    await waitFor(() => {
      const campo = container.querySelector(
        '[aria-label="Confiança mínima (%)"]',
      ) as HTMLInputElement | null;
      expect(campo?.value).toBe('72');
    });
    const porDia = container.querySelector('[aria-label="Operações por dia"]') as HTMLInputElement;
    expect(porDia.value).toBe('5');
    // Campo sem valor no motor continua declarando "vazio = não declarado".
    const banca = container.querySelector('[aria-label="Banca"]') as HTMLInputElement;
    expect(banca.value).toBe('');
  });
});

/*
  A RECUSA DE PLANO APONTA O DESBLOQUEIO (11/10/2026)
  ===================================================
  MEDIDO: numa conta Free o 403 de `/api/auto/start` trazia
  `code: PLAN_REQUIRED` e `required_plans: ['VIP', 'VIPS']` no corpo — o
  `plano_gate.resposta_bloqueio` já manda tudo —, e a tela imprimia só
  `error`. O operador lia "recurso nao liberado no plano atual: auto_engine"
  sem ter onde ativar: o gateway já expunha
  `/api/subscriptions/{plans,me,activate}` e o frontend não tinha UM
  consumidor. Um bloqueio sem o caminho do desbloqueio é o beco sem saída que
  este projeto já registrou duas vezes.
*/
describe('recusa de plano aponta o desbloqueio (11/10/2026)', () => {
  it('PROVA: 403 PLAN_REQUIRED em /api/auto/start vira "Configurações → Plano"', async () => {
    vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body ?? '{}'));
      estado.chamadas.push({ url: String(url), body });
      if (String(url).includes('/api/universal/quotes')) {
        return { ok: true, json: async () => ({ quotes: [{ price: 4140.6 }] }) };
      }
      if (String(url).includes('/api/auto/start')) {
        return {
          ok: false,
          status: 403,
          json: async () => ({
            ok: false,
            error: 'plano local atual não inclui: auto_engine',
            code: 'PLAN_REQUIRED',
            feature: 'auto_engine',
            required_plans: ['VIP', 'VIPS'],
          }),
        };
      }
      return { ok: true, json: async () => ({ ok: true }) };
    });

    renderPainel();
    await ticketMontado();
    await ticketComPadrao11();
    fireEvent.click(screen.getByRole('switch', { name: 'Operação automática' }));

    await waitFor(() => {
      const texto = document.querySelector('.robo-observacao')?.textContent ?? '';
      expect(texto).toContain('Configurações → Plano');
      expect(texto).toContain('VIP');
    });
    // PROVA NEGATIVA: o `error` cru do backend não pode ser mais o texto final.
    const texto = document.querySelector('.robo-observacao')?.textContent ?? '';
    expect(texto).not.toBe('plano local atual não inclui: auto_engine');
    // A ordem não foi enviada por causa disso — o gate é do motor, não da tela.
    expect(estado.chamadas.some((c) => c.url.includes('/api/trade/order'))).toBe(false);
  });

  it('PROVA: recusaDePlano só fala quando o gateway falou de plano', () => {
    // Sem 403 e sem o code, a função é muda — senão qualquer recusa viraria
    // "ative um plano" e o operador seria mandado para Configurações por um
    // erro de lote ou de campo.
    expect(recusaDePlano({ error: 'defina lote' }, 400)).toBe('');
    expect(recusaDePlano({ error: 'x', code: 'OUTRO' }, 500)).toBe('');
    const comLista = recusaDePlano({ code: 'PLAN_REQUIRED', required_plans: ['VIP'] }, 403);
    expect(comLista).toContain('VIP');
    expect(comLista).toContain('Configurações → Plano');
    // Sem a lista, o texto ainda aponta o lugar, sem inventar nome de plano.
    const semLista = recusaDePlano({ code: 'PLAN_REQUIRED' }, 403);
    expect(semLista).toContain('um plano superior');
    expect(semLista).toContain('Configurações → Plano');
  });
});

/*
  SEM CONTA, SEM CORRETORA NA TELA — NADA DE MT5 FIXO (11/10/2026)
  ================================================================
  Decisao do dono: na aba ROBO, nas partes de cima e no grafico, "MT5" fixo
  nao pode — e modelo/par BTCUSD fixo, menos ainda. Antes o `broker` nascia
  `'mt5'` (e o par, do primeiro modelo publicavel, gravado no store): a aba
  inteira operava MT5/BTCUSD sem ninguem escolher.

  O `beforeEach` deste arquivo grava `xau-active-account = mt5:metals`; aqui
  a chave e APAGADA antes de renderizar, para medir a tela sem conta.
*/
describe('sem conta salva: recusa com motivo, nunca MT5 fixo (11/10/2026)', () => {
  it('PROVA: o cabecalho diz "sem corretora", e o AUTO recusa nomeando onde ativar', async () => {
    window.localStorage.removeItem('xau-active-account');
    // Sem conta e sem par no motor: nada para presumir.
    estado.auto = { ativo: false, simbolo: '', timeframe: '' };
    renderPainel();
    await ticketMontado();

    const cabeca = document.querySelector('.robo-comandos .muted')?.textContent ?? '';
    expect(cabeca).toContain('sem corretora');
    // PROVA NEGATIVA: o nome fixo nao pode ser o texto final.
    expect(cabeca).not.toContain('MT5');

    fireEvent.click(screen.getByRole('switch', { name: 'Operação automática' }));
    await waitFor(() => {
      const texto = document.querySelector('.robo-observacao')?.textContent ?? '';
      // A escolha existe de verdade: o Ativar das Conexoes grava a conta
      // ativa (ver `ConnectionSettings`), entao a mensagem aponta para la.
      expect(texto).toContain('Conexões');
      expect(texto).toContain('Ativar');
    });
    // Nada saiu para o gateway: a recusa e da tela, antes de qualquer POST.
    expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(false);
    expect(estado.chamadas.some((c) => c.url.includes('/api/auto/start'))).toBe(false);
  });

  it('PROVA: sem par escolhido, o seletor nao presume par nenhum', async () => {
    window.localStorage.removeItem('xau-active-account');
    estado.auto = { ativo: false, simbolo: '', timeframe: '' };
    const { container } = renderPainel();
    await ticketMontado();

    const seletor = container.querySelector(
      '[aria-label="Par para operar"]',
    ) as HTMLSelectElement;
    expect(seletor).toBeTruthy();
    // O valor e vazio: nenhum BTCUSD (nem outro par) nasce escolhido, e nada
    // foi gravado no store por tabela.
    expect(seletor.value).toBe('');
  });
});

/*
  UM GRAFICO SO, NA SUB-ABA OPERACAO (11/10/2026)
  ===============================================
  Decisao do dono: duas sub-abas estavam com o grafico duplicado — remover de
  uma, apenas 1 grafico. Antes o `<AcompanharModelos />` era sempre visivel,
  embaixo de qualquer sub-aba: o mesmo grafico em quatro lugares, quatro
  consultas e quatro polls para o mesmo par.
*/
describe('um grafico so, na sub-aba Operacao (11/10/2026)', () => {
  const quantosGraficos = (container: HTMLElement) =>
    container.querySelectorAll('[data-testid="painel-grafico"]').length;

  it('PROVA: na Operacao (padrao), o grafico esta la — e e UM so', () => {
    const { container } = render(<RobotTabs />);
    expect(container.querySelector('.robo-sub-aba.ativa')?.textContent).toBe('Operação');
    expect(quantosGraficos(container)).toBe(1);
  });

  it.each(['Modelos', 'Risco', 'Operações'] as const)(
    'PROVA: na sub-aba %s, nao ha grafico nenhum',
    async (aba) => {
      const { container } = render(<RobotTabs />);
      fireEvent.click(screen.getByRole('tab', { name: aba }));
      await waitFor(() => {
        expect(container.querySelector('.robo-sub-aba.ativa')?.textContent).toBe(aba);
      });
      expect(quantosGraficos(container)).toBe(0);
    },
  );

  it('PROVA: voltar para a Operacao traz o grafico de volta — ainda UM so', async () => {
    const { container } = render(<RobotTabs />);
    fireEvent.click(screen.getByRole('tab', { name: 'Modelos' }));
    await waitFor(() => {
      expect(container.querySelector('.robo-sub-aba.ativa')?.textContent).toBe('Modelos');
    });
    expect(quantosGraficos(container)).toBe(0);

    fireEvent.click(screen.getByRole('tab', { name: 'Operação' }));
    await waitFor(() => {
      expect(container.querySelector('.robo-sub-aba.ativa')?.textContent).toBe('Operação');
    });
    expect(quantosGraficos(container)).toBe(1);
  });

  it('PROVA NEGATIVA: o grafico fora da Operacao voltaria sem nenhum teste reclamar', () => {
    // Sem este caso, alguem recoloca o `<AcompanharModelos />` fora da
    // condicao e so o caso da Operacao continuaria passando — o defeito
    // (grafico em quatro lugares) voltaria verde.
    const { container } = render(<RobotTabs />);
    const abas = ['Operação', 'Modelos', 'Risco', 'Operações'] as const;
    let total = 0;
    for (const aba of abas) {
      fireEvent.click(screen.getByRole('tab', { name: aba }));
      total += quantosGraficos(container);
    }
    // Somadas as quatro sub-abas, ha exatamente UMA montagem de grafico.
    expect(total).toBe(1);
  });
});
