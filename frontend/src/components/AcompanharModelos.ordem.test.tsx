// @vitest-environment jsdom
// O PAINEL DA ORDEM ARMADA E O ENVIO (06/10/2026)
// ================================================
// MEDIDO nas capturas da XM: o clique ARMA, o painel mostra tudo, e o botao
// `Colocar ordem a 85.510,25` ENVIA. Este arquivo cobre o painel e o envio; o
// grafico (as tres linhas, o `x` e o arraste) tem o seu proprio.
//
// O QUE ESTES TESTES TRAVAM
// =========================
// 1. O CLIQUE NO GRAFICO NAO MANDA ORDEM. Sem isso o caminho removido a pedido
//    do dono ("remover botao 1 clique") volta por outra porta, e volta melhor:
//    com o preco que o operador nao escolheu.
// 2. `confirm: true` e `request_id` em TODA escrita. Medido em
//    `backend/mt5_gateway.py:2177` — `confirm` ausente e recusa do gateway, e o
//    `request_id` e a idempotencia que impede a mesma ordem em dois envios.
// 3. O painel RECUSA COM MOTIVO NOMEADO. A rota exige `sl > 0` e `tp > 0`
//    (linha 2190) e devolve "symbol, side, volume <= 0.10, sl e tp validos sao
//    obrigatorios" — que nao diz qual dos cinco faltou (AGENTS.md 5).
// 4. SEM `contract_size` NAO HA NIVEL. `nivelDoValor` devolve `null` e o painel
//    diz isso, em vez de estimar um nivel 100.000 vezes errado em forex.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const estado = vi.hoisted(() => ({
  auto: { ativo: false, simbolo: 'BTCUSD', broker: 'mt5', market: 'crypto-spot', timeframe: 'M5' },
  sinais: [] as Array<{ time: number; signal: string; confidence?: number }>,
  posicoes: [] as Array<Record<string, unknown>>,
  chamadas: [] as Array<{ url: string; body: Record<string, unknown> }>,
  /** O que `/api/universal/assets` devolve: e a FICHA do ativo. */
  contrato: 1 as number | null,
  /**
   * A ALAVANCAGEM DA CONTA, como o `/api/account` devolve.
   *
   * MEDIDO na conta 391773676 (XMGlobal-MT5 14): o painel `Gerir` da XM escreve
   * `Alavancagem 1000:1`, e `account_info().leverage` devolve `1000`.
   *
   * `null` por padrao, e nao 1000: um duble que devolve o valor certo por
   * padrao esconde o caminho de `leverage` ausente — que e o caso em que o
   * painel tem de dizer "indisponivel" em vez de escrever `$0,85`. Os testes
   * que precisam do numero dizem `estado.alavancagem = 1000`.
   */
  alavancagem: null as number | null,
}));

vi.mock('../hooks/queries', () => ({
  useAutoState: () => ({ data: estado.auto }),
  usePositions: () => ({ data: { positions: estado.posicoes }, refetch: vi.fn() }),
  useAccount: () => ({ data: { leverage: estado.alavancagem } }),
}));

vi.mock('../hooks/useSinaisModelo', () => ({
  useSinaisModelo: () => ({ sinais: estado.sinais, idadeSeg: null }),
}));

vi.mock('./charts/PriceChart', () => ({
  default: (props: Record<string, any>) => (
    <div data-testid="grafico">
      <span data-testid="modo-ordem">{String(Boolean(props.modoOrdem))}</span>
      <span data-testid="linhas">{JSON.stringify(props.ordem ?? [])}</span>
      <button type="button" onClick={() => props.onArmarOrdem?.(85510.25)}>
        simular clique no grafico
      </button>
      <button type="button" onClick={() => props.onRemoverLinha?.('sl')}>
        simular x no stop
      </button>
    </div>
  ),
}));

const { default: AcompanharModelos } = await import('./AcompanharModelos');

function renderPainel() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <AcompanharModelos />
    </QueryClientProvider>,
  );
}

/** O clique no grafico: o operador escolhe o preco. */
const clicarNoGrafico = async () => {
  fireEvent.click(screen.getByText('simular clique no grafico'));
  await waitFor(() => expect(screen.getByText(/Colocar ordem a/)).toBeTruthy());
};

/**
 * O clique, e DEPOIS a ficha.
 *
 * O painel aparece assim que o clique arma, mas o nivel em dinheiro so existe
 * depois que `/api/universal/assets` devolve o `contract_size` — ate la o botao
 * esta desabilitado, com o motivo nomeado. E o comportamento certo: sem
 * contrato nao ha preco (AGENTS.md 3). Um teste que clicasse e mandasse nao
 * estaria medindo a tela, estaria medindo a corrida entre dois fetches.
 */
const clicarComFicha = async () => {
  await clicarNoGrafico();
  await waitFor(() => {
    const linhas = JSON.parse(screen.getByTestId('linhas').textContent ?? '[]');
    expect(linhas).toHaveLength(3);
  });
};

/** As linhas que o grafico recebeu. */
const linhasDoGrafico = () =>
  JSON.parse(screen.getByTestId('linhas').textContent ?? '[]') as Array<{
    papel: string;
    preco: number;
    rotulo: string;
    cor: string;
  }>;

/** O que foi para `/api/trade/order`, se algo foi. */
const envio = () => estado.chamadas.find((c) => c.url.includes('/api/trade/order'));

const FICHA = {
  symbol: 'BTCUSD',
  display_name: 'Bitcoin',
  availability: 'available',
  restrictions: [],
  digits: 2,
  point: 0.01,
  volume_min: 0.01,
  volume_max: 10,
  volume_step: 0.01,
  contract_size: 1,
  asset_class: 'crypto',
};

beforeEach(() => {
  estado.auto = {
    ativo: false,
    simbolo: 'BTCUSD',
    broker: 'mt5',
    market: 'crypto-spot',
    timeframe: 'M5',
  };
  estado.sinais = [];
  estado.posicoes = [];
  estado.chamadas = [];
  estado.contrato = 1;
  // `null` por padrao: o requisito de margem tem de aparecer como
  // INDISPONIVEL quando a alavancagem nao veio. Os testes que medem o numero
  // ligam `estado.alavancagem = 1000` explicitamente.
  estado.alavancagem = null;
  vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
    const bruto = String(init?.body ?? '{}');
    let body: Record<string, unknown> = {};
    try {
      body = JSON.parse(bruto);
    } catch {
      /* GET sem corpo */
    }
    if (String(init?.method ?? 'GET') === 'POST')
      estado.chamadas.push({ url: String(url), body });
    if (String(url).includes('/api/universal/assets'))
      return {
        ok: true,
        json: async () => ({
          broker: 'mt5',
          market: 'crypto-spot',
          source: 'mt5_gateway',
          received_at: '2026-10-06T14:12:39Z',
          provider_timestamp: null,
          assets: [{ ...FICHA, contract_size: estado.contrato }],
          errors: [],
        }),
      };
    return { ok: true, json: async () => ({ ok: true, candles: [], positions: [] }) };
  });
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe('o grafico esta em MODO DE ORDEM', () => {
  it('o componente recebe modoOrdem ligado', async () => {
    renderPainel();
    // `textContent`, e nao `toHaveTextContent`: este projeto nao carrega o
    // jest-dom, e o matcher seria "Invalid Chai property" — o mesmo erro em
    // todo teste, sem medir nada.
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
  });
});

describe('o clique ARMA e NAO ENVIA', () => {
  it('nada vai para /api/trade/order ao clicar no grafico', async () => {
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarNoGrafico();
    // ESTE e o teste que importa: se o clique mandasse, o caminho de 1-clique
    // que o dono mandou remover estaria vivo de novo.
    expect(envio()).toBeUndefined();
    expect(estado.chamadas.some((c) => c.url.includes('/api/trade/order'))).toBe(false);
  });

  it('o painel so aparece DEPOIS do clique, e mostra o preco clicado', async () => {
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    expect(screen.queryByText(/Colocar ordem a/)).toBeNull();
    await clicarNoGrafico();
    // O preco no BOTAO, que e onde o operador decide enviar (medido na captura).
    expect(screen.getByText('Colocar ordem a 85.510,25')).toBeTruthy();
  });

  it('as tres linhas seguem o preco clicado, com o rotulo em dinheiro', async () => {
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    const linhas = linhasDoGrafico();
    expect(linhas).toHaveLength(3);
    expect(linhas.map((l) => l.papel)).toEqual(['entrada', 'sl', 'tp']);
    // MEDIDO na captura: `0,01 | −2,00 USD` e `0,01 | +2,00 USD`.
    expect(linhas[1].rotulo).toBe('0,01 | −2,00 USD');
    expect(linhas[2].rotulo).toBe('0,01 | +2,00 USD');
  });

  it('as tres linhas ficam em LADOS OPOSTOS em relacao ao clique', async () => {
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    const [entrada, sl, tp] = linhasDoGrafico();
    expect(entrada.preco).toBeCloseTo(85510.25, 2);
    // COMPRA: o stop abaixo (e onde se perde) e o alvo acima. Os dois do mesmo
    // lado colocariam o stop DEPOIS do alvo, e a ordem nao teria protecao.
    expect(sl.preco).toBeLessThan(entrada.preco);
    expect(tp.preco).toBeGreaterThan(entrada.preco);
  });
});

describe('o botao envia com confirm e request_id', () => {
  it('manda symbol, side, volume, sl, tp, confirm e request_id', async () => {
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    fireEvent.click(screen.getByText('Colocar ordem a 85.510,25'));
    await waitFor(() => expect(envio()).toBeTruthy());
    const body = envio()!.body;
    expect(body.symbol).toBe('BTCUSD');
    expect(body.side).toBe('BUY');
    expect(body.confirm).toBe(true);
    expect(typeof body.request_id).toBe('string');
    expect(String(body.request_id).length).toBeGreaterThan(0);
  });

  it('o SL e o TP vaem DERIVADOS do dinheiro, nos lados do lado escolhido', async () => {
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    fireEvent.click(screen.getByText('Colocar ordem a 85.510,25'));
    await waitFor(() => expect(envio()).toBeTruthy());
    const body = envio()!.body;
    /*
      2,00 USD / (0,01 x 1) = 200 pontos. COMPRA: o stop fica ABAIXO (e onde se
      perde) e o alvo ACIMA. Um nivel do lado errado manda ordem sem protecao, e
      a tela nao faria o operador desconfiar do numero — que e o pior defeito
      possivel numa tela de ordem.
    */
    expect(body.sl).toBeCloseTo(85510.25 - 200, 2);
    expect(body.tp).toBeCloseTo(85510.25 + 200, 2);
  });

  it('VENDE inverte os dois lados: stop acima, alvo abaixo', async () => {
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    fireEvent.click(screen.getByText('Vender'));
    await waitFor(() => expect(screen.getByText('Vender').getAttribute('aria-pressed')).toBe('true'));
    fireEvent.click(screen.getByText('Colocar ordem a 85.510,25'));
    await waitFor(() => expect(envio()).toBeTruthy());
    expect(envio()!.body.side).toBe('SELL');
    expect(envio()!.body.sl).toBeCloseTo(85510.25 + 200, 2);
    expect(envio()!.body.tp).toBeCloseTo(85510.25 - 200, 2);
  });

  it('cada envio tem um request_id PROPRIO', async () => {
    /*
    `request_id` e a idempotencia: o mesmo id duas vezes e a MESMA ordem, e o
    gateway devolve a anterior. Dois ids para dois cliques no botao sao duas
    ordens — que e o que o operador mandou ao clicar duas vezes.
    */
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    fireEvent.click(screen.getByText('Colocar ordem a 85.510,25'));
    await waitFor(() => expect(envio()).toBeTruthy());
    await clicarComFicha();
    fireEvent.click(screen.getByText('Colocar ordem a 85.510,25'));
    await waitFor(() => expect(estado.chamadas.length).toBeGreaterThanOrEqual(2));
    const ids = estado.chamadas
      .filter((c) => c.url.includes('/api/trade/order'))
      .map((c) => String(c.body.request_id));
    expect(new Set(ids).size).toBe(ids.length);
  });

  it('a ordem recusada pelo gateway FICA no painel, com o motivo', async () => {
    vi.stubGlobal('fetch', async (url: string, init?: RequestInit) => {
      const m = String(init?.method ?? 'GET');
      if (m === 'POST')
        estado.chamadas.push({ url: String(url), body: JSON.parse(String(init?.body ?? '{}')) });
      if (String(url).includes('/api/universal/assets'))
        return {
          ok: true,
          json: async () => ({
            broker: 'mt5',
            market: 'crypto-spot',
            source: 'mt5_gateway',
            received_at: '2026-10-06T14:12:39Z',
            provider_timestamp: null,
            assets: [{ ...FICHA, contract_size: estado.contrato }],
            errors: [],
          }),
        };
      if (String(url).includes('/api/trade/order'))
        return {
          ok: false,
          status: 403,
          json: async () => ({ ok: false, error: 'confirm=true obrigatorio' }),
        };
      return { ok: true, json: async () => ({ ok: true, candles: [], positions: [] }) };
    });
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    fireEvent.click(screen.getByText('Colocar ordem a 85.510,25'));
    // O motivo da CORRETORA aparece. Um painel que fecha em silencio depois de
    // recusado faz o operador achar que a ordem saiu.
    await waitFor(() => expect(screen.getByText('confirm=true obrigatorio')).toBeTruthy());
    // E o painel continua armado: a ordem nao saiu, e o operador precisa ver
    // o que ele escreveu para corrigir.
    expect(screen.getByText(/Colocar ordem a/)).toBeTruthy();
  });
});

describe('o painel RECUSA COM MOTIVO NOMEADO', () => {
  it('sem contract_size: diz que dinheiro nao vira preco, e nao envia', async () => {
    estado.contrato = null;
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarNoGrafico();
    // A ficha sem `contract_size` e a recusa CORRETA: um default de 1 daria
    // nivel 100.000 vezes errado em forex, e o numero sairia plausivel.
    await waitFor(() => expect(screen.getByText(/tamanho do contrato deste ativo/)).toBeTruthy());
    const botao = screen.getByText(/Colocar ordem a/) as HTMLButtonElement;
    expect(botao.disabled).toBe(true);
  });

  it('PROVA NEGATIVA: sem contract_size so a linha de entrada e desenhada', async () => {
    estado.contrato = null;
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarNoGrafico();
    // Dois nivelestimados em forex seriam 100.000 vezes errados E plausiveis.
    expect(linhasDoGrafico().map((l) => l.papel)).toEqual(['entrada']);
  });

  it('o `x` no stop tira a protecao, AVISA, e o botao continua clicavel', async () => {
    // SL/TP deixou de ser obrigatorio (decisao do dono, 07/10/2026). O que este
    // caso protege nao e mais a recusa: e que o operador VEJA que a ordem vai
    // sem stop antes de clicar. O risco e dele — mas ele precisa saber.
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    fireEvent.click(screen.getByText('simular x no stop'));
    // A linha some do grafico...
    expect(linhasDoGrafico().map((l) => l.papel)).toEqual(['entrada', 'tp']);
    // ...e o painel DIZ que vai sem stop, com o aviso escrito.
    await waitFor(() => expect(screen.getByText(/Esta ordem vai/)).toBeTruthy());
    await waitFor(() => expect(screen.getByText(/sem stop/i)).toBeTruthy());
    expect((screen.getByText(/Colocar ordem a/) as HTMLButtonElement).disabled).toBe(false);
  });

  it('PROVA NEGATIVA: sem stop, o botao existe mas o aviso some quando o stop volta', async () => {
    // Sem este caso, um painel que mostrasse o aviso sempre passaria.
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    fireEvent.click(screen.getByText('simular x no stop'));
    await waitFor(() => expect(screen.getByText(/Esta ordem vai/)).toBeTruthy());
    // Repoe o stop: o aviso tem de sumir.
    fireEvent.change(screen.getByLabelText(/Quanto aceita perder/i), { target: { value: '2' } });
    await waitFor(() => expect(screen.queryByText(/Esta ordem vai/)).toBeNull());
  });

  it('PROVA NEGATIVA: o `x` no alvo tira o alvo, pelo mesmo caminho', async () => {
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    fireEvent.click(screen.getByText('Vender'));
    fireEvent.change(screen.getByLabelText(/Quanto espera ganhar/i), { target: { value: '0' } });
    expect(linhasDoGrafico().map((l) => l.papel)).toEqual(['entrada', 'sl']);
    await waitFor(() => expect(screen.getByText(/sem alvo/i)).toBeTruthy());
  });

  it('PROVA NEGATIVA: o botao "sem SL/TP" existe e zera os dois campos', async () => {
    // O botao explicito que o dono pediu: quem QUER mandar sem clica nele, em
    // vez de esvaziar os campos na mao e ficar na duvida se errou.
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    const botao = screen.getByRole('button', { name: /Enviar sem SL\/TP|Sem SL\/TP/ });
    fireEvent.click(botao);
    await waitFor(() => expect(screen.getByText(/Esta ordem vai/)).toBeTruthy());
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Sem SL\/TP/ }).getAttribute('aria-pressed')).toBe(
        'true',
      ),
    );
  });

  it('PROVA NEGATIVA: sem sl/tp, o corpo NAO leva sl: 0 nem tp: 0', async () => {
    // `sl: 0` e um NUMERO, e nao uma ausencia. Mandar zero e pedir uma
    // protecao de preco zero, que o motor leria como nivel invalido. O campo
    // ausente e o que significa "sem protecao".
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    fireEvent.click(screen.getByRole('button', { name: /Enviar sem SL\/TP|Sem SL\/TP/ }));
    await waitFor(() => expect(screen.getByText(/Esta ordem vai/)).toBeTruthy());
    fireEvent.click(screen.getByText(/Colocar ordem a/));
    await waitFor(() => expect(estado.chamadas.some((c) => c.body)).toBe(true));
    const envio = estado.chamadas.find((c) => c.body && String(c.url).includes('/api/trade/order'));
    expect(envio).toBeTruthy();
    const corpo = envio!.body;
    expect(corpo.sl).toBeUndefined();
    expect(corpo.tp).toBeUndefined();
    // E o que continua obrigatorio, presente:
    expect(corpo.symbol).toBeTruthy();
    expect(corpo.side).toBeTruthy();
    expect(corpo.confirm).toBe(true);
    expect(corpo.request_id).toBeTruthy();
  });

  it('PROVA NEGATIVA: com stop e alvo preenchidos, o corpo LEVA os dois', async () => {
    // O caminho oposto: preenchido tem de ir no corpo. Sem este, uma correcao
    // que so apagasse os campos passaria.
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    fireEvent.change(screen.getByLabelText(/Quanto aceita perder/i), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText(/Quanto espera ganhar/i), { target: { value: '4' } });
    fireEvent.click(screen.getByText(/Colocar ordem a/));
    await waitFor(() => expect(estado.chamadas.some((c) => c.body)).toBe(true));
    const envio = estado.chamadas.find((c) => c.body && String(c.url).includes('/api/trade/order'));
    const corpo = envio!.body;
    expect(Number(corpo.sl)).toBeGreaterThan(0);
    expect(Number(corpo.tp)).toBeGreaterThan(0);
  });

  it('PROVA NEGATIVA: quantidade zero desliga o botao e nomeia o campo', async () => {
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarComFicha();
    fireEvent.change(screen.getByLabelText(/Quantidade em/i), { target: { value: '0' } });
    await waitFor(() => expect(screen.getByText('Informe a quantidade.')).toBeTruthy());
    expect((screen.getByText(/Colocar ordem a/) as HTMLButtonElement).disabled).toBe(true);
  });

  it('PROVA NEGATIVA: acima de 0,10 o motivo diz o limite, nao "invalido"', async () => {
    /*
    Medido em `backend/mt5_gateway.py:2190`: `volume <= 0.10`. O painel repete o
    limite medido, para o operador corrigir o campo em vez de procurar defeito na
    corretora (AGENTS.md 5).
    */
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarNoGrafico();
    fireEvent.change(screen.getByLabelText(/Quantidade em/i), { target: { value: '0.5' } });
    await waitFor(() => expect(screen.getByText(/acima do máximo aceito: 0,10/)).toBeTruthy());
    expect((screen.getByText(/Colocar ordem a/) as HTMLButtonElement).disabled).toBe(true);
  });

  it('PROVA NEGATIVA: o botao desabilitado nao envia, mesmo com o clique forcado', async () => {
    estado.contrato = null;
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarNoGrafico();
    fireEvent.click(screen.getByText(/Colocar ordem a/));
    expect(envio()).toBeUndefined();
  });

  it('o painel aceita DESCARTER sem enviar', async () => {
    estado.contrato = null;
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarNoGrafico();
    fireEvent.click(screen.getByText('Descartar'));
    await waitFor(() => expect(screen.queryByText(/Colocar ordem a/)).toBeNull());
    expect(envio()).toBeUndefined();
  });
});

/*
  O REQUISITO DE MARGEM (06/10/2026)
  ===================================
  MEDIDO na captura da XM (20:43): `Quantidade 0,01 lotes` ·
  `Requisito de margem $0.85` · barra em `8,01%`.

  Este bloco entra no painel depois do ciclo que o RECUSOU. O motivo da recusa
  era certo — nao se escreve estimativa num painel onde o numero vira limite — e
  a conclusao estava errada: a alavancagem NAO e um numero que o app nao tem de
  onde ler. MEDIDO no painel `Gerir` da XM: `Alavancagem 1000:1`. MEDIDO em
  `account_info().leverage`: `1000`.

  A conta confere, e e isso que autoriza a tela a escrever o numero:
  `0,01 x contract_size 1,0 x 85.510,25 = 855,10` de nocional, e
  `855,10 / 1000 = 0,855`. A XM escreve `$0.85`.
*/
describe('o requisito de margem bate com a conta', () => {
  it('PROVA: com alavancagem da conta, o painel escreve 0.85 e o nocional', async () => {
    estado.alavancagem = 1000;
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarNoGrafico();

    await waitFor(() => expect(screen.getByText(/Requisito de margem/i)).toBeTruthy());
    // 0,01 x 1,0 x 85.510,25 = 855,1025 → 855,10. E 855,1025 / 1000 = 0,8551.
    expect(screen.getByText('0.86 USD')).toBeTruthy();
    expect(screen.getByText(/nocional 855,10 USD/)).toBeTruthy();
    // A alavancagem aparece: e ela que explica o numero.
    expect(screen.getByText(/alavancagem 1000:1/)).toBeTruthy();
  });

  it('PROVA NEGATIVA: sem alavancagem, o painel DIZ QUE FALTA — e nao escreve 0,00', async () => {
    /*
      O defeito que este caso impede: `$0,00` de requisito lido como "de graça".
      E o pior tipo de numero errado, porque o operador age em cima dele.

      E `$0,00` nao viria de um bug de formatacao: viria de dividir por um
      padrao quando a alavancagem nao chegou. Com `1000` de padrao o numero
      estaria CERTO nesta conta — e o operador nunca saberia que era chute.
    */
    estado.alavancagem = null;
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarNoGrafico();

    await waitFor(() => expect(screen.getByText(/indisponível/i)).toBeTruthy());
    expect(screen.getByText(/alavancagem da conta/i)).toBeTruthy();
    // O painel NAO pode escrever um numero de margem.
    expect(screen.queryByText(/0\.00 USD/)).toBeNull();
    // E o botao continua habilitado: requisito de margem e INFORMACAO, nao
    // trava. A XM deixa enviar com o numero na barra.
    expect((screen.getByText(/Colocar ordem a/) as HTMLButtonElement).disabled).toBe(false);
  });

  it('PROVA NEGATIVA: sem contract_size o requisito nao vira chute em forex', async () => {
    /*
      MEDIDO: BTCUSD tem `contract_size = 1` e EURUSD tem `100.000`. Com um
      padrao de 1 no lugar do contrato, o mesmo `0,01` a 85.510,25 daria `$0,86`
      no BTCUSD — e `$85.510,25` no EURUSD.

      O primeiro e o numero certo do BTCUSD POR COINCIDENCIA. E a coincidencia
      que torna o defeito perigoso: o operador confia no BTCUSD, troca para
      forex, e so descobre depois de abrir a ordem.
    */
    estado.alavancagem = 1000;
    estado.contrato = null;
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarNoGrafico();

    await waitFor(() => expect(screen.getByText(/indisponível/i)).toBeTruthy());
    // `/tamanho do contrato/i` casaria TAMBEM com a recusa do botao ("A corretora
    // nao devolveu o tamanho do contrato deste ativo"), e `getByText` reprovaria
    // com "encontrados varios". O motivo do requisito mora dentro do bloco dele.
    expect(screen.getByText(/Requisito de margem indisponível/)).toBeTruthy();
    expect(screen.queryByText(/0\.86 USD/)).toBeNull();
  });

  it('a quantidade muda o requisito em linha reta', async () => {
    estado.alavancagem = 1000;
    renderPainel();
    await waitFor(() => expect(screen.getByTestId('modo-ordem').textContent).toBe('true'));
    await clicarNoGrafico();
    await waitFor(() => expect(screen.getByText('0.86 USD')).toBeTruthy());

    // 0,02 é o dobro de 0,01: 0,02 x 1,0 x 85.510,25 = 1.710,205, e
    // 1.710,205 / 1000 = 1,71.
    fireEvent.change(screen.getByLabelText(/Quantidade em/i), { target: { value: '0.02' } });
    await waitFor(() => expect(screen.getByText('1.71 USD')).toBeTruthy());
    expect(screen.getByText(/nocional 1.710,21 USD/)).toBeTruthy();
  });
});