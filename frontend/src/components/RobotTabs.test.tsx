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

// Os três blocos externos são mockados: este arquivo testa a ESTRUTURA da
// página e o TICKET. Gráfico e terminal têm arquivos próprios.
vi.mock('./UniversalLiveTerminal', () => ({ default: () => <div data-testid="painel-mini" /> }));
vi.mock('./AcompanharModelos', () => ({ default: () => <div data-testid="painel-grafico" /> }));
vi.mock('./SeletorModelo', () => ({ default: () => <div data-testid="painel-par" /> }));

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
  window.localStorage.setItem('xau-active-account', 'mt5:metals');
  vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
    const body = JSON.parse(String(init?.body ?? '{}'));
    estado.chamadas.push({ url: String(url), body });
    if (String(url).includes('/api/universal/quotes')) {
      return { ok: true, json: async () => ({ quotes: [{ price: 4140.6 }] }) };
    }
    return { ok: true, json: async () => ({ ok: true }) };
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('RobotTabs — a ordem que o dono pediu', () => {
  it('cabecalho, comandos, escolha do par, grafico e miniterminal, nessa ordem', () => {
    const { container } = render(<RobotTabs />);
    const filhos = Array.from(container.querySelectorAll('.robo > *'));
    // O primeiro e o cabecalho. Os outros quatro sao os blocos, cada um dentro
    // da sua barreira de erro.
    //
    // O `aria-label` vem do `section` que CADA bloco declara. Os blocos
    // mockados nao tem `aria-label` proprio, entao o teste confere a POSICAO
    // deles, e nao o nome — e a ordem que importa aqui.
    expect(filhos).toHaveLength(5);
    expect(filhos[0].tagName).toBe('HEADER');
    expect(filhos[1].getAttribute('aria-label')).toBe('Operação automática');
    expect(filhos[2].getAttribute('data-testid')).toBe('painel-par');
    expect(filhos[3].getAttribute('data-testid')).toBe('painel-grafico');
    expect(filhos[4].getAttribute('data-testid')).toBe('painel-mini');
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
  it('AUTO NAO aplica lote/sl/tp e liga o motor', async () => {
    renderPainel();
    await ticketMontado();
    const auto = screen.getByRole('switch', { name: 'Operação automática' });
    fireEvent.click(auto);
    await waitFor(() => expect(screen.getByText(/Preencha SL e TP/)).toBeTruthy());
    fireEvent.change(screen.getByLabelText('Quantidade em lotes'), { target: { value: '0.01' } });
    fireEvent.change(screen.getByLabelText('Stop loss'), { target: { value: '4130' } });
    fireEvent.change(screen.getByLabelText('Take profit'), { target: { value: '4150' } });
    fireEvent.click(auto);
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/config'))).toBe(true),
    );
    await waitFor(() =>
      expect(estado.chamadas.some((c) => c.url.includes('/api/auto/start'))).toBe(true),
    );
    const cfg = estado.chamadas.find((c) => c.url.includes('/api/auto/config'))!;
    expect(cfg.body.lote).toBe(0.01);
    expect(cfg.body.sl_preco).toBe(4130);
    expect(cfg.body.simbolo).toBe('GOLD');
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
    fireEvent.change(screen.getByLabelText('Quantidade em lotes'), { target: { value: '50' } });
    fireEvent.change(screen.getByLabelText('Stop loss'), { target: { value: '4130' } });
    fireEvent.change(screen.getByLabelText('Take profit'), { target: { value: '4150' } });
    fireEvent.click(screen.getByRole('switch', { name: 'Operação automática' }));
    await waitFor(() => expect(screen.getByText(/Lote entre 0.01 e 10/)).toBeTruthy());
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
    // Passo com escala do ativo: 0,1% de 4140,6 = 4,14. O preset 1:3 da
    // SL 4,14 e TP 12,42.
    fireEvent.click(screen.getByRole('button', { name: '1:3' }));
    await waitFor(() =>
      expect((screen.getByLabelText('Stop loss') as HTMLInputElement).value).toBe('4.14'),
    );
    expect((screen.getByLabelText('Take profit') as HTMLInputElement).value).toBe('12.42');
  });
});