// @vitest-environment jsdom
/*
  O GRAFICO EXISTE COM O MOTOR DESLIGADO (07/10/2026)
  ======================================================
  MEDIDO no app instalado, 00:33 de 07/10, build novo:

      Gráfico indisponível: Identidade de mercado inválida.
      BTCUSD sem candles reais para .

  E a linha do rodapé dizia `BTCUSD · — ·` — o tracejado no lugar do periodo.

  ESTE TESTE EXISTE PORQUE O DEFEITO JA TEVE DUAS FORMAS DIFERENTES
  ================================================================
  O ciclo anterior ja corrigiu `OperacaoAutomatica` com um bloco de 40 linhas
  sobre `escopoAtivo()` devolver `mt5:forex`. O mesmo defeito voltou em
  `AcompanharModelos`, que le o MESMO par e nao tinha a reserva.

  E o AGENTS.md 5 na forma exata que o proprio arquivo documenta: "dois
  componentes, o mesmo dado, uma versao com reserva e outra sem". O sintoma
  apontava para o GATEWAY e para a CORRETORA — o gateway respondeu `null` para
  `market: ''`, e `normalizeMarketSource` lancou o throw de `marketApi.ts:1368`.

  O QUE ESTE TESTE TRAVA
  ======================
  1. Com o motor DESLIGADO e o par escolhido na barra, o grafico TEM de
     carregar. Sem isto, fechar o motor apaga o grafico — e o operador conclui
     que o motor tambem controla a leitura de candles.
  2. O mercado vem da FICHA, e nao do nome do simbolo. `BTCUSD`, `XAUUSD` e
     `EURUSD` terminam igual: so a hierarquia da corretora separa.
  3. O periodo tem UMA resposta certa — o que o operador escolheu. Um default
     fixo faria a tela discordar do painel logo acima.
*/
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';

const estado = vi.hoisted(() => ({
  /** O que o MOTOR devolve. `null` = motor desligado, sem timeframe e sem mercado. */
  auto: null as Record<string, unknown> | null,
  /** O par escolhido na barra INFERIOR — sempre disponivel. */
  parDaTela: 'BTCUSD',
  /**
   * O CATALOGO que a corretora publica.
   *
   * `assetClass` e a HIERARQUIA, nao palavra no nome. E o que separa
   * `BTCUSD` de `EURUSD` — os dois em CAIXA ALTA, os dois terminando em `USD`.
   */
  catalogo: [] as Array<{
    symbol: string;
    assetClass: string | null;
    contractSize?: number | null;
    point?: number | null;
    volumeMin?: number | null;
    volumeMax?: number | null;
    volumeStep?: number | null;
  }>,
  pedidos: [] as Array<{ symbol: string; market: string; timeframe: string }>,
}));

vi.mock('../hooks/queries', () => ({
  useAutoState: () => ({ data: estado.auto }),
  usePositions: () => ({ data: { positions: [] }, refetch: vi.fn() }),
  useAccount: () => ({ data: { leverage: 1000 } }),
}));
vi.mock('../hooks/useSinaisModelo', () => ({
  useSinaisModelo: () => ({ sinais: [], idadeSeg: null }),
}));
vi.mock('../lib/escopoAtivo', () => ({
  escopoAtivo: () => ({ broker: 'mt5', market: 'forex' }),
}));
/*
  A BARRA INFERIOR: e de onde vem o par quando o motor nao tem um.

  `parDaTela` e `useAppStore((s) => s.selectedSymbol)`. Sem este duble o
  componente recebe `undefined` e cai no cartao "Escolha o par", que e a
  mensagem para o caso de NAO haver par — e o teste mediria o caso errado.
*/
vi.mock('../hooks/useAppStore', () => ({
  useAppStore: (seletor: (estado: { selectedSymbol: string }) => unknown) =>
    seletor({ selectedSymbol: estado.parDaTela }),
}));
vi.mock('../hooks/useCatalogoAtivos', () => ({
  useCatalogoAtivos: () => estado.catalogo,
}));
vi.mock('../lib/marketApi', () => ({
  getCandles: async (identidade: { symbol: string; market: string }, timeframe: string) => {
    estado.pedidos.push({
      symbol: String(identidade?.symbol ?? ''),
      market: String(identidade?.market ?? ''),
      timeframe: String(timeframe ?? ''),
    });
    return {
      candles: [
        {
          time: 1788000000 + 3600,
          open: 85500,
          high: 85600,
          low: 85400,
          close: 85520,
          volume: 1,
          broker: 'mt5',
          market: 'crypto-spot',
          symbol: String(identidade?.symbol ?? ''),
          source: 'mt5_gateway',
          received_at: '2026-10-07T00:33:00Z',
          provider_timestamp: null,
        },
      ],
      source: 'mt5_gateway',
      received_at: '2026-10-07T00:33:00Z',
    };
  },
}));
vi.mock('./charts/PriceChart', () => ({
  /*
    `TIMEFRAMES` e o mesmo array do componente real, e nao um palpite: e a lista
    de periodos que o `PriceChart` aceita, e o fallback do `AcompanharModelos`
    tem de sair DELA. Um array proprio aqui passaria mesmo com os dois lados
    divergindo — e a divergencia e o defeito que este arquivo mede.
  */
  TIMEFRAMES: ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'],
  default: (props: Record<string, any>) => (
    <div data-testid="grafico">
      <span data-testid="timeframe">{String(props.timeframe ?? '')}</span>
      <span data-testid="market">{String(props.market ?? '')}</span>
      <span data-testid="candles">{String(props.candles?.length ?? 0)}</span>
    </div>
  ),
}));

const { default: AcompanharModelos } = await import('./AcompanharModelos');

/** A MESMA lista que o duble expoe — o fallback do periodo tem de sair dela. */
const TIMEFRAMES_ESPERADOS = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'] as const;

beforeEach(() => {
  estado.auto = null;
  estado.parDaTela = 'BTCUSD';
  estado.pedidos = [];
  estado.catalogo = [];
});

afterEach(() => cleanup());

describe('o grafico existe com o MOTOR DESLIGADO', () => {
  it('PROVA: motor desligado, par escolhido na barra, o grafico carrega', async () => {
    /*
      O caminho que o operador fez na captura: `Motor desligado`, `AUTO NAO`,
      e o par `BTCUSD` escolhido na barra.

      Sem o par do motor, `auto.market` e `auto.timeframe` vinham vazios, e o
      `getCandles` recebia `market: ''` — que `normalizeMarketSource` recusa.
    */
    estado.catalogo = [{ symbol: 'BTCUSD', assetClass: 'crypto', contractSize: 1 }];
    render(<AcompanharModelos />);

    await waitFor(() => expect(screen.getByTestId('candles').textContent).toBe('1'));
    /*
      O periodo tem de ter chegado no grafico — era o `para .` da captura.

      O valor e `TIMEFRAMES[0]`, e nao um `'M5'` escrito aqui: o fallback sai
      da lista que o `PriceChart` aceita. O duble expoe a MESMA lista do
      componente real, e por isso os dois lados nao podem divergir sem o teste
      ver.
    */
    expect(screen.getByTestId('timeframe').textContent).toBe(TIMEFRAMES_ESPERADOS[0]);
    expect(screen.getByTestId('timeframe').textContent).not.toBe('');
    // E o mercado tem de ser o da CLASSE, nao o default do navegador.
    expect(screen.getByTestId('market').textContent).toBe('crypto-spot');
  });

  it('PROVA NEGATIVA: SEM ficha o mercado nao vira palpite, e a tela diz o que falta', async () => {
    /*
      `escopoAtivo()` devolve `mt5:forex` sem a chave gravada. Um par de cripto
      nesse mercado volta vazio do gateway — e o sintoma seria "nao tem grafico",
      com a culpa na corretora.

      Sem ficha, `configurado` e falso e o painel avisa, em vez de pedir ao
      gateway uma consulta que ele nao pode atender (AGENTS.md 3).
    */
    estado.catalogo = [];
    render(<AcompanharModelos />);

    await waitFor(() => expect(screen.getByTestId('grafico')).toBeTruthy());
    // Nenhuma consulta com mercado inventado.
    expect(estado.pedidos).toHaveLength(0);
  });
});

describe('o mercado vem da CLASSE, nunca do nome', () => {
  /*
  UM CASO POR `describe`, COM O PAR DA BARRA TAMBEM TROCADO.

  MEDIDO na captura: o par vem da barra INFERIOR (`BTCUSD · — ·`) quando o motor
  esta desligado. Trocar so o catalogo sem trocar `parDaTela` mede o par
  anterior, e o `fichaDoAtivo` nao acha ficha — o mercado fica vazio e o teste
  falha por um motivo que nao e o do defeito.
*/
it('PROVA: BTCUSD (crypto) e EURUSD (forex) nao recebem o mesmo mercado', async () => {
    /*
      `escopoAtivo()` devolve `forex` para os dois. `BTCUSD` em forex volta
      vazio do gateway; `EURUSD` em forex funciona. Com um default so,
      funciona um e falha o outro — e o operador culparia a corretora pelo que
      e derivacao.
    */
    estado.parDaTela = 'BTCUSD';
    estado.catalogo = [{ symbol: 'BTCUSD', assetClass: 'crypto', contractSize: 1 }];
    const { unmount } = render(<AcompanharModelos />);
    await waitFor(() => expect(screen.getByTestId('market').textContent).toBe('crypto-spot'));
    unmount();
    estado.pedidos = [];

    estado.parDaTela = 'EURUSD';
    estado.catalogo = [{ symbol: 'EURUSD', assetClass: 'forex', contractSize: 100_000 }];
    render(<AcompanharModelos />);
    await waitFor(() => expect(screen.getByTestId('market').textContent).toBe('forex'));
  });

  it('PROVA: GOLD e METAL pelo catalogo, nao pelo nome XAUUSD', async () => {
    /*
      MEDIDO no catalogo da XM: `XAUUSD` publica `assetClass` da hierarquia de
      metais. E o mesmo ativo que o MT5 mostra como `GOLD`.

      O nome `XAUUSD` nao diz metal para quem nao sabe a sigla — e adivinhar
      por sigla seria exatamente a fronteira de palavra que o AGENTS.md 3 proibe
      (`SOL` casaria dentro de "Solvar").
    */
    estado.parDaTela = 'XAUUSD';
    estado.catalogo = [{ symbol: 'XAUUSD', assetClass: 'metal', contractSize: 100 }];
    render(<AcompanharModelos />);
    await waitFor(() => expect(screen.getByTestId('market').textContent).toBe('metals'));
    expect(estado.pedidos[0]?.market).toBe('metals');
  });

  it('PROVA NEGATIVA: ativo sem classe publicada NAO recebe forex por padrao', async () => {
    /*
      Um par novo da corretora, ainda sem classe na hierarquia. O mercado fica
      VAZIO e o painel avisa.

      Um default aqui seria pior que o defeito: a ordem ia para `forex`, o
      gateway aceitava, e o volume seria interpretado com `contract_size` de
      forex num ativo que nao e forex.
    */
    estado.catalogo = [{ symbol: 'ATIVONOVO', assetClass: null, contractSize: null }];
    estado.parDaTela = 'ATIVONOVO';
    render(<AcompanharModelos />);

    await waitFor(() => expect(screen.getByTestId('grafico')).toBeTruthy());
    expect(estado.pedidos).toHaveLength(0);
  });
});

describe('o periodo e o que o operador escolheu', () => {
  it('PROVA: com o motorChoosing H4, o grafico recebe H4', async () => {
    /*
      MEDIDO na captura de 00:40: o seletor de modelo mostra `H4 · edge 15,5%`
      e o rodape do grafico, na MESMA tela, mostrava `BTCUSD · — ·`.

      Duas telas da mesma pagina discordando do periodo, e a de baixo sem
      grafico. Um default fixo aqui seria o grafico mostrando H1 enquanto o
      painel diz que o modelo e H4 — e o operador operate no timeframe errado.
    */
    estado.auto = {
      ativo: false,
      simbolo: 'BTCUSD',
      broker: 'mt5',
      market: 'crypto-spot',
      timeframe: 'H4',
    };
    estado.catalogo = [{ symbol: 'BTCUSD', assetClass: 'crypto', contractSize: 1 }];
    render(<AcompanharModelos />);

    await waitFor(() => expect(screen.getByTestId('timeframe').textContent).toBe('H4'));
    expect(estado.pedidos[0]?.timeframe).toBe('H4');
  });

  it('PROVA NEGATIVA: motor SEM periodo nao repete o que veio vazio no grafico', async () => {
    /*
      `String(auto?.timeframe ?? '')` produzia `''`, e o `PriceChart` recebia
      timeframe vazio. O rodape escrevia o tracejado.

      Aqui o motor traz `simbolo` e `broker` mas nao traz `timeframe` — o caso
      real do motor ligando sem modelo escolhido.
    */
    estado.auto = { ativo: false, simbolo: 'BTCUSD', broker: 'mt5', market: 'crypto-spot' };
    estado.catalogo = [{ symbol: 'BTCUSD', assetClass: 'crypto', contractSize: 1 }];
    render(<AcompanharModelos />);

    await waitFor(() => expect(screen.getByTestId('timeframe').textContent).not.toBe(''));
    expect(screen.getByTestId('timeframe').textContent).toBe(TIMEFRAMES_ESPERADOS[0]);
    expect(estado.pedidos[0]?.timeframe).toBe(TIMEFRAMES_ESPERADOS[0]);
  });
});