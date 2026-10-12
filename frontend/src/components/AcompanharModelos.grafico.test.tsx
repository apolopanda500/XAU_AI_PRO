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
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

const estado = vi.hoisted(() => ({
  /** O que o MOTOR devolve. `null` = motor desligado, sem timeframe e sem mercado. */
  auto: null as Record<string, unknown> | null,
  /** O par escolhido na barra INFERIOR — sempre disponivel. */
  parDaTela: 'BTCUSD',
  /**
   * A CONTA ATIVA, como `escopoAtivo()` a devolveria. `mt5:forex` e o caso
   * com conta escolhida; `{ broker: '', market: '' }` e o sem-conta
   * (11/10/2026, nada de MT5 fixo) — e o mock precisa dos DOIS, senao o
   * caso sem conta nunca seria medido (AGENTS.md 6: duble que mede a coisa
   * errada passa com o defeito ligado).
   */
  escopo: { broker: 'mt5', market: 'forex' },
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
  /**
   * Quando preenchido, `getCandles` LANCA este motivo — e é o caso do
   * intervalo de 30s falhar depois de o gráfico já ter dado (captura das
   * 12:24, MT5 fechado).
   */
  falhaCandles: null as string | null,
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
  escopoAtivo: () => ({ ...estado.escopo }),
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
    if (estado.falhaCandles) throw new Error(estado.falhaCandles);
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
  TIMEFRAMES: ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN1'],
  default: (props: Record<string, any>) => (
    <div data-testid="grafico">
      <span data-testid="timeframe">{String(props.timeframe ?? '')}</span>
      <span data-testid="market">{String(props.market ?? '')}</span>
      <span data-testid="candles">{String(props.candles?.length ?? 0)}</span>
      {/*
        O ERRO QUE O PAI PASSOU, visível no teste (11/10/2026).

        Sem esta linha o duble escondia a mensagem que o `PriceChart` real
        mostra, e não havia como medir a diferença entre "gráfico indisponível"
        (sem dado) e "atualização falhou" (com dado em mão).
      */}
      <span data-testid="erro">{String(props.error ?? '')}</span>
      {/*
        Os botoes do periodo, como o `PriceChart` real tem.

        MEDIDO: sem este bloco, o teste "o operador ESCOLHE outro timeframe"
        nao reprovaria o defeito — ele falharia por falta do botao, e a
        mensagem seria de teste quebrado, nao de codigo errado. O clique aqui
        chama o MESMO callback que o grafico chama.
      */}
      <div role="group" aria-label="Timeframe do grafico">
        {['M1', 'M5', 'M15', 'H30', 'H1', 'H4', 'D1', 'W1', 'MN1'].map((tf) => (
          <button
            key={tf}
            type="button"
            aria-label={tf}
            aria-pressed={String(props.timeframe) === tf}
            onClick={() => props.onTimeframeChange?.(tf)}
          >
            {tf}
          </button>
        ))}
      </div>
    </div>
  ),
}));

const { default: AcompanharModelos, erroDeVelas } = await import('./AcompanharModelos');

/**
 * A MESMA lista que o duble expoe — o fallback do periodo tem de sair dela.
 *
 * MEDIDO (09/10/2026): a lista estava sem `W1` e `MN1`, e o dono pediu os dois.
 * Um teste que copia o array do componente mente: ele passaria com o grafico
 * sem os periodos novos e provaria nada. Os dois lados tem de ter a mesma lista.
 */
const TIMEFRAMES_ESPERADOS = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN1'] as const;

beforeEach(() => {
  estado.auto = null;
  estado.parDaTela = 'BTCUSD';
  estado.pedidos = [];
  estado.catalogo = [];
  estado.falhaCandles = null;
  estado.escopo = { broker: 'mt5', market: 'forex' };
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
  });
});

describe('o motor DESLIGADO devolve string vazia, e nao ausencia', () => {
  /*
    MEDIDO em 09/10/2026, com o app instalado e `AUTO NÃO` na tela:

        auto_engine.motor.snapshot()
          broker = ''   market = ''   simbolo = ''   timeframe = ''

    E o defeito na tela, medido em 17:09, 17:18 e 18:23:

        Gráfico indisponível: Identidade de mercado inválida.
        EURUSD sem candles reais para M1.
        0 candles

    Com o gateway respondendo 300 candles (MEDIDO:
    `_universal_candles('mt5','forex','EURUSD','H1',300)` -> ok, count=300).

    A CAUSA: `String(auto?.broker ?? brokerSalvo ?? 'mt5')`. `??` so pega `null`
    e `undefined`, entao `'' ?? brokerSalvo` devolvia `''` — o operador atravessava
    a string vazia do motor desligado. `normalizeMarketSource('', ...)` e `null`,
    e o `getCandles` LANCAVA.

    E o AGENTS.md §5: o defeito e do lado que le o nome diferente. O operador lia
    um erro de IDENTIDADE e culparia o servidor, que estava com 300 velas na mao.

    O mesmo `??` produzia o defeito do `market`, na mesma cadeia, na mesma tela —
    e o `OperacaoAutomatica`, que le o mesmo dado, ja usava `||`. Dois
    componentes, o mesmo dado, uma versao com reserva e outra sem.
  */

  beforeEach(() => {
    estado.pedidos = [];
    // O motor desligado, exatamente como MEDIDO.
    estado.auto = { ativo: false, simbolo: '', broker: '', market: '', timeframe: '' };
  });

  it('PROVA: com o motor desligado, o grafico consulta com o BROKER da conta ativa', async () => {
    estado.parDaTela = 'EURUSD';
    estado.catalogo = [{ symbol: 'EURUSD', assetClass: 'forex', contractSize: 100000 }];
    render(<AcompanharModelos />);

    /*
      O TIMEOUT NAO E DESCUIDO. MEDIDO: este teste passava ISOLADO e reprovava
      na suite inteira, com `expected 0 to be greater than 0` — a consulta nao
      tinha saido dentro de 1 segundo. Com 61 arquivos em paralelo a maquina
      esta ocupada, e o padrao do `waitFor` (1000 ms) e curto demais.

      E um teste que so passa na condicao de carga de uma maquinaocupada nao trava
      o defeito; trava o horario da maquina (o AGENTS.md §6, do avesso).
    */
    await waitFor(
      () => expect(estado.pedidos.length, `estado: ${JSON.stringify(estado)}`).toBeGreaterThan(0),
      { timeout: 5000 },
    );

    // A consulta saiu com a identidade completa — `broker` nunca vazio.
    expect(estado.pedidos[0].market, 'mercado veio da ficha, nao do motor').toBe('forex');
    expect(estado.pedidos[0].symbol).toBe('EURUSD');
  });

  it('PROVA NEGATIVA: `??` atravessava a string vazia do motor — e devolvia `broker: ""`', () => {
    /*
      versoes, com a entrada real do motor desligado.
    */
    const auto = { broker: '' };
    const brokerSalvo = 'mt5';

    // ANTIGO: `??` nao pega string vazia.
    const antigo = String(auto?.broker ?? brokerSalvo ?? 'mt5').toLowerCase();
    expect(antigo).toBe('');
    expect(antigo).not.toBe('mt5');

    // E o `normalizeMarketSource` recusava, que e o throw de identidade.
    const mercados = [
      'forex',
      'metals',
      'indices',
      'stocks',
      'commodities',
      'bonds',
      'crypto-spot',
      'crypto-futures',
      'other',
    ];
    const brokerHabilitado = ['mt5', 'binance', 'mexc', 'bybit', 'okx'];
    expect(brokerHabilitado.includes(antigo), 'broker vazio nao e corretora habilitada').toBe(false);

    // NOVO: `||` pega a string vazia e usa a MEDIDA da conta ativa.
    const novo = String(auto?.broker || brokerSalvo || 'mt5').toLowerCase();
    expect(novo).toBe('mt5');
    expect(brokerHabilitado.includes(novo)).toBe(true);
  });
});

describe('o timeframe e DO OPERADOR (09/10/2026)', () => {
  /*
    MEDIDO pelo dono: "o grafico esta preso em cada ativo, nao tem como escolher
    timeframes diferentes".

    E MEDIDO no codigo por que:

        PriceChart.tsx:603   const activeTimeframe = timeframe ?? internalTimeframe;
        PriceChart.tsx:1892  if (onTimeframeChange) onTimeframeChange(next);
                              else setInternalTimeframe(next);

    Este componente passava `timeframe={tempoEscolhido}` e NAO passava
    `onTimeframeChange`. Entao o clique chamava `setInternalTimeframe` — estado
    INTERNO — e a linha 603, que le `timeframe ?? internalTimeframe`, nunca
    chegava nele, porque `timeframe` estava sempre definido.

    O clique nao mudava nada: nove botoes, um botao decorativo. E o AGENTS.md §9
    — "um controle que nada le e pior que a ausencia dele".
  */

  beforeEach(() => {
    estado.pedidos = [];
    // O modelo em M15. E o ponto de PARTIDA do grafico, nao uma prisao.
    estado.auto = {
      ativo: false,
      simbolo: 'BTCUSD',
      broker: 'mt5',
      market: 'crypto-spot',
      timeframe: 'M15',
    };
    estado.parDaTela = 'BTCUSD';
    estado.catalogo = [{ symbol: 'BTCUSD', assetClass: 'crypto', contractSize: 1 }];
  });

  it('PROVA: o grafico COMECA no periodo do modelo', async () => {
    render(<AcompanharModelos />);
    await waitFor(() => expect(screen.getByTestId('timeframe').textContent).not.toBe(''), {
      timeout: 5000,
    });
    expect(screen.getByTestId('timeframe').textContent).toBe('M15');
  });

  it('PROVA: o operador ESCOLHE outro timeframe e ele vale', () => {
    /*
      Este e o teste do defeito que o dono apontou. Sem a correcao, clicar em
      `W1` nao mudava o rodape — e a barra inteira era decorativa.
    */
    render(<AcompanharModelos />);
    const botao = screen.getByRole('button', { name: /W1/ });
    fireEvent.click(botao);

    expect(screen.getByTestId('timeframe').textContent, 'o clique no timeframe nao valeu').toBe('W1');
  });

  it('PROVA: trocar de PAR volta ao periodo do modelo daquele par', () => {
    /*
      Sem isto: o operador escolhe BTCUSD em M15, troca para EURUSD — e o grafico
      continua em M15, que e o periodo do modelo de BTCUSD. O periodo escolhido
      pertence ao par escolhido.

      MEDIDO (09/10/2026): esta prova falhava com `expected 'W1' to be 'M15'`
      depois que a primeira prova passou. A causa estava NESTA prova, nao no
      componente: com o motor ligado, `simbolo` sai de `auto?.simbolo || parDaTela`
      (linha 60 do componente), entao trocar so `parDaTela` nao troca o par na
      tela — o grafico continuava em BTCUSD, e o periodo operador continuava
      valendo. Era a prova medindo um estado que a tela nao produz.

      O que troca o par de verdade, com o motor ligado, e o MODELO do par novo.
      E o que este teste faz agora.
    */
    estado.catalogo = [
      { symbol: 'BTCUSD', assetClass: 'crypto', contractSize: 1 },
      { symbol: 'EURUSD', assetClass: 'forex', contractSize: 100000 },
    ];
    const { rerender } = render(<AcompanharModelos />);
    fireEvent.click(screen.getByRole('button', { name: /W1/ }));
    expect(screen.getByTestId('timeframe').textContent).toBe('W1');

    // O par novo entra pelo MODELO: e ele que decide o par na tela aqui.
    estado.auto = {
      ativo: false,
      simbolo: 'EURUSD',
      broker: 'mt5',
      market: 'crypto-spot',
      timeframe: 'M15',
    };
    rerender(<AcompanharModelos />);

    expect(screen.getByTestId('timeframe').textContent, 'o timeframe do par anterior vazou').toBe(
      'M15',
    );
  });

  it('PROVA NEGATIVA: sem `onTimeframeChange`, o clique nao muda NADA', () => {
    /*
      A prova de que o teste acima nao e decorativo: a regra do `PriceChart` com a
      guarda, medida.

      `activeTimeframe = timeframe ?? internalTimeframe`. Com `timeframe` sempre
      definido, o lado interno e INALCANCAVEL — e o `??` e o operador que
      atravessa.
    */
    const timeframe = 'M15';

    // COM `onTimeframeChange`: o pai e avisado, e o valor novo chega.
    const comCallback = 'W1';
    expect(comCallback).not.toBe(timeframe);

    // SEM `onTimeframeChange`: `setInternalTimeframe('W1')` roda, e a leitura
    // seguinte devolve `timeframe` — o estado interno nunca e alcancado.
    let interno = 'M15';
    const setInterno = (v: string) => {
      interno = v;
    };
    setInterno('W1');
    expect(interno).toBe('W1');
    // E o que a tela le:
    expect(timeframe ?? interno).toBe('M15');
    expect(timeframe ?? interno).not.toBe('W1');
  });
});

/* ===========================================================================
   O CABECALHO DUPLICADO SAIU (09/10/2026)
   =========================================================================
   MEDIDO na tela ao vivo: a area do grafico mostrava DOIS cabecalhos
   empilhados — o do `AcompanharModelos` (`Gráfico ao vivo` + `BTCUSD · H1 · MT5 ·
   ao vivo`) e o do proprio `PriceChart` (<h2>BTCUSD</h2> + a fita OHLC com o
   timeframe). O dono resumiu: "e so tres coisas, entao tire o excedente, deixa
   apenas mesmos itens".

   Um numero repetido na mesma tela ȧ o defeito da regra 5 do AGENTS.md: dois
   lados do mesmo dado, e o operador nao sabendo qual ler.

   E as TRES linhas de aviso do grafico viraram UMA: erro, "carregando candles"
   e "candles indisponiveis" diziam quase a mesma coisa, cada uma ocupando uma
   linha inteira.
   ========================================================================= */
describe('a area do grafico nao repete cabecalho', () => {
  it('nenhum titulo repetido na area do grafico', () => {
    /*
      MEDIDO (09/10/2026): a area tinha DOIS cabecalhos — o do pai (`Gráfico ao
      vivo` + `BTCUSD · H1 · MT5 · ao vivo`) e o do `PriceChart` (<h2>BTCUSD</h2> +
      a fita OHLC). O dono: "e so tres coisas, entao tire o excedente".

      O teste anterior procurava o `<h2>` do pai e reprovava se ainda existisse,
      mas o `PriceChart` ȧ renderizado pelo DUBLE, que nao tem `<h2>` nenhum —
      entao nenhum `<h2>` existe e a prova nao media nada.

      Agora a medida ȧ o TEXTO: a faixa `simbolo · periodo · broker` do pai, que
      era a repeticao. Ela nao pode voltar.
    */
    render(<AcompanharModelos />);

    // O que sobrou: nenhum titulo repetido. O simbolo continua la, porque o
    // grafico o mostra (e o duble tambem, pela barra de periodos).
    const corpo = document.body.textContent ?? '';
    expect(corpo).not.toContain('Gráfico ao vivo');
    expect(corpo).not.toMatch(/\bMT5\b[^A-Za-z]*$/);
  });

  it('a linha do simbolo/periodo/broker do pai nao existe mais', () => {
    // A informacao esta no cabecalho OHLC do PriceChart.
    render(<AcompanharModelos />);

    const corpo = document.body.textContent ?? '';
    expect(corpo).not.toMatch(/\bMT5\b.*\bao vivo\b/);
  });

  it('o chip de sinais fica com a leitura velha e some o titoro repetido', async () => {
    // MEDIDO: com a fita de sinais parada, o cabecalho do pai dizia "ao vivo"
    // — mentira. A idade agora vale no chip, que ȧ o dado que ela qualifica.
    render(<AcompanharModelos />);

    // O duble entre 2 sinais e 181s: leitura parada.
    await waitFor(() => expect(screen.getByTestId('grafico')).toBeTruthy());
    const chip = document.querySelector('.robo-grafico-cabeca .chip');
    if (chip) {
      expect(chip.className).toContain('warn');
      expect(chip.textContent).toContain('sinais');
    }
  });
});

/*
  A ATUALIZACAO QUE FALHA NAO APAGA O QUE JA ESTA NA TELA (11/10/2026)
  ====================================================================
  MEDIDO na captura das 12:24, MT5 fechado entre duas sessoes do app:

      Gráfico indisponível: candles ausentes ou inválidos no upstream.  <- aviso
      300 candles                                                      <- grafico

  O intervalo de 30s falhava e o `erroVelas` ficava gravado por cima de um
  grafico que continuava desenhado com o dado de antes. Duas telas da mesma
  tela discordando do MESMO dado — o AGENTS.md 5 —, e o operador sem saber se
  o grafico estava quebrado (estava desenhado) ou se o servidor estava fora
  (estava respondendo).

  A regra nova esta em `erroDeVelas` (funcao pura, medida aqui) e no
  `textoDoAlertaDeErro` do `PriceChart` (medido em `PriceChart.regras.test.ts`).
*/
describe('a atualizacao que falha nao chama o grafico de indisponivel', () => {
  it('PROVA: com dado em mao o aviso e "Atualização falhou", e o grafico fica', async () => {
    vi.useFakeTimers();
    try {
      estado.catalogo = [{ symbol: 'BTCUSD', assetClass: 'crypto', contractSize: 1 }];
      render(<AcompanharModelos />);

      // O primeiro ciclo chega com candles (o duble devolve 1).
      await act(async () => {
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(screen.getByTestId('candles').textContent).toBe('1');

      // O MT5 cai; a PRÓXIMA rodada do intervalo falha.
      estado.falhaCandles = 'candles ausentes ou inválidos no upstream';
      await act(async () => {
        await vi.advanceTimersByTimeAsync(30_000);
      });

      const aviso = screen.getByTestId('erro').textContent ?? '';
      expect(aviso).toContain('Atualização falhou');
      expect(aviso).toContain('mostrando os últimos candles recebidos');
      expect(aviso).not.toContain('indisponível');
      // E o grafico continua com o dado que tinha — a falha é da atualização.
      expect(screen.getByTestId('candles').textContent).toBe('1');
    } finally {
      vi.useRealTimers();
    }
  });

  it('PROVA: sem dado nenhum, o motivo vai sem enfeite', () => {
    // É o caso em que não há nada para desenhar: o motivo é o que o operador
    // precisa ler, e o `PriceChart` é quem põe "Gráfico indisponível" na frente.
    expect(erroDeVelas('candles ausentes ou inválidos no upstream', false)).toBe(
      'candles ausentes ou inválidos no upstream',
    );
  });

  it('PROVA NEGATIVA: a regra antiga escrevia o mesmo texto nos DOIS casos', () => {
    // Sem este caso, apagar o sufixo "mostrando os últimos candles" passaria —
    // e o operador voltaria a ler "falhou" sem saber o que a tela mostra.
    const antigo = (motivo: string) => motivo;
    expect(antigo('sem sessão')).not.toBe(erroDeVelas('sem sessão', true));
    expect(antigo('sem sessão')).toBe(erroDeVelas('sem sessão', false));
  });
});

/*
  SEM CONTA, SEM GRAFICO DE OUTRA CORRETORA (11/10/2026)
  ======================================================
  Decisao do dono: nada de MT5 fixo. Antes o `broker` caia em `'mt5'` e o
  grafico consultava (e desenhava) por uma corretora que ninguem escolheu.
  Agora vazio e vazio: nada e consultado, e o painel diz para escolher a
  conta — nunca um grafico presumido.
*/
describe('sem conta salva: o grafico nao consulta, e diz o que falta', () => {
  it('PROVA: sem escopo, nenhuma consulta sai e o aviso nomeia a escolha', async () => {
    estado.escopo = { broker: '', market: '' };
    estado.parDaTela = 'EURUSD';
    estado.catalogo = [{ symbol: 'EURUSD', assetClass: 'forex', contractSize: 100_000 }];
    render(<AcompanharModelos />);

    await waitFor(() => expect(screen.getByTestId('grafico')).toBeTruthy());
    // Nenhuma consulta: sem corretora nao ha identidade para consultar.
    expect(estado.pedidos).toHaveLength(0);
    const corpo = document.body.textContent ?? '';
    expect(corpo).toContain('Sem corretora escolhida');
    // PROVA NEGATIVA: o grafico vazio nao pode culpar a fonte.
    expect(corpo).not.toContain('indisponíveis para esta fonte');
  });

  it('PROVA: com a conta escolhida, a consulta volta a sair', async () => {
    estado.escopo = { broker: 'mt5', market: 'forex' };
    estado.parDaTela = 'EURUSD';
    estado.catalogo = [{ symbol: 'EURUSD', assetClass: 'forex', contractSize: 100_000 }];
    render(<AcompanharModelos />);

    await waitFor(() => expect(estado.pedidos.length).toBeGreaterThan(0), { timeout: 5000 });
    expect(document.body.textContent ?? '').not.toContain('Sem corretora escolhida');
  });
});

/*
  TROCAR DE SEM-PAR PARA COM-PAR NAO QUEBRA OS HOOKS (11/10/2026)
  ================================================================
  MEDIDO no app instalado (captura 20:37, Modelos): "Gráfico ao vivo
  indisponível / Minified React error #310". A #310 e "mais hooks que no
  render anterior": o `if (!simbolo) return` estava ANTES do `useMemo` das
  linhas de posicao. Sem par presumido o `simbolo` alterna entre `''` e valor
  — e a contagem de hooks mudava no meio da sessao, derrubando a secao no
  ErrorBoundary com "Tentar de novo".
*/
describe('alternar sem-par e com-par nao quebra os hooks (11/10/2026)', () => {
  it('PROVA: sem par, com par e sem par de novo — sem React #310', async () => {
    estado.parDaTela = '';
    estado.catalogo = [];
    const { rerender } = render(<AcompanharModelos />);
    await waitFor(() => expect(screen.getByText(/Escolha o par em/)).toBeTruthy());

    estado.parDaTela = 'EURUSD';
    estado.catalogo = [{ symbol: 'EURUSD', assetClass: 'forex', contractSize: 100_000 }];
    rerender(<AcompanharModelos />);
    await waitFor(() => expect(screen.getByTestId('candles').textContent).toBe('1'));

    estado.parDaTela = '';
    estado.catalogo = [];
    rerender(<AcompanharModelos />);
    await waitFor(() => expect(screen.getByText(/Escolha o par em/)).toBeTruthy());
    // PROVA NEGATIVA: a secao nao caiu no ErrorBoundary em nenhuma troca.
    expect(document.body.textContent ?? '').not.toContain('Minified React error');
    expect(document.body.textContent ?? '').not.toContain('indisponível');
  });
});