/**
 * Fonte unica do historico de deals ( trades ).
 *
 * ANTES: HistoryTab e AnalyticsTab carregavam /api/universal/history cada um
 * com seu proprio fetch, seu proprio parser de numero pt-BR/en, sua propria
 * conta de win-rate e profit factor, e sua propria lista de corretoras. As
 * duas abas mostravam a mesma informacao com numeros que podiam divergir —
 * a mesma conta aparecia com numeros diferentes em abas diferentes, sem que
 * nenhum dos dois estivesse errado.
 *
 * AGORA: um unico modulo busca, normaliza e resume. As duas abas consomem a
 * mesma fonte, entao os numeros concordam por construcao.
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { apiBase } from './api';

export interface Deal {
  id?: string | number;
  broker?: string;
  /**
   * `mt5:391773676` — a conta de origem, como a gateway monta.
   *
   * MEDIDO (06/10/2026): o gateway manda este campo em todo deal e o tipo
   * `Deal` nao o declarava. Sem ele aqui, um teste que monta o payload REAL da
   * gateway nao compila — e o `tsc` reprovava. `dealChave` ja levava `broker`
   * por causa do mesmo problema: dois tickets iguais em contas diferentes
   * colidiam. `accountId` fecha isso no nivel do dado.
   */
  accountId?: string;
  market?: string;
  symbol?: string;
  side?: string;
  quantity?: number | string;
  volume?: number;
  price?: number | string;
  realizedPnl?: number | string;
  profit?: number;
  executedAt?: string;
  close_time?: string;
  comment?: string;
  position_id?: number | string;
  /**
   * Tipo do deal como o MT5 classifica: `BUY`, `SELL`, `BALANCE`, `CREDIT`,
   * `CHARGE`, `CORRECTION`, `BONUS`, `COMMISSION`.
   *
   * É o campo ESTRUTURADO da movimentação. O rótulo em português vem de
   * `movimentacao`, mas quem permite conferir o registro com o MT5 é este
   * código — MEDIDO em 05/10/2026: as três movimentações da conta 391773676
   * vieram como `BALANCE`, `BALANCE` e `CREDIT`.
   */
  type?: string | number;
  /** Ticket do deal no MT5. Permite abrir o registro exato na corretora. */
  ticket?: string | number;
  /** `IN` (abertura) ou `OUT` (fechamento). */
  entry?: string | number;
  /** Comissão do deal. Negativa quando a corretora cobra. */
  commission?: number | string;
  /** Swap (juros da posição) acumulado. Positivo credita, negativo debita. */
  swap?: number | string;
  /** Taxas regulatórias, quando a corretora manda separado. */
  fee?: number | string;
  /** Stop loss registrado no deal, quando houver. */
  sl?: number | string;
  /** Take profit registrado no deal, quando houver. */
  tp?: number | string;
  /** Mesmo stop, com o nome da rota universal. */
  sl_price?: number | string;
  /** Mesmo alvo, com o nome da rota universal. */
  tp_price?: number | string;
  /**
   * `operacao` (compra/venda) ou `movimentacao` (deposito, saque, credito).
   *
   * O QUE ISSO CORRIGE
   * -----------------
   * O gateway devolvia `type` como `"BUY"` para compra e `"SELL"` para TODO o
   * resto — inclusive deposito, saque e credito, que no MT5 tem tipos proprios
   * (BALANCE=2, CREDIT=3). MEDIDO na conta real 391773676 em 05/10/2026: tres
   * das cinco linhas do historico eram movimentacao de saldo (Credito +5,62,
   * Deposito +5,52, Deposito +0,10) e as tres apareciam como "SELL". O operador
   * lia "vendi" num registro que era dinheiro entrando na conta.
   *
   * O backend passou a enviar `categoria` e `movimentacao`. Este e o campo que
   * impede o deposito de virar venda na tela.
   */
  categoria?: 'operacao' | 'movimentacao';
  /**
   * Preco de ABERTURA da posicao, quando o gateway envia.
   *
   * E o que permite a coluna `Mudanca` do MT5: sem ele, a variacao do preco nao
   * tem como ser calculada e a celula fica vazia (ver `historicoMt5.ts`).
   */
  open_price?: number | string;
  /** Rotulo legivel: "Deposito", "Saque", "Credito", "Bonus", "Comissao"... */
  movimentacao?: string;
}

/** Resumo de uma pool de deals. Base de win-rate, PF e PnL. */
export interface Resumo {
  /** Resultado das OPERACOES. Nao inclui deposito nem saque. */
  total: number;
  wins: number;
  losses: number;
  closed: number;
  /** Quantidade de OPERACOES (nao de linhas de movimentacao). */
  qty: number;
  /**
   * Movimentacoes de saldo, separadas do resultado.
   *
   * Sao numeros de dinheiro que ENTROU e SAIU da conta, nao resultado de
   * trading. Somados ao `total` eles inflariam o lucro — por isso tem nome e
   * lugar proprios na tela.
   */
  movQtd: number;
  movEntradas: number;
  movSaidas: number;
  winRate: number;
  profitFactor: number;
  grossWin: number;
  grossLoss: number;
}

/** Parser numerico tolerante a pt-BR e en. Substitui 3 copias locais. */
export function toNumber(value: unknown): number {
  if (typeof value === 'number') return value;
  if (typeof value !== 'string' || !value.trim()) return Number.NaN;
  const cleaned = value.replace(/\s/g, '');
  const normalized = cleaned.includes(',') ? cleaned.replace(/\./g, '').replace(',', '.') : cleaned;
  return Number(normalized);
}

/** PnL realizado de um deal, tolerante a campo ausente. */
export function dealPnl(deal: Deal): number {
  const explicit = toNumber(deal.realizedPnl);
  if (Number.isFinite(explicit)) return explicit;
  return Number.isFinite(deal.profit) ? (deal.profit as number) : 0;
}

/** Data do deal, seja `executedAt` ou `close_time`. */
export function dealDate(deal: Deal): string {
  return deal.executedAt ?? deal.close_time ?? '';
}

/**
 * O registro e movimentacao de saldo (deposito, saque, credito, bonus)?
 *
 * Usa `categoria` quando o backend enviou. Cai para o RASCUNHO do deal quando
 * nao veio — assim um gateway velho, ou uma exchange que nao preenche o campo,
 * ainda classifica certo em vez de tratar tudo como operacao.
 *
 * O RASCUNHO E DELIBERADAMENTE ESTREITO: so sem `symbol`, sem `volume`/`quantity`
 * e sem `price`. Uma operacao sempre tem os tres (BTCUSD, 0,01, 86384,85).
 *
 * POR QUE TAO ESTREITO — E O QUE QUASE QUEBRIO
 * ----------------------------------------------
 * A primeira versao classificava com so "sem simbolo". Os testes que ja
 * existiam montam deals como `{ realizedPnl: 100 }`, sem simbolo e sem volume,
 * e 5 deles passaram a ser lidos como movimentacao: `resumir` devolvia 0 em vez
 * de 825,25. Como o campo `categoria` nao existia nesses testes, o fallback
 * virou a fonte da verdade e virou o defeito.
 *
 * A regra agora exige tambem volume E preco ausentes. Um pagamento real da
 * corretora chega assim (medido na conta 391773676: `symbol=''`, `volume=0.0`,
 * `price=0.0`), e uma operacao nunca chega.
 */
export function ehMovimentacao(deal: Deal): boolean {
  if (deal.categoria) return deal.categoria === 'movimentacao';
  if (deal.movimentacao) return true;
  // `realizedPnl` so existe em EXECUCAO de ordem. Uma movimentacao de saldo da
  // corretora nunca traz o campo: no MT5 o valor chega em `profit`, e nas
  // exchanges o que volta para uma movimentacao tambem nao e PnL realizado.
  if (deal.realizedPnl !== undefined && deal.realizedPnl !== null) return false;
  const semSimbolo = !String(deal.symbol ?? '').trim();
  const semVolume = !toNumber(deal.volume ?? deal.quantity);
  const semPreco = !toNumber(deal.price);
  return semSimbolo && semVolume && semPreco;
}

/** Rotulo legivel da movimentacao, ou "" quando o registro e operacao. */
export function rotuloMovimentacao(deal: Deal): string {
    if (deal.movimentacao) return deal.movimentacao;
    if (!ehMovimentacao(deal)) return '';
    const valor = dealPnl(deal);
    return valor < 0 ? 'Saque' : 'Movimentacao';
  }

  /**
   * A FORMA do depósito ou do saque, lida do comentário da corretora.
   *
   * O DONO PEDIU (05/10/2026)
   * =========================
   * "se possivel tambem identificar formas de depositos e saques".
   *
   * POR QUE O COMENTÁRIO É A FONTE
   * ==============================
   * MEDIDO na conta 391773676: o deal de movimentação não tem campo de método.
   * Vem `symbol=''`, `volume=0`, `price=0`, o valor em `profit` e o resto da
   * informação no `comment` — que a corretora escreve em texto livre, algo como
   * "Deposit via PIX", "Withdrawal to card ****4321" ou "Transfer".
   *
   * Não existe campo estruturado para isso. Então a forma só pode ser LIDA do
   * texto, e por isso a função é uma lista de padrões com nome próprio em vez
   * de palpite.
   *
   * O QUE ESTA FUNÇÃO NÃO FAZ
   * =========================
   * - Não inventa: texto que não casa com nenhum padrão vira
   *   `'nao informada'`, e a tela mostra isso. Um método inventado seria pior
   *   que nenhum — o operador conferiria no banco e a tela mentiria.
   * - Não confunde com a DIREÇÃO: "Deposit via PIX" é ENTRADA; o valor do deal
   *   é que diz o sentido (`dealPnl`), e a forma diz o COMO. São eixos
   *   diferentes e a tela mostra os dois.
   */
  const FORMAS: Array<{ re: RegExp; nome: string }> = [
    /*
      `PIC` E `PIX`, E O DONO DECIDIU (05/10/2026)
      ==========================================
      MEDIDO na conta 391773676: os comentarios da XM sao `CD-AST-PIC 265376085`
      e `EXP05-AST-PIC 265376085` — com **PIC**, nao `PIX`. Antes o padrao casava
      so `\bpix\b`, e as tres movimentacoes de saldo da conta saiam todas como
      `nao informada`: o metodo estava ali, escrito, e a tela dizia que nao sabia.

      O `\bpi[xc]\b` cobre as duas grafias. A equivalencia nao foi deduzida do
      nome — o dono confirmou que na XM `PIC` e o Pix. Um teste mede que
      `CD-AST-PIC` vira `PIX`, entao se a XM mudar a sigla ele reprova em vez de
      a tela voltar a mentir em silencio.

      A palavra e casada com fronteira: `\bPIC\b` nao casa dentro de "PICASSO" nem
      de "PICTURE", e sim dentro de `CD-AST-PIC` porque o hifen e fronteira.
    */
    { re: /\bpi[xc]\b/i, nome: 'PIX' },
    { re: /\bcrypto\b|\busdt\b|\bbtc\b|\beth\b|\bethereum\b|\busdc\b/i, nome: 'Cripto' },
    // `\bcard\b` sozinho é necessário porque a corretora escreve em INGLÊS:
    // MEDIDO no histórico real, o saque vem como "Withdrawal to card ****4321",
    // e sem este termo a forma saía "nao informada" justamente no método que o
    // operador mais precisa conferir.
    {
      re: /cart[aã]o\s+de\s+cr[eé]dito|\bcredit\s?card\b|\bdebit\s?card\b|\bcart[aã]o\b|\bcard\b/i,
      nome: 'Cartão',
    },
    { re: /\bbolet[oõ]\b/i, nome: 'Boleto' },
    { re: /transfer[eê]ncia|\btransfer\b|\bwire\b|\bted\b|\biban\b|\bswift\b|\bsepa\b/i, nome: 'Transferência bancária' },
    { re: /cheque|\bcheck\b/i, nome: 'Cheque' },
    { re: /din[eé]rio\s+virtual|net\s?banking|\binternet\s?banking\b|\bmb\b|\bnet\b/i, nome: 'Débito online' },
    { re: /conta\s+interna|\binternal\b|\binternal\s+transfer\b|\between\s+accounts\b/i, nome: 'Conta interna' },
    { re: /promo|b[oô]nus|bonus|cashback/i, nome: 'Bônus' },
    { re: /comiss[aã]o|\bcommission\b|\bfee\b|\btaxa\b/i, nome: 'Comissão' },
    { re: /corre[cç]|[ -]post/i, nome: 'Correios' },
  ];

  /**
   * Forma da movimentação, ou `'nao informada'`.
   *
   * Devolve sempre uma string: a coluna tem largura constante e o operador
   * não precisa ler a diferença entre "vazio" e "não sei".
   */
  export function formaMovimentacao(deal: Deal): string {
    const texto = `${deal.comment ?? ''} ${deal.movimentacao ?? ''}`.trim();
    if (!texto) return 'nao informada';
    for (const { re, nome } of FORMAS) {
      if (re.test(texto)) return nome;
    }
    return 'nao informada';
  }

/**
 * Resumo de uma pool de deals. Substitui as copias em History e Analytics.
 *
 * OPERACOES E MOVIMENTACOES SAO SEPARADAS
 * --------------------------------------
 * Somar deposito ao resultado e dizer "lucro" e a forma mais facil de mentir
 * sobre performance: o saldo subiu, mas nao por trading. `total`, wins, losses,
 * winRate e profitFactor passam a considerar SO operacoes — e as
 * movimentacoes vao para `movEntradas`/`movSaidas`, que sao numeros diferentes
 * e com nome proprio na tela.
 */
export function resumir(deals: readonly Deal[]): Resumo {
  const operacoes = deals.filter((d) => !ehMovimentacao(d));
  const pnls = operacoes.map(dealPnl);
  const movs = deals.filter(ehMovimentacao).map(dealPnl);
  const movEntradas = movs.filter((v) => v > 0).reduce((s, v) => s + v, 0);
  const movSaidas = Math.abs(movs.filter((v) => v < 0).reduce((s, v) => s + v, 0));
  const wins = pnls.filter((p) => p > 0).length;
  const losses = pnls.filter((p) => p < 0).length;
  const grossWin = pnls.filter((p) => p > 0).reduce((s, p) => s + p, 0);
  const grossLoss = Math.abs(pnls.filter((p) => p < 0).reduce((s, p) => s + p, 0));
  const closed = wins + losses;
  return {
    total: pnls.reduce((s, p) => s + p, 0),
    wins,
    losses,
    closed,
    qty: operacoes.length,
    movQtd: movs.length,
    movEntradas,
    movSaidas,
    // performanceMetrics.ts trabalha com TradeResult[]; aqui calculamos direto
    // sobre os PnLs ja extraidos para nao inventar um objeto de trade falso.
    winRate: closed > 0 ? (wins / closed) * 100 : 0,
    profitFactor: grossLoss > 0 ? grossWin / grossLoss : grossWin > 0 ? Infinity : 0,
    grossWin,
    grossLoss,
  };
}

const API = `${apiBase()}`;

/** Corretoras consultadas. MT5 e as cripto; o resto e derivado. */
const BROKERS = ['mt5', 'mexc', 'binance'] as const;

export interface HistoricoState {
  deals: Deal[];
  loading: boolean;
  erro: string;
  status: string;
  updatedAt: string;
  recarregar: () => void;
  /**
   * O MT5 respondeu SEM sessao viva? (06/10/2026)
   *
   * `true` significa que o dado esta vazio porque o terminal esta fechado, e
   * nao porque a conta nao tem operacao. Sao telas identicas e causas
   * diferentes: a tela de sucesso com zero linhas mandava o operador procurar
   * erro na conta, e o erro era um programa nao aberto.
   *
   * A tela usa isto para dizer o que fazer, em vez de repetir "nenhum registro".
   */
  desconectado: boolean;
}

export interface HistoricoOptions {
  broker?: string;
  symbol?: string;
  days?: string;
}

/**
 * Chave estavel de um deal, para deduplicar.
 *
 * POR QUE NAO E SO O `id`
 * ==========================
 * O `id` do gateway e o ticket do MT5, que e um contador POR CONTA. A tela
 * consulta varias corretoras ao mesmo tempo e junta tudo numa lista, entao o
 * mesmo ticket aparece em duas contas — e o React ainda avisaria, porque o
 * `id` repetido vira `key` repetida.
 *
 * A chave precisa do que torna o deal unico no conjunto: corretora, conta,
 * ticket, horario e lado. Sem o horario, um deal de abertura e o de fechamento
 * da mesma posicao (mesmo ticket, mesmo conta) continuariam colidindo.
 */
export function dealChave(deal: Deal, indice = 0): string {
  /*
    A chave precisa do que torna o deal unico DENTRO da conta.
    `realizedPnl` e `type` entram como alternativa a `side`, nao em vez dele:
    `side` vem das exchanges e `type` vem do MT5. Ler so `side` deixava toda
    operacao do MT5 com lado vazio, e o resultado eram colisoes falsas.
  */
  const partes = [
    deal.broker ?? '',
    String(deal.id ?? ''),
    deal.symbol ?? '',
    deal.executedAt ?? deal.close_time ?? '',
    String(deal.side ?? deal.type ?? ''),
    // `position_id` e `entry` faltavam aqui, e o dono viu operacao repetida na
    // tela. Sem eles:
    //   - abertura e fechamento da MESMA posicao (mesmo ticket, mesmo segundo)
    //     viravam um registro so;
    //   - duas operacoes que compartilham ticket e horario na mesma conta
    //     colidiam.
    // `position_id` ja existia no tipo `Deal` e era ignorado — e exatamente
    // para isso que ele existe.
    String(deal.position_id ?? ''),
    String(deal.entry ?? ''),
  ];
  const chave = partes.join('|');
  // O indice so entra quando o resto e vazio: sem ticket, horario e lado, dois
  // deals seriam indistinguiveis e um deles sumiria da tela. Quando existe
  // qualquer um desses campos, dois deals de verdade NUNCA tem a mesma chave.
  return chave === '|||||||' ? `sem-campos|${indice}` : chave;
}

/** Remove deals repetidos, preservando a ordem de chegada. */
export function deduplicar(deals: Deal[]): Deal[] {
  const vistas = new Set<string>();
  const saida: Deal[] = [];
  deals.forEach((deal, indice) => {
    const chave = dealChave(deal, indice);
    if (vistas.has(chave)) return;
    vistas.add(chave);
    saida.push(deal);
  });
  return saida;
}

/**
 * Hook de historico. Compartilhado por HistoryTab e AnalyticsTab para que as
 * duas abas leiam exatamente os mesmos deals.
 */
export function useHistorico(options: HistoricoOptions = {}): HistoricoState {
  const { broker = 'all', symbol = '', days = '90' } = options;
  const [deals, setDeals] = useState<Deal[]>([]);
  const [loading, setLoading] = useState(true);
  const [erro, setErro] = useState('');
  const [status, setStatus] = useState('Carregando historico real...');
  const [updatedAt, setUpdatedAt] = useState('--:--:--');
  const [tick, setTick] = useState(0);
  /*
    O TOKEN DA REQUISICAO, e nao um `busy` booleano.

    MEDIDO pelo dono: "o historico demora carregar". As duas causas foram
    medidas antes de corrigir, e a segunda e a que produzia o sintoma de espera.

    O que havia: `if (busyRef.current) return`. Uma requisicao em andamento
    CANCELAVA a proxima em silencio. O operador digita `BTCUSD` — sao seis
    eventos de teclado — e o primeiro dispara a busca; as cinco seguintes eram
    descartadas. O campo mostrava `BTCUSD`, a tabela mostrava os deals do filtro
    ANTERIOR, e o `status` dizia carregado. Sem erro, sem pendencia.

    O operador que ve isso digita de novo, esperando que a segunda vez funcione.
    A segunda funciona, porque a primeira terminou. E ele conclui que a tela e
    lenta — e fica esperando. O defeito nao era lentidao: era o filtro e a
    tabela discordando em silencio, que e o AGENTS.md 5.

    MEDIDO para descartar a rede como causa: `history_deals_get` responde em
    0,1 ms e `copy_rates` de 300 barras em 4,5 ms. O gateway nao era o gargalo.

    O token serve para DOIS Guards, e os dois sao necessarios:
      - `ultimoToken`: uma resposta atrasada nao sobrescreve a tela com o dado de
        um filtro que o operador JA TROCOU.
      - `emVoo`: evita disparar a mesma busca duas vezes quando nada mudou.
  */
  const tokenRef = useRef(0);
  const emVooRef = useRef(false);
  const [desconectado, setDesconectado] = useState(false);

  useEffect(() => {
    let active = true;
    tokenRef.current += 1;
    const meuToken = tokenRef.current;

    const carregar = async () => {
      /*
        `emVoo` e lido, e nao usado para CANCELAR: se a requisseo atual ainda
        corre, esta espera e dispara depois. Cancelar seria correto no papel e
        errado na pratica — o `fetch` do navegador nao aborta de verdade, e a
        tela ficaria com um estado de "carregando" que ninguem termina.
      */
      if (emVooRef.current) {
        await new Promise<void>((resolve) => {
          window.setTimeout(resolve, 60);
        });
        if (!active || meuToken !== tokenRef.current) return;
      }
      emVooRef.current = true;
      setErro('');
      const lista = broker === 'all' ? [...BROKERS] : [broker];

      const settled = await Promise.allSettled(
        lista.map(async (b) => {
          if (b !== 'mt5' && !symbol.trim()) {
            return { broker: b, deals: [] as Deal[], skipped: true };
          }
          const params = new URLSearchParams({
            broker: b,
            market: b === 'mt5' ? 'other' : 'crypto-spot',
            days,
          });
          if (symbol.trim()) params.set('symbol', symbol.trim());
          const resposta = await fetch(`${API}/api/universal/history?${params}`, {
            signal: AbortSignal.timeout(15000),
          });
          /*
            `connected` vem do gateway e diz se o MT5 TEM sessao viva.

            MEDIDO na conta 391773676: com o `terminal64` fechado,
            `history_deals_get` volta vazio — e `deals: []` e indistinguivel de
            "a conta nao tem operacoes nesse periodo". A tela mostrava "Nenhum
            registro no periodo", que e uma tela de SUCESSO com zero linhas, e o
            operador foi procurar erro na conta. Nao havia erro: havia um
            programa nao aberto.

            `connected: undefined` e o caso das EXCHANGES, que nao tem terminal.
            So o `false` explicito e desconexao — tratar `undefined` como
            desconectado colocaria "terminal fechado" numa tela Binance que
            funciona.
          */
          const corpo = (await resposta.json()) as {
            deals?: Deal[];
            error?: string;
            connected?: boolean;
          };
          if (!resposta.ok) throw new Error(corpo.error || `${b} indisponivel`);
          return { broker: b, deals: corpo.deals ?? [], connected: corpo.connected };
        }),
      );

      /*
        ESTE E O GUARD QUE IMPEDE A TABELA ANTIGA.

        Duas condicoes, e as duas importam:
          - `!active`: o efeito foi desfeito (o filtro mudou de novo).
          - `meuToken !== tokenRef.current`: OUTRA requisicao foi iniciada depois
            desta. Sem esta comparacao, a resposta lenta da busca antiga
            sobrescreveria a tela com o dado de um filtro que o operador JA
            TROCOU — e o sintoma seria uma tabela que muda sozinha depois de
            pronta.
      */
      if (!active || meuToken !== tokenRef.current) {
        if (meuToken === tokenRef.current) emVooRef.current = false;
        return;
      }

      const coletados: Array<{ broker: string; deals: Deal[] }> = [];
      const falhas: string[] = [];
      let algumDesconectado = false;
      settled.forEach((resultado, indice) => {
        if (resultado.status === 'fulfilled') {
          if (!resultado.value.skipped) {
            coletados.push({ broker: resultado.value.broker, deals: resultado.value.deals });
            if (resultado.value.connected === false) algumDesconectado = true;
          }
        } else {
          const motivo = resultado.reason;
          falhas.push(
            `${lista[indice]}: ${motivo instanceof Error ? motivo.message : 'indisponivel'}`,
          );
        }
      });

      const plano = coletados.flatMap(({ broker: b, deals: lista }) =>
        lista.map((deal) => ({ ...deal, broker: deal.broker ?? b })),
      );
      plano.sort((a, b) => dealDate(b).localeCompare(dealDate(a)));
      // Deduplica DEPOIS do sort: a ordem vem de varias corretoras, e o mesmo
      // ticket pode aparecer em contas diferentes. Sem esta linha o operador
      // via a mesma operacao duas vezes na tabela.
      setDeals(deduplicar(plano));

      const contagem = coletados.map((c) => `${c.broker}: ${c.deals.length}`).join('  |  ');
      /*
        O STATUS DIZ SE LEU, E SE NAO LEU.

        Sao duas situacoes que produzem a MESMA tela — zero linhas — e que o
        operador precisa distinguir: a conta nao tem operacao no periodo, ou o
        MT5 esta fechado. A segunda e a que o dono pediu: o app nao pode
        depender do MT5 ligado sem DIZER que depende.

        Por que o texto e do `status` e nao de um `<p>` na tela: o `status` ja
        e o que a aba mostra e o que o leitor de tela anuncia, e um texto em
        dois lugares e dois textos que divergem.
      */
      setDesconectado(algumDesconectado);
      const motivoDesconectado = algumDesconectado
        ? 'MT5 sem sessao: abra o MetaTrader 5 e faca login para ler o historico'
        : '';
      setStatus(
        falhas.length
          ? `${contagem || 'sem fontes'}  |  falhas parciais: ${falhas.join(' | ')}`
          : `${contagem || 'sem fontes'}${motivoDesconectado ? `  |  ${motivoDesconectado}` : ''}`,
      );
      setErro(coletados.length ? '' : falhas.join(' | '));
      setUpdatedAt(new Date().toLocaleTimeString('pt-BR'));
      setLoading(false);
      emVooRef.current = false;
    };

    void carregar();
    return () => {
      active = false;
    };
  }, [broker, symbol, days, tick]);

  /*
    `recarregar` anula o token de proposito: e o botao "Atualizar", e ele
    significa "leia de novo, agora", vencendo qualquer requisicao em voo. Sem
    isso o clique pareceria nao funcionar enquanto a busca antiga estivesse no
    caminho — e o botao que parece funcionar e nao funciona e o defeito que o
    dono reportou no botao EMA.
  */
  const recarregar = useCallback(() => {
    tokenRef.current += 1;
    emVooRef.current = false;
    setLoading(true);
    setTick((n) => n + 1);
  }, []);

  return useMemo(
    () => ({ deals, loading, erro, status, updatedAt, recarregar, desconectado }),
    [deals, loading, erro, status, updatedAt, recarregar, desconectado],
  );
}
