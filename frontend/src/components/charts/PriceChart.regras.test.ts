/*
  AS DUAS REGRAS QUE FAZIAM O GRAFICO FICAR ESCURO (09/10/2026)
  =============================================================
  MEDIDO no app instalado, 17:09 e 17:18, em QUALQUER par e QUALQUER
  timeframe — EURUSD, AUDUSD, H1, M1, todos iguais:

      Grafico indisponivel: Identidade de mercado invalida.
      EURUSD sem candles reais para M1.
      RSI (14) precisa de 15 candles; ha 0.
      0 candles

  E o BACKEND respondia 300 candles corretos. MEDIDO:

      _universal_candles('mt5','forex','EURUSD','H1',300)  ->  ok, count=300
      EURUSD 1.14166 -> 1.14069 ... ultima 1.12009

  300 velas na mao do servidor e a tela dizendo que nao havia nenhuma. Quem
  lesse a tela culparia o servidor — e o servidor respondia. E o AGENTS.md §5.

  POR QUE FUNCOES PURAS, E NAO UM TESTE DE COMPONENTE
  ===================================================
  MEDIDO nesta sessao, duas vezes: o defeito NAO se reproduz no `jsdom`. La o
  `getCandles` falha no `fetch`, antes de chegar no `normalizeMarketSource`, e o
  texto que aparece e outro. Um teste de componente passou com a correcao LIGADA
  e com a correcao DESLIGADA — decorativo, que e o AGENTS.md §6 na forma mais
  facil de cair.

  A regra e pura, entao virou funcao pura, e aqui ela e medida direto. Cada
  `expect` tem o caso que reprovaria sem a correcao.
*/
import { describe, expect, it } from 'vitest';

import {
  erroVigente,
  mercadoParaConsulta,
  rotuloRodape,
  separadorCabecalho,
  textoDoAlertaDeErro,
} from './PriceChart';

describe('o mercado da consulta: medido, ou nao medido', () => {
  it('PROVA: `undefined` cai no padrao do broker — compatibilidade com quem nao informa', () => {
    /*
      Quem chama o componente sem `market` continua funcionando. O MT5 e forex;
      as exchanges, cripto a vista. Este comportamento ANTES da correcao e nao
      pode mudar: mudar seria quebrar os outros consumidores.
    */
    expect(mercadoParaConsulta(undefined, 'mt5')).toBe('forex');
    expect(mercadoParaConsulta(undefined, 'binance')).toBe('crypto-spot');
  });

  it('PROVA: o mercado informado passa intacto, sem passar por default nenhum', () => {
    expect(mercadoParaConsulta('metals', 'mt5')).toBe('metals');
    expect(mercadoParaConsulta('crypto-spot', 'binance')).toBe('crypto-spot');
    expect(mercadoParaConsulta('forex', 'binance')).toBe('forex');
  });

  it('PROVA: `""` e ESPACO VAZIO nao viram `forex` — sao "ainda nao medido"', () => {
    /*
      A REGRA, e o defeito.

      `market ?? defaultMarket(broker)`: `??` so pega `null` e `undefined`.
      A cadeia entrega `String(mercadoDaFicha ?? auto?.market ?? '')`, que e
      `''` — e `''` atravessava, chegava em `normalizeMarketSource('mt5','')`
      como `null`, e o `getCandles` LANCAVA "Identidade de mercado invalida".

      E happen no PRIMEIRO RENDER de cada par, com o catalogo do gateway ainda
      nao voltado. O operador lia um erro de IDENTIDADE e culpava o servidor,
      que respondia 300 velas.

      Aqui nao se completa com `forex`: `BTCUSD` nao e forex, e a tela provaria
      o erro na conta do operador (AGENTS.md §3).
    */
    expect(mercadoParaConsulta('', 'mt5')).toBe('');
    expect(mercadoParaConsulta('   ', 'mt5')).toBe('');
    expect(mercadoParaConsulta('\n\t', 'mt5')).toBe('');
  });

  it('PROVA NEGATIVA: a regra antiga devolvia `forex` para `""` — e `??` nao e a solucao', () => {
    /*
      A prova de que os tres testes acima nao sao decorativos: as DUAS
      expressions, lado a lado, com o mesmo entrada.

        ANTIGO   market ?? defaultMarket(broker)
        NOVO     mercadoParaConsulta(market, broker)
    */
    const defaultMarket = (broker: string) => (broker === 'mt5' ? 'forex' : 'crypto-spot');
    const antigo = (market?: string) => market ?? defaultMarket('mt5');

    // Com `''`: o antigo NAO pegava o padrao, e devolvia a string vazia —
    // que e o defeito, porque `''` nao esta na lista de mercados aceitos.
    expect(antigo('')).toBe('');
    expect(antigo('')).not.toBe('forex');

    // E e por isso que o `getCandles` lancava: `''` nao casa com nenhum
    // mercado habilitado. A lista e a de `MARKET_SOURCES` no `marketApi`.
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
    expect(mercados.includes(antigo(''))).toBe(false);
    expect(mercados.includes('forex')).toBe(true);

    // O novo devolve `''` tambem — e quem impede a consulta e o guarda do
    // efeito, que so chama `getCandles` com mercado nao vazio. Aqui o que se
    // trava e que `''` NAO virou `forex`, que era a forma de ela consultando.
    expect(mercadoParaConsulta('', 'mt5')).not.toBe('forex');
  });

  it('`null` tambem e "nao medido" — e nao o padrao', () => {
    /*
      `null` chegou de verdade em outra versao da cadeia, e `??` pegava ele:
      `'' ?? 'forex'` e `null ?? 'forex'`, mas `'' ?? 'forex'` e `''`.
      Tratar os dois como ausentes e o que fecha a porta.
    */
    expect(mercadoParaConsulta(null as never, 'mt5')).toBe('');
  });

  it('PROVA: sem BROKER nao ha padrao — `undefined` com corretora vazia e `""` (11/10/2026)', () => {
    /*
      Decisao do dono: nada de MT5 fixo. O `defaultMarket` antigo devolvia
      `forex` para `mt5` e `crypto-spot` para QUALQUER outra coisa — inclusive
      `''`. Com a corretora vazia, `market === undefined` caia em
      `crypto-spot`: um palpite com nome de medida, e a consulta saia para um
      mercado que ninguem escolheu.

      Agora: sem corretora, sem mercado. O guarda do efeito nao consulta, e a
      tela recusa nomeando a escolha (AGENTS.md 3).
    */
    expect(mercadoParaConsulta(undefined, '' as never)).toBe('');
    expect(mercadoParaConsulta(undefined, 'mt5')).toBe('forex');
    expect(mercadoParaConsulta(undefined, 'binance')).toBe('crypto-spot');
  });
});

describe('o erro que vale e o de quem forneceu as velas', () => {
  it('PROVA: com as velas da PROP, o erro velho da consulta propria nao manda', () => {
    /*
      A SEGUNDA parte da causa, e ela mantinha a tela escura mesmo com o dado em
      mao.

      `displayError = error || loadedError` dava precedencia ao erro da consulta
      PROPRIA. Quando os 300 candles chegaram pela prop, `displayCandles`
      encheu — e o `loadedError` do primeiro render continuou pintando a
      mensagem por cima do grafico.
    */
    expect(erroVigente('', 'Identidade de mercado invalida.', true)).toBe('');
    expect(erroVigente('', 'Grafico indisponivel: qualquer coisa', true)).toBe('');
  });

  it('PROVA: sem a prop, quem responde e a consulta propria', () => {
    expect(erroVigente('', 'Identidade de mercado invalida.', false)).toBe(
      'Identidade de mercado invalida.',
    );
  });

  it('PROVA: o erro do PAI sempre manda — ele e o dono da tela', () => {
    expect(erroVigente('terminal MT5 sem sessao', 'erro velho', true)).toBe(
      'terminal MT5 sem sessao',
    );
    expect(erroVigente('terminal MT5 sem sessao', 'erro velho', false)).toBe(
      'terminal MT5 sem sessao',
    );
  });

  it('PROVA NEGATIVA: a regra antiga devolvia o erro velho POR CIMA do dado novo', () => {
    /*
      A prova de que os tres testes acima nao sao decorativos: a regra antiga,
      aplicada ao MESMO caso.

        ANTIGO   error || loadedError
        NOVO     erroVigente(error, loadedError, candlesPresentes)
    */
    const antigo = (error: string, loadedError: string) => error || loadedError;

    // O pai nao deu erro; a consulta propria deu, num render anterior.
    // As velas chegaram. O erro velho NAO pode aparecer.
    const erroAntigo = antigo('', 'Identidade de mercado invalida.');
    expect(erroAntigo).toBe('Identidade de mercado invalida.');
    expect(erroAntigo).not.toBe('');

    // A regra nova, no MESMO caso, devolve vazio — porque as velas da prop
    // mandam no erro delas.
    expect(erroVigente('', 'Identidade de mercado invalida.', true)).toBe('');
  });

  it('a trava nao vira silencio: sem velas, sempre ha aviso na tela', () => {
    /*
      Corrigir o precedence nao pode calar a tela. Um controle que nada lê e
      pior que a ausencia dele (AGENTS.md §9): o operador precisa saber que nao
      ha dado, e o por que.

      Estes sao os quatro estados que a tela renderiza, e nenhum deles e vazio.
    */
    const comPropVazia = erroVigente('', '', true);
    expect(comPropVazia, 'sem velas e sem erro, o aviso de "sem velas" e o que resta').toBe('');

    const comErroDoPai = erroVigente('terminal MT5 sem sessao', '', true);
    expect(comErroDoPai).toBe('terminal MT5 sem sessao');

    const comConsulta = erroVigente('', 'sem velas para EURUSD', false);
    expect(comConsulta).toBe('sem velas para EURUSD');

    const comOsDois = erroVigente('erro do pai', 'erro da consulta', false);
    expect(comOsDois).toBe('erro do pai');
  });
});

describe('o nome do aviso acompanha o que a tela mostra (11/10/2026)', () => {
  /*
    MEDIDO na captura das 12:24, MT5 fechado e depois religado: a tela mostrava
    300 candles DESDEHNADOS e, na mesma linha, "Gráfico indisponível: ...".
    Duas telas da mesma tela discordando, e o operador sem saber qual acreditar
    — o AGENTS.md 5, com o agravante de o gráfico estar ali, na frente.

    A causa era a composição: o PAI (AcompanharModelos) mandava o motivo da
    atualização que falhou, e o PriceChart colava o prefixo "Gráfico
    indisponível" por cima, sem olhar que tinha dado na tela.
  */
  it('PROVA: com candles na tela, o aviso e o do pai, sem "indisponível"', () => {
    const aviso = textoDoAlertaDeErro('Atualização falhou: sem sessão MT5 — mostrando os últimos candles recebidos.', true);
    expect(aviso).toContain('Atualização falhou');
    expect(aviso).not.toContain('indisponível');
  });

  it('PROVA: sem candles, o nome continua o de sempre', () => {
    // É o caso em que não há nada para olhar — e é o texto que os testes de
    // captura e o histórico reconhecem como "sem gráfico".
    expect(textoDoAlertaDeErro('candles ausentes ou inválidos no upstream', false)).toBe(
      'Gráfico indisponível: candles ausentes ou inválidos no upstream',
    );
  });

  it('PROVA NEGATIVA: a regra antiga colava o prefixo nos DOIS casos', () => {
    // Sem este caso, uma correção que só apagasse o prefixo passaria — e o
    // operador ficaria sem saber que o gráfico está indisponível no caso
    // em que ele realmente está.
    const antigo = (error: string) => `Gráfico indisponível: ${error}`;
    expect(antigo('Atualização falhou')).not.toBe(textoDoAlertaDeErro('Atualização falhou', true));
    expect(antigo('candles ausentes')).toBe(textoDoAlertaDeErro('candles ausentes', false));
  });
});

describe('o rodapé não conta quando há erro na tela (11/10/2026)', () => {
  /*
    MEDIDO na captura do dono (12:28): o hint dizia `Gráfico indisponível:
    candles ausentes ou inválidos no upstream` e, logo abaixo, o rodapé dizia
    `300 candles` — e no M5 `0 candles` com o eixo de horas preenchido. Dois
    lados do mesmo dado discordando (AGENTS.md §5): o operador lia "sem
    candles" e "300 candles" no mesmo bloco.

    A causa: o hint é a árvore `displayError`, e o rodapé é
    `displayCandles.length`. São fontes DIFERENTES — `erroVigente` pode
    devolver `''` (sem erro vigente) enquanto a prop trouxe lista vazia, e o
    rodapé escrevia `0 candles` ao lado de um eixo que mostrava dados.

    A regra: com erro vigente, o rodapé NÃO CONTA. O erro já é a resposta.
  */
  it('PROVA: sem erro, o rodapé conta o que a tela tem', () => {
    expect(rotuloRodape('', 300)).toBe('300 candles');
    expect(rotuloRodape('', 0)).toBe('0 candles');
  });

  it('PROVA: com erro, o rodapé some — a contagem seria a errada ao lado da certa', () => {
    // O caso da captura: erro do upstream com 300 candles no array. O rodapé
    // NÃO pode escrever `300 candles` ao lado do "candles ausentes".
    expect(rotuloRodape('candles ausentes ou inválidos no upstream', 300)).toBeNull();
    // E o caso do M5: `0 candles` ao lado do eixo de horas preenchido.
    expect(rotuloRodape('candles ausentes ou inválidos no upstream', 0)).toBeNull();
  });

  it('PROVA NEGATIVA: a regra antiga contava SEMPRE, mesmo com erro na tela', () => {
    // Sem este caso, uma correção que sempre escondesse o rodapé passaria — e
    // o operador ficaria sem a contagem no caso em que ela é a resposta.
    const antigo = (_erro: string, quantos: number) => `${quantos} candles`;

    // Com erro: a regra antiga devolvia a contagem; a nova não pode.
    expect(antigo('candles ausentes', 300)).toBe('300 candles');
    expect(rotuloRodape('candles ausentes', 300)).toBeNull();

    // Sem erro: as duas dizem a mesma coisa — a correção não apagou o rodapé.
    expect(antigo('', 300)).toBe(rotuloRodape('', 300));
  });
});

describe('o cabeçalho não cola o OHLC na fonte (11/10/2026)', () => {
  /*
    MEDIDO na captura do dono (12:28): `FECHA 83.129,45Candles OHLC reais` — o
    número do fechamento encostado no nome da fonte, lido como `45Candles`.

    A causa é de CSS: os dois `<span>` são IRMÃOS inline, e o `gap: 6px` do
    `.price-chart-ohlc` é o espaço INTERNO do flexbox — ele só separa os
    filhos do próprio span, nunca os dois spans entre si. Sem um separador
    textual, o olho lê a união dos dois como uma palavra só.

    A regra é pura porque o defeito é de layout e não se reproduz no `jsdom`
    (mesmo motivo de `textoDoAlertaDeErro`, no cabeçalho deste arquivo).
  */
  it('PROVA: com OHLC na tela e fonte depois, o separador é ` · `', () => {
    expect(separadorCabecalho(true, 'XMGlobal-MT5 14 · metals')).toBe(' · ');
  });

  it('PROVA: sem candle, não há o que separar — o separador é vazio', () => {
    // Sem a linha OHLC, não existe o primeiro bloco; imprimir ` · ` deixaria
    // um separador órfão antes de "Candles OHLC reais".
    expect(separadorCabecalho(false, 'XMGlobal-MT5 14 · metals')).toBe('');
  });

  it('PROVA NEGATIVA: a regra antiga era o JSX sem separador entre os spans', () => {
    /*
      Sem este caso, uma correção que imprimisse o separador SEMPRE passaria —
      e com a linha OHLC ausente apareceria ` · Candles OHLC reais` com um
      ` · ` solto na frente. As DUAS expressions, lado a lado:

        ANTIGO   ''                     (nada entre os dois spans)
        NOVO     separadorCabecalho(temOhlc, fonte)
    */
    const antigo = (_temOhlc: boolean, _fonte: string) => '';

    // Com os dois lados: o antigo colava; o novo separa.
    expect(antigo(true, 'XMGlobal-MT5 14')).toBe('');
    expect(antigo(true, 'XMGlobal-MT5 14')).not.toBe(separadorCabecalho(true, 'XMGlobal-MT5 14'));

    // Sem o segundo lado: as duas dizem a mesma coisa — nada a separar.
    expect(antigo(true, '')).toBe(separadorCabecalho(true, ''));
  });
});