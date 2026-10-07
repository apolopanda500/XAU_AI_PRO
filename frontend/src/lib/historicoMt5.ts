import { dealPnl, ehMovimentacao, formaMovimentacao, toNumber, type Deal } from './historico';

/*
  O HISTORICO NO FORMATO MT5 — MEDIDO NA CAPTURA DO DONO (05/10/2026)
  ======================================================================
  A captura e a aba Historico do MT5 terminal, conta 391773676
  (XMGlobal-MT5 14), com o deal 24503922 aberto. As 4 linhas, literais:

      2026.10.04 21:53:54   —   260002613  balance  CD-AST-PIC 265376085       5,52
      2026.10.04 21:53:54   —   260002614  balance  EXP05-AST-PIC 265376085      0,10
      2026.10.04 21:53:55   —   260002615  credit   Credit-In-100%-$100-NewClients  5,62
      2026.10.05 01:46:43   btcusd  24503922  buy   0,01  86394,85  86594,50
                             2026.10.05 02:12:25  86585,35   2,01   0,23%

      Lucro: 2,01  Credito: 5,62  Recarregar: 5,62  Retirada: 0,00  Saldo: 13,25

  O QUE A CAPTURA CORRIGE, E O QUE O CODIGO ANTES DIZIA ERRADO
  =============================================================
  Este modulo antes afirmava, em comentario, que "o MT5 mostra entrada e saida
  de uma posicao em DUAS linhas da MESMA tabela". NAO E VERDADE. A captura
  mostra UMA LINHA por operacao, com a entrada e o fechamento lado a lado:

      Horario | Ativo | Bilhete | Tipo | Volume | Preco | S/L | T/P
             | Horario | Preco | Lucro | Mudanca

  Os dois primeiros sao a ABERTURA (01:46:43, 86394,85) e os dois seguintes o
  FECHAMENTO (02:12:25, 86585,35). Uma linha. E era exatamente o que o dono
  tinha pedido antes — "remover um pouco de dupicates" — que este modulo
  tinha trazido de volta ao dizer que o MT5 fazia assim.

  Este modulo tambem afirmava que "Credito e Recarregar sao numeros DIFERENTES
  de proposito". Na captura os dois sao 5,62 — o mesmo numero — porque os dois
  deals `balance` (5,52 e 0,10) SOMEM a 5,62. Ver `resumoMt5`.
*/

/** Os tipos que o MT5 grava como movimentacao de saldo. */
const TIPOS_MOVIMENTACAO = new Set([
  'BALANCE', 'CREDIT', 'CHARGE', 'CORRECTION', 'BONUS', 'COMMISSION', 'FEE',
]);

export type LinhaMt5 = {
  chave: string;
  /** `IN` = abertura, `OUT` = fechamento. Vazio nas movimentacoes. */
  entrada: '' | 'IN' | 'OUT';
  /** `balance`/`credit`/... das movimentacoes; `buy`/`sell` das operacoes. */
  tipo: string;
  /** Rotulo legivel do tipo, como o MT5 escreve. */
  rotuloTipo: string;
  ativo: string;
  /** Ticket do deal. Na captura da operacao e o ticket do FECHAMENTO. */
  bilhete: string;
  /** Comentario da corretora. Vem DEPOIS do bilhete, como no MT5. */
  comentario: string;
  /**
   * A FORMA do deposito ou do saque: "PIX", "Cartao", "Transferencia
   * bancaria", ou `nao informada`.
   *
   * MEDIDO: o deal de movimentacao NAO tem campo de metodo. O que existe e o
   * `comment` em texto livre, e a forma e lida dele por `formaMovimentacao`.
   * Vazio nas operacoes — uma compra nao tem forma de deposito.
   */
  forma: string;
  /** Horario da ABERTURA. */
  horario: string;
  /**
   * Volume da operacao, ou `null`.
   *
   * NUMERO, NAO TEXTO. A primeira versao deste modulo devolvia string com
   * `toFixed`, e a tela escrevia `86394.85` enquanto o MT5 — e o resto do app,
   * que e pt-BR — escreve `86394,85`. Locale nao e decisao de camada de dado.
   * `null` e ausencia, e zero e um numero: as duas frases nao podem virar a
   * mesma na tela.
   */
  volume: number | null;
  /** Preco de abertura, ou `null`. Numero pelo mesmo motivo de `volume`. */
  preco: number | null;
  /** Stop loss registrado, ou `null`. */
  sl: number | null;
  /** Take profit registrado, ou `null`. */
  tp: number | null;
  /**
   * Horario do FECHAMENTO, no segundo par de colunas da captura.
   *
   * Vazio enquanto a posicao esta aberta: a captura escreve `2026.10.05 02:12:25`
   * na linha que ja fechou. Numa posicao aberta, este e o lugar onde a celula
   * fica VAZIA — e vazia e melhor que repetir a hora de abertura, que diria
   * que a posicao ja tinha fechado.
   */
  horarioFim: string;
  /** Preco do fechamento, ou `null`. Vazio pelo mesmo motivo de `horarioFim`. */
  precoFim: number | null;
  /**
   * Resultado da operacao. Zero/vazio nas movimentacoes.
   *
   * `null` e NAO 0: uma movimentacao de saldo nao tem resultado — o dinheiro
   * entrou. Escrever 0,00 diria que a corretora mediu uma performance e nao
   * mediu nada (AGENTS.md 10).
   */
  lucro: number | null;
  /**
   * Variacao percentual do preco, como a ultima coluna da captura.
   *
   * VAZIA quando o payload nao traz `open_price`. Vazio e melhor que "0,00%": a
   * celula vazia diz que nao ha dado, e o zero diria que o preco nao se moveu.
   */
  mudanca: string;
  /** true para `balance`/`credit`/... — dinheiro que entrou ou saiu. */
  movimentacao: boolean;
};

/** O que o MT5 escreve em `Tipo`, por codigo numerico e por nome. */
const ROTULOS_TIPO: Record<string, string> = {
  BUY: 'Compra',
  SELL: 'Venda',
  BUY_IN: 'Compra (entrada)',
  SELL_OUT: 'Venda (saida)',
  BALANCE: 'Saldo',
  CREDIT: 'Credito',
  CHARGE: 'Cobranca',
  CORRECTION: 'Correcao',
  BONUS: 'Bonus',
  COMMISSION: 'Comissao',
  FEE: 'Taxa',
};

/** Numero -> nome, para quando o gateway manda o enum do MT5. */
const TIPOS_POR_CODIGO: Record<number, string> = {
  0: 'BUY',
  1: 'SELL',
  2: 'BALANCE',
  3: 'CREDIT',
  4: 'CHARGE',
  5: 'CORRECTION',
  6: 'BONUS',
  7: 'COMMISSION',
};

export function nomeDoTipo(tipo: string | number | undefined): string {
  if (tipo === undefined || tipo === null || tipo === '') return '';
  if (typeof tipo === 'number') return TIPOS_POR_CODIGO[tipo] ?? '';
  const bruto = String(tipo).toUpperCase();
  return bruto;
}

/**
 * O tipo da linha: o nome estruturado quando existe, o derivado do `categoria`
 * quando nao.
 *
 * MEDIDO na captura (05/10/2026): a conta 391773676 devolveu `BALANCE`,
 * `BALANCE` e `CREDIT`. Sem ler o campo, tudo aparecia como "SELL" — e o
 * operador lia "vendi" num deposito.
 */
export function tipoDaLinha(deal: Deal): string {
  const nome = nomeDoTipo(deal.type);
  if (nome) return nome;
  if (ehMovimentacao(deal)) return 'BALANCE';
  const side = String(deal.side ?? '').toUpperCase();
  return side === 'BUY' ? 'BUY' : side === 'SELL' ? 'SELL' : '';
}

export function ehLinhaMovimentacao(deal: Deal): boolean {
  const t = tipoDaLinha(deal);
  return TIPOS_MOVIMENTACAO.has(t) || (!t && ehMovimentacao(deal));
}

/** `IN` / `OUT` normalizado. Vazio quando o deal nao diz. */
function entradaDe(deal: Deal): '' | 'IN' | 'OUT' {
  const bruto = String(deal.entry ?? '').toUpperCase();
  if (bruto === 'IN' || bruto === 'OUT') return bruto;
  // Sem `entry`, um deal que tem simbolo e volume e abertura ou fechamento? O
  // MT5 sempre manda. Ausente vira vazio, que e melhor que adivinhar.
  return '';
}

/**
 * Lê um preço de um campo do deal, aceitando os nomes que as rotas usam.
 *
 * A rota MT5 manda `sl`/`tp`; a universal manda `sl_price`/`tp_price`.
 * Considerar só um deles deixaria a coluna vazia na rota que usa o outro nome —
 * e vazia aqui significa "a mercado", que é uma leitura errada, não uma ausência.
 *
 * `null` e NÃO 0: zero é um preço válido em alguns pares e significaria "stop
 * loss em zero", que é nonsense. Ausência precisa ser ausência.
 */
function precoDoDeal(deal: Deal, ...nomes: string[]): number | null {
  for (const nome of nomes) {
    const bruto = (deal as unknown as Record<string, unknown>)[nome];
    if (bruto === null || bruto === undefined || bruto === '') continue;
    const n = toNumber(bruto);
    if (Number.isFinite(n) && n !== 0) return n;
  }
  return null;
}

/**
 * Uma linha por operacao, como a captura do MT5.
 *
 * ABERTURA E FECHAMENTO NA MESMA LINHA
 * =====================================
 * MEDIDO na captura: a operacao 24503922 e UMA linha com
 * `01:46:43 | btcusd | 24503922 | buy | 0,01 | 86394,85 | 86594,50` e, depois,
 * `2026.10.05 02:12:25 | 86585,35 | 2,01 | 0,23%`. Sao as duas pontas na MESMA
 * linha. Duas linhas fariam o operador ler duas operacoes onde houve uma —
 * que e o duplicado que o dono pediu para remover.
 *
 * A REGRA DE AGRUPAMENTO E A POSICAO
 * ----------------------------------
 *   - `position_id` presente e a chave real: e o identificador que o MT5 da
 *     para a posicao e que sobrevive a abertura e ao fechamento.
 *   - sem `position_id`, agrupa por `corretora|ativo` no PRIMEIRO deal livre.
 *     Duas ordens realmente distintas no mesmo par continuam em linhas
 *     separadas — agrupar tudo por par esconderia operacoes de verdade.
 *
 * O QUE A LINHA CONSERVA DO PRIMEIRO DEAL E DO ULTIMO
 * ---------------------------------------------------
 * A coluna `Horario`/`Preco` e da ABERTURA e o `Bilhete` e do FECHAMENTO.
 * MEDIDO: na captura, `Bilhete` e 24503922, que e o ticket do deal de saida —
 * a entrada tem outro. E `Lucro` e a SOMA dos deals do grupo, que e o
 * resultado da operacao.
 *
 * Movimentacoes de saldo NAO entram no agrupamento: sao uma linha cada, com
 * as colunas de operacao vazias. Um deposito nao e uma operacao de mercado, e
 * soma-lo ao lucro infla o resultado (AGENTS.md 10).
 */
export function linhasMt5(deals: readonly Deal[]): LinhaMt5[] {
  const grupos = new Map<string, Deal[]>();
  const ordem: string[] = [];
  /** Quantos deals cada grupo aberto ja recebeu. */
  const tamanho = new Map<string, number>();

  deals.forEach((deal) => {
    if (ehLinhaMovimentacao(deal)) {
      // Movimentacao: uma linha, sem agrupar. Duas recargas no mesmo segundo
      // sao DUAS recargas, e agrupar por `corretora|ativo` fundiria o deposito
      // de 5,52 com o bonus de 0,10 — que a captura mostra em linhas separadas.
      const chave = `mov|${ordem.length}`;
      ordem.push(chave);
      grupos.set(chave, [deal]);
      tamanho.set(chave, 1);
      return;
    }

    const idPosicao = String(deal.position_id ?? '').trim();
    const chave = idPosicao
      ? `pos|${deal.broker ?? ''}#${idPosicao}`
      : null;
    if (chave) {
      if (!grupos.has(chave)) ordem.push(chave);
      grupos.set(chave, [...(grupos.get(chave) ?? []), deal]);
      tamanho.set(chave, (grupos.get(chave) ?? []).length);
      return;
    }

    // Sem `position_id`: procura um grupo ABERTO do mesmo par (que tem exatamente
    // 1 deal, a abertura). Grupo ja fechado nao recebe mais nada.
    const par = `${deal.broker ?? ''}|${deal.symbol ?? ''}`;
    const candidato = ordem.find(
      (c) => c.startsWith(`ab|${par}`) && (tamanho.get(c) ?? 0) === 1,
    );
    if (candidato) {
      grupos.set(candidato, [...(grupos.get(candidato) ?? []), deal]);
      tamanho.set(candidato, 2);
      return;
    }
    // Nenhum grupo aberto do par: abre um novo. Duas ordens realmente distintas
    // no mesmo par continuam em linhas separadas.
    const nova = `ab|${par}#${ordem.length}`;
    ordem.push(nova);
    grupos.set(nova, [deal]);
    tamanho.set(nova, 1);
  });

  return ordem.map((chave) => {
    const lista = grupos.get(chave) ?? [];
    const primeiro = lista[0];
    const ultimo = lista[lista.length - 1];
    const mov = ehLinhaMovimentacao(primeiro);

    /*
      LUCRO E MUDANCA SO EXISTEM EM OPERACAO.
      ---------------------------------------
      Numa movimentacao de saldo nao ha preco de entrada, nao ha preco de saida e
      nao ha resultado: o dinheiro entrou. Escrever "0,00" nela seria inventar
      medida para um registro que nao a tem — e o resumo somaria dinheiro que
      entrou como se fosse resultado.

      `mudanca` e a variacao percentual do preco. Para sair, o MT5 manda o preco
      de entrada da posicao. Sem esse campo no payload, a celula fica VAZIA — e
      vazia e melhor que "0,00%", que diria "o preco nao se moveu" para um
      registro que nao tem como saber.
    */
    const volume = toNumber(primeiro.volume ?? primeiro.quantity);
    const preco = toNumber(primeiro.price);
    const precoAbertura = toNumber(ultimo.open_price) || preco;

    /*
      O FECHAMENTO SO EXISTE COM UM DEAL DE SAIDA DISTINTO.
      ---------------------------------------------------
      Com um deal so no grupo, `ultimo === primeiro` e a guarda abaixo passaria:
      a hora da ABERTURA apareceria na coluna de fechamento, e o operador leria
      que a posicao fechou no minuto em que abriu. `entradaDe` sozinho nao
      protege, porque o unico deal e `IN`. A guarda e `lista.length > 1` E o
      ultimo deal ser `OUT` — os dois.
    */
    const saida = !mov && lista.length > 1 && entradaDe(ultimo) === 'OUT' ? ultimo : null;

    /*
      S/L E T/P: O PRIMEIRO DEAL DO GRUPO QUE OS DECLARAR.
      ---------------------------------------------------
      O MT5 grava o stop pedido na abertura e o repete no fechamento; e uma
      rota nova pode mandar em um só dos dois. Ler so do primeiro deal deixaria
      a coluna vazia na rota que manda no segundo — e vazia aqui significa "a
      mercado", que e uma LEITURA ERRADA e nao uma ausencia. Zero e ignorado:
      0 e um preco valido em alguns pares e nao existe stop no zero.
    */
    const slPreco = lista.reduce<number | null>(
      (acc, d) => acc ?? precoDoDeal(d, 'sl', 'sl_price', 'stop_loss'),
      null,
    );
    const tpPreco = lista.reduce<number | null>(
      (acc, d) => acc ?? precoDoDeal(d, 'tp', 'tp_price', 'take_profit'),
      null,
    );

    const linha: LinhaMt5 = {
      chave,
      entrada: entradaDe(primeiro),
      /*
        O TIPO E O LADO DA ABERTURA, e nao do fechamento.
        --------------------------------------------------
        MEDIDO na captura: a operacao 24503922 tem `buy` na coluna Tipo, e o
        deal de fechamento e `SELL`. A linha comeca na abertura — horario,
        volume, preco e S/L sao dela — e por isso o Tipo e dela tambem. Ler o
        do fechamento escreveria "venda" numa operacao que foi COMPRA, que e o
        inverso do duplicado que esta tela ja corrigiu.
      */
      tipo: tipoDaLinha(primeiro),
      rotuloTipo: ROTULOS_TIPO[tipoDaLinha(primeiro)] ?? '',
      ativo: String(mov ? '' : primeiro.symbol ?? '').trim(),
      // MEDIDO: na captura, `Bilhete` e o ticket do FECHAMENTO.
      bilhete: String(ultimo.ticket ?? ultimo.position_id ?? primeiro.ticket ?? '').trim(),
      comentario: String(ultimo.comment ?? primeiro.comment ?? '').trim(),
      forma: mov ? formaMovimentacao(ultimo) : '',
      horario: String(primeiro.executedAt ?? primeiro.close_time ?? ''),
      preco: mov || !preco ? null : preco,
      volume: mov || !volume ? null : volume,
      sl: mov ? null : slPreco,
      tp: mov ? null : tpPreco,
      /*
        HORARIO E PRECO DO FECHAMENTO.
        -------------------------------
        Vem do deal de SAIDA, e nao da entrada: a entrada nao conhece quando a
        posicao fechou. Sem deal de saida no grupo — posicao aberta, ou filtro
        que cortou o fechamento — os dois campos ficam VAZIOS, e a celula vazia
        diz que a posicao nao tem fechamento CONHECIDO. Repetir a hora de
        abertura ali diria que ela fechou no minuto em que abriu.
      */
      horarioFim: saida ? String(saida.executedAt ?? '') : '',
      precoFim: saida && toNumber(saida.price) ? toNumber(saida.price) : null,
      lucro: mov ? null : lista.reduce((acc, d) => acc + dealPnl(d), 0),
      mudanca:
        !mov && preco > 0 && precoAbertura > 0
          ? `${(((toNumber(ultimo.price) - precoAbertura) / precoAbertura) * 100).toFixed(2)}%`
          : '',
      movimentacao: mov,
    };
    return linha;
  });
}

export type ResumoMt5 = {
  /** Resultado das OPERACOES. Nunca inclui entrada ou saida de saldo. */
  lucro: number;
  /**
   * `credit` e `bonus`: credito concedido pela corretora.
   *
   * MEDIDO na captura: o deal `credit` de 5,62 (comentario
   * `Credit-In-100%-$100-NewClients`) e o que a XM concedeu. Os dois `balance`
   * (5,52 e 0,10) sao deposito do operador e vao para `recarregar`.
   */
  credito: number;
  /**
   * `balance` e `correction`: deposito do operador na conta.
   *
   * MEDIDO na captura: 5,52 (`CD-AST-PIC 265376085`) + 0,10 (`EXP05-AST-PIC
   * 265376085`) = 5,62 — que e exatamente o "Recarregar: 5,62" que o MT5
   * escreve. Negative vira `retirar`.
   */
  recarregar: number;
  /** Saida de saldo da conta: saque. Negativo, como no MT5. */
  retirar: number;
  /**
   * Comissao, taxa e cobranca da corretora.
   *
   * SEPARADO, e nao em `retirar` nem em `lucro`, por dois motivos medidos:
   *
   * 1. "Retirada" significa saque. Comissao nao e dinheiro que o operador sacou;
   *    soma-la ali diz ao operador que ele retirou da conta o que ele pagou de
   *    taxa — e muda o que ele le da conta.
   * 2. Somar em `lucro` pode CONTA DUAS VEZES: o deal de saida da posicao ja
   *    traz `commission`, e o deal `COMMISSION` avulso traz o mesmo valor. A
   *    soma viraria o dobro, e nenhum dos dois numeros viria errado sozinho.
   *
   * A linha de resumo da captura NAO tem coluna para isso, e por isso este campo
   * nao vai para a tela. Fica calculado e testado para quando existir onde
   * mostrar — um numero sem consumidor e um controle sem leitura (AGENTS.md 9).
   */
  custos: number;
  /**
   * Saldo informado pela corretora, ou `null`.
   *
   * NAO SAI DO HISTORICO. MEDIDO na captura: `Saldo: 13,25` e o Capital da
   * conta (o painel da XM mostra Saldo $7,63 e Capital $13,25), e a soma das
   * movimentacoes do dia da 11,24. Somar os deals e chamar de saldo seria
   * inventar o que a corretora disse.
   */
  saldo: number | null;
};

/**
 * O RESUMO COM OS ROTULOS DA CAPTURA.
 *
 * MEDIDO na conta 391773676 (05/10/2026), com a captura do MT5 do lado:
 *
 *     Lucro: 2,01  Credito: 5,62  Recarregar: 5,62  Retirada: 0,00  Saldo: 13,25
 *
 * `credito` e `recarregar` sao numeros DIFERENTES de proposito, ainda que na
 * captura coincidam em 5,62: `credit` e o que a corretora concedeu e `balance` e
 * o que o operador depositou. Somar os dois perde a distincao entre "a XM me
 * deu credito" e "eu depositei" — e com outros valores os dois numeros
 * divergem, que e o que o operador precisa ver.
 */
export function resumoMt5(deals: readonly Deal[], saldoAtual?: number | null): ResumoMt5 {
  let credito = 0;
  let recarregar = 0;
  let retirar = 0;
  let custos = 0;
  let lucro = 0;

  for (const deal of deals) {
    const t = tipoDaLinha(deal);
    const valor = dealPnl(deal);

    // Comissao, taxa e cobranca: custo da corretora. Nem saldo, nem saque,
    // nem resultado (ver `custos`).
    if (t === 'COMMISSION' || t === 'FEE' || t === 'CHARGE') {
      custos += valor;
      continue;
    }

    if (ehLinhaMovimentacao(deal)) {
      if (t === 'CREDIT' || t === 'BONUS') credito += valor;
      else if (t === 'BALANCE' || t === 'CORRECTION') {
        if (valor < 0) retirar += valor;
        else recarregar += valor;
      } else if (valor < 0) retirar += valor;
    } else {
      lucro += valor;
    }
  }

  return {
    lucro,
    credito,
    recarregar,
    retirar,
    custos,
    saldo: typeof saldoAtual === 'number' && Number.isFinite(saldoAtual) ? saldoAtual : null,
  };
}