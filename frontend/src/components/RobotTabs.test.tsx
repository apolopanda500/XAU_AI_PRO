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
const { default: OperacaoAutomatica } = await import('../components/OperacaoAutomatica');
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

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('RobotTabs — a ordem que o dono pediu', () => {
it('operacao automatica, grafico e miniterminal, nessa ordem', () => {
      /*
      O CABECALHO "OPERAÇÃO / ROBÔ" SAIU (06/10/2026)
      ================================================
      Este teste contava QUATRO filhos e o primeiro era `<header>`. Agora sao
      TRES, e o primeiro e o bloco de operação automática.

      O dono pediu para remover. E o motivo se sustenta: a barra lateral ja
      escreve `ROBÔ` em todas as paginas, e o cabeçalho repetia o titulo mais
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
      // Os tres sao os blocos, cada um dentro da sua barreira de erro.
      //
      // O `aria-label` vem do `section` que CADA bloco declara. Os blocos
      // mockados nao tem `aria-label` proprio, entao o teste confere a POSICAO
      // deles, e nao o nome - e a ordem que importa aqui.
      expect(filhos).toHaveLength(3);
      expect(filhos[0].getAttribute('aria-label')).toBe('Operação automática');
      expect(filhos[1].getAttribute('data-testid')).toBe('painel-grafico');
      expect(filhos[2].getAttribute('data-testid')).toBe('painel-mini');
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
    const { container } = render(<RobotTabs />);
    const ordem = Array.from(container.querySelectorAll('[data-testid]')).map((n) =>
      n.getAttribute('data-testid'),
    );
    expect(ordem.indexOf('painel-grafico')).toBeLessThan(ordem.indexOf('painel-mini'));
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

  it('o ticket tem as 6 areas do grid', () => {
    // Preco, lote, valor no risco, protecao, presets e botao. Cada uma com
    // `grid-area` propria: sem isso o `grid-template-areas` do CSS nao acha
    // ninguem e a faixa desmorona.
    renderPainel();
    expect(document.querySelector('.robo-ticket')).toBeTruthy();
    for (const area of ['preco', 'lote', 'volume', 'protecao', 'presets', 'enviar']) {
      expect(
        document.querySelector(`.robo-ticket-${area}`),
        `falta a area .robo-ticket-${area}`,
      ).toBeTruthy();
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
    */
    renderPainel();
    await ticketMontado();
    const auto = screen.getByRole('switch', { name: 'Operação automática' });
    await waitFor(() =>
      expect((screen.getByLabelText('Stop loss') as HTMLInputElement).value).toBe('4136.46'),
    );
    expect((screen.getByLabelText('Take profit') as HTMLInputElement).value).toBe('4144.74');
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

  it('o que o operador digitou NAO e sobrescrito pelo padrao', async () => {
    /*
    O padrao so age em campo VAZIO. Um padrao que reescreve o risco escolhido
    pelo dono e o app decidindo dinheiro por ele (AGENTS.md 9).
    */
    renderPainel();
    await ticketMontado();
    fireEvent.change(screen.getByLabelText('Stop loss'), { target: { value: '4130' } });
    fireEvent.change(screen.getByLabelText('Take profit'), { target: { value: '4150' } });
    await waitFor(() => expect(screen.getByText(/1:1 padrão/)).toBeTruthy());
    expect((screen.getByLabelText('Stop loss') as HTMLInputElement).value).toBe('4130');
    expect((screen.getByLabelText('Take profit') as HTMLInputElement).value).toBe('4150');
  });

  it('PROVA NEGATIVA: sem preco ao vivo o AUTO nao manda SL zero', async () => {
    /*
    Sem cotacao nao existe nivel. Mandar `sl_preco: 0` seria recusado pelo motor
    com um motivo generico, e o operador culparia a corretora por um numero que
    o painel inventou.
    */
    estado.preco = null;
    renderPainel();
    await ticketMontado();
    const auto = screen.getByRole('switch', { name: 'Operação automática' });
    fireEvent.click(auto);
    await waitFor(() => expect(screen.getByText(/Preencha SL e TP/)).toBeTruthy());
    expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(false);
    expect(estado.chamadas.some((c) => c.url.includes('/api/auto/start'))).toBe(false);
  });

  it('NAO envia ordem manual', async () => {
    // A ordem manual vive no grafico, em 1 clique. Aqui seria duplicacao.
    const { container } = renderPainel();
    await ticketMontado();
    fireEvent.change(screen.getByLabelText('Stop loss'), { target: { value: '4130' } });
    fireEvent.change(screen.getByLabelText('Take profit'), { target: { value: '4150' } });
    fireEvent.click(container.querySelector('.robo-ticket-enviar') as HTMLButtonElement);
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(true),
    );
    expect(estado.chamadas.some((c) => c.url.includes('/api/trade/order'))).toBe(false);
  });

  it('recusa lote fora da faixa antes do gateway', async () => {
    renderPainel();
    await ticketMontado();
    fireEvent.change(screen.getByLabelText('Quantidade em lote(s)'), { target: { value: '50' } });
    fireEvent.change(screen.getByLabelText('Stop loss'), { target: { value: '4130' } });
    fireEvent.change(screen.getByLabelText('Take profit'), { target: { value: '4150' } });
    fireEvent.click(screen.getByRole('switch', { name: 'Operação automática' }));
    await waitFor(() => expect(screen.getByText(/Volume entre 0.01 e 10/)).toBeTruthy());
    expect(estado.chamadas.some((c) => c.url.includes('/api/auto/start'))).toBe(false);
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

  it('os presets preenchem SL e TP', async () => {
    renderPainel();
    await ticketMontado();
    /*
      O PRESET ESCREVE PRECO, E NAO DISTANCIA (06/10/2026)
      ====================================================
      Este teste afirmava `4.14` e `12.42` — a DISTANCIA. Mudou porque a
      distacia chegava ao motor como se fosse preco: `ligar()` manda
      `sl_preco: slN`, e `MotorAuto` le `sl_preco` como preco
      (`auto_engine.py:152` — `"sl_preco": "stop loss (preco)"` — usado direto
      na linha 757, sem converter).

      Em ouro a 4.140,60, `sl_preco: 4.14` e um stop invalido. O `order_check`
      recusaria, e a tela mostraria "configurado" para uma protecao que nao
      existe. Era o AGENTS.md 5: o sintoma (stop recusado) cairia no MOTOR,
      e o defeito era do painel que produziu o numero.

      Este e o mesmo campo que o teste do AUTO digita como preco (`4130` em ouro
      a `4140,6`). Dois sentidos no mesmo campo — agora ha um so.

      Passo 0,1% de 4.140,60 = 4,1406. Com 1:3: SL = 4.136,46 · TP = 4.153,02.
    */
    fireEvent.click(screen.getByRole('button', { name: '1:3' }));
    await waitFor(() =>
      expect((screen.getByLabelText('Stop loss') as HTMLInputElement).value).toBe('4136.46'),
    );
    expect((screen.getByLabelText('Take profit') as HTMLInputElement).value).toBe('4153.02');
  });

  it('PROVA NEGATIVA: o preset nao escreve nada sem preco ao vivo', async () => {
    /*
    Sem preco nao existe nivel. Um preset que preenchesse 0 mandaria stop zero ao
    motor, e a recusa do gateway seria com motivo generico — o operador culparia
    a corretora por um numero que o painel inventou (AGENTS.md 9).
    */
    estado.preco = null;
    renderPainel();
    await ticketMontado();
    fireEvent.click(screen.getByRole('button', { name: '1:3' }));
    expect((screen.getByLabelText('Stop loss') as HTMLInputElement).value).toBe('');
    expect((screen.getByLabelText('Take profit') as HTMLInputElement).value).toBe('');
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
