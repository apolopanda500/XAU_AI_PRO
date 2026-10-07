// Histórico no formato MT5: UMA tabela, com a linha de resumo embaixo.
//
// MEDIDO NA CAPTURA DO DONO (05/10/2026)
// =========================================
// Aba Histórico do MT5 terminal, conta 391773676 (XMGlobal-MT5 14). As 4
// linhas, literais:
//
//     2026.10.04 21:53:54   —   260002613  balance  CD-AST-PIC 265376085           5,52
//     2026.10.04 21:53:54   —   260002614  balance  EXP05-AST-PIC 265376085          0,10
//     2026.10.04 21:53:55   —   260002615  credit   Credit-In-100%-$100-NewClients  5,62
//     2026.10.05 01:46:43  btcusd 24503922 buy  0,01 86394,85 86594,50
//                            2026.10.05 02:12:25 86585,35  2,01  0,23%
//
//     Lucro: 2,01  Crédito: 5,62  Recarregar: 5,62  Retirada: 0,00  Saldo: 13,25
//
// O QUE MUDOU NESTA TELA, E POR QUÊ
// ================================
// A tela tinha DUAS tabelas — "Operações" e "Recargas e saques" — e MEDIDO na
// conta 391773676 a de operações mostrava as três movimentações de saldo como
// se fossem operações: `CREDIT` e `BALANCE` com `—` no ativo, `sem` em S/L e
// T/P, e o resultado de um depósito na coluna Resultado. Três das cinco linhas.
//
// Duas tabelas obrigavam o operador a olhar duas janelas para saber "o que
// aconteceu hoje", e a de operações ainda lia dinheiro que ENTROU como
// resultado. Na captura do MT5 é UMA tabela e o que separa operação de
// movimentação é o TIPO — `balance` e `credit` são linhas da mesma tabela com
// campos de operação vazios.
//
// A REGRA DE DADOS CONTINUA VALENDO, E É POR ISSO QUE O TIPO SEPARA
// =====================================================================
// `totalLucro` em `resumoMt5` só soma operação. Somar entrada de saldo em lucro
// é proibido (AGENTS.md 10), e a captura mostra `Lucro: 2,01` — que é a
// operação, não os 11,24 que entraram.
//
// COMPATIBILIDADE COM OUTRAS CORRETORAS
// =====================================
// `all` faz o hook consultar MT5 e as exchanges em paralelo e juntar o que
// respondeu. Bybit e OKX entraram na lista: o backend já tem cliente para os
// dois. Para exchange, o símbolo é obrigatório — não há como listar histórico
// sem saber o par.
import { useMemo, useState } from 'react';
import { fmtNum, fmtSigned } from '../../lib/format';
import { useHistorico } from '../../lib/historico';
import { linhasMt5, resumoMt5 } from '../../lib/historicoMt5';
import '../../theme/history.css';
// Carregado por último: sobrescreve as celulas de 40px do history.css.
import '../../theme/history-grid.css';

const BROKERS: Array<{ value: string; label: string }> = [
  { value: 'all', label: 'Todas' },
  { value: 'mt5', label: 'MT5' },
  { value: 'binance', label: 'Binance' },
  { value: 'mexc', label: 'MEXC' },
  { value: 'bybit', label: 'Bybit' },
  { value: 'okx', label: 'OKX' },
];

const limits: Record<string, number> = {
  '1': 100,
  '7': 200,
  '15': 300,
  '30': 500,
  '90': 500,
  '365': 500,
  '0': 500,
};

/** Só a HORA, como a captura: `01:46:43`. A data fica na faixa de dia. */
const hora = (v?: string) => {
  if (!v) return '';
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? '' : d.toLocaleTimeString('pt-BR');
};

/** Data e hora completas, para o `title` de quem precisa do valor inteiro. */
const stamp = (v?: string) => {
  if (!v) return '';
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? v : d.toLocaleString('pt-BR');
};

/**
 * ESTILO MT5: SEPARADOR DE DIA (05/10/2026)
 * =========================================
 * O histórico vem agrupado por dia, com uma faixa de data atravessando a
 * tabela. Vinte operações do mesmo dia ocupam uma faixa e vinte linhas.
 *
 * Ganho concreto, além do visual: o operador confere o dia antes de conferir a
 * operação. "Quantas operações hoje?" é a primeira pergunta do dia, e ela fica
 * respondida pelo cabeçalho em vez de exigir varredura da coluna de data.
 *
 * A ORDEM É PRESERVADA. Não se reordena por data: o histórico vem na ordem que
 * o gateway devolveu (mais recente primeiro) e trocar essa ordem mudaria o que
 * "primeira linha" significa para quem lê. Aqui só se INSERE um separador
 * quando o dia muda — e a troca de dia é detectada pela data já convertida no
 * fuso local, não por comparação da string crua, porque `data` pode vir em ISO
 * UTC e virar o dia anterior na conversão.
 */
export interface GrupoDia<T> {
  /** `YYYY-MM-DD` no fuso local, usado como chave de agrupamento. */
  chave: string;
  /** Rótulo pronto para a faixa: "hoje", "ontem" ou "12/05/2026, terça-feira". */
  rotulo: string;
  linhas: T[];
}

function chaveDia(valor: string): string {
  if (!valor) return 'sem-data';
  const d = new Date(valor);
  if (Number.isNaN(d.getTime())) return 'sem-data';
  const mes = String(d.getMonth() + 1).padStart(2, '0');
  const dia = String(d.getDate()).padStart(2, '0');
  return `${d.getFullYear()}-${mes}-${dia}`;
}

function rotuloDia(chave: string): string {
  const hoje = new Date();
  const ontem = new Date();
  ontem.setDate(ontem.getDate() - 1);
  if (chave === chaveDia(hoje.toISOString())) return 'Hoje';
  if (chave === chaveDia(ontem.toISOString())) return 'Ontem';

  const partes = chave.split('-');
  if (partes.length !== 3) return chave;
  const d = new Date(Number(partes[0]), Number(partes[1]) - 1, Number(partes[2]));
  if (Number.isNaN(d.getTime())) return chave;
  const data = d.toLocaleDateString('pt-BR');
  const dia = d.toLocaleDateString('pt-BR', { weekday: 'long' });
  return `${data}, ${dia}`;
}

/** Agrupa por dia preservando a ordem de entrada. */
export function agruparPorDia<T>(linhas: readonly T[], dataDe: (linha: T) => string): GrupoDia<T>[] {
  const grupos: GrupoDia<T>[] = [];
  let atual: GrupoDia<T> | undefined;
  for (const linha of linhas) {
    const chave = chaveDia(dataDe(linha));
    if (!atual || atual.chave !== chave) {
      atual = { chave, rotulo: rotuloDia(chave), linhas: [] };
      grupos.push(atual);
    }
    atual.linhas.push(linha);
  }
  return grupos;
}

/** `Lucro: 2,01` — o número como o MT5 escreve, com o sinal. */
const money = (v: number) => fmtSigned(v, 2);

/**
 * Preço de mercado em pt-BR, com as casas que o par pede.
 *
 * POR QUE A CASA VARIA POR COLUNA, E NÃO É PREFERÊNCIA
 * ======================================================
 * A conta real tem contratos com casas distintas: `86394,85` em BTCUSD e
 * `0,00001` em Forex. Duas casas em tudo arredonda o preço de Forex para zero
 * e esconde o dígito do BTC — e o valor que o operador confere é justamente o
 * último. A regra abaixo é do mercado, não do gosto (AGENTS.md 9).
 *
 * `null` devolve VAZIO, e não `0,00`: uma movimentação de saldo não tem preço,
 * e um `--` diria "o gateway não mandou". O que se lê na tela é ausência.
 */
const preco = (v: number | null): string => {
  if (v === null) return '';
  return fmtNum(v, v >= 1000 ? 2 : v >= 1 ? 4 : 6);
};

/** Volume: abaixo de 1 são frações de lote, e precisam de mais casas. */
const volume = (v: number | null): string => {
  if (v === null) return '';
  return fmtNum(v, v >= 1 ? 2 : 4);
};

/** As 5 colunas do rodapé, na ordem da captura. */
const ROTULOS_RESUMO = ['Lucro', 'Credito', 'Recarregar', 'Retirada', 'Saldo'] as const;

/** Quantas colunas a tabela tem. O rodapé precisa do mesmo `colSpan`. */
const COLUNAS = 13;

export default function HistoryTab() {
  const [broker, setBroker] = useState('all');
  const [symbol, setSymbol] = useState('');
  /**
   * O PERÍODO PADRÃO (05/10/2026)
   * ============================
   * MEDIDO na conta 391773676: existem 5 deals, TODOS de 04/10 — uma operação
   * BTCUSD e três movimentações de saldo. Nada de 05/10.
   *
   * Com o padrão "Hoje", a tabela abria vazia e o dono leu isso como "as
   * recargas não carregam": a recarga estava no MT5, no gateway e no histórico
   * — só que fora da janela que a tela pedia.
   *
   * Por que 30 dias e não "Tudo": a rota universal tem limite de 3650 dias e o
   * volume real cresce com a janela. 30 dias mostra a recarga, as operações da
   * semana e a movimentação recente sem despejar anos na tela. O seletor
   * continua com "Tudo" para quem quiser o acumulado.
   */
  const [days, setDays] = useState('30');
  const {
    deals,
    erro: error,
    status,
    updatedAt,
    recarregar: load,
    loading,
    desconectado,
  } = useHistorico({ broker, symbol, days });

  const rows = useMemo(() => deals.slice(0, limits[days] ?? 500), [deals, days]);

  /*
    AS LINHAS E O RESUMO, DO MESMO CONJUNTO.
    ----------------------------------------
    As duas coisas leem `rows`. Um resumo calculado de outro conjunto é um
    número que pode divergir da tabela logo abaixo dele sem ninguém ver — e é
    isso que o operador confia.
  */
  const linhas = useMemo(() => linhasMt5(rows), [rows]);
  const resumo = useMemo(() => resumoMt5(rows), [rows]);

  /* Agrupamento por dia, como a aba Histórico do MT5. */
  const grupos = useMemo(
    () => agruparPorDia(linhas, (linha) => linha.horario),
    [linhas],
  );

  /*
    `Saldo` NAO VEM DO HISTORICO — E ISTO E O MAIS IMPORTANTE DA LINHA.
    ===================================================================
    MEDIDO na captura: `Saldo: 13,25` e o CAPITAL da conta — o painel da XM
    mostra Saldo $7,63 e Capital $13,25, e a soma das movimentacoes do dia da
    11,24. Nenhum dos tres e o mesmo numero, e o historico nao tem como saber
    qual deles o operador quer.

    Por isso a coluna fica VAZIA, e nao "a soma das movimentacoes". Somar os
    deals e escrever "Saldo" seria mostrar um numero inventado com o nome de
    um numero que a corretora mede — e o operador nao tem como saber qual dos
    dois leu.

    Para ter saldo de verdade, a rota `/api/account` traz `balance` e `equity`
    da conta MT5. Ela nao entra nesta tela porque o filtro e por CORRETORA e
    POR PERIODO: um saldo de conta nao muda com o filtro, e mostrar o saldo da
    conta junto com o historico de um filtro mudaria o que o operador le. A
    Carteira mostra o saldo de cada corretora, que e o lugar dele.
  */

  const exportCsv = () => {
    // O CSV mantem as DUAS naturezas lado a lado: sem isso, quem abre a
    // planilha volta a somar deposito como se fosse lucro — o mesmo erro que a
    // tela deixou de ter.
    const cols = [
      'Natureza',
      'Bilhete',
      'Ativo',
      'Tipo',
      'Comentario',
      'Forma',
      'Volume',
      'Preco',
      'S/L',
      'T/P',
      'HorarioFechamento',
      'PrecoFechamento',
      'Lucro',
      'Mudanca',
      'Data',
    ];
    const linhasCsv = linhas.map((linha) => [
      linha.movimentacao ? 'Movimentacao' : 'Operacao',
      linha.bilhete,
      linha.ativo,
      linha.tipo,
      linha.comentario,
      linha.forma,
      linha.volume ?? '',
      linha.preco ?? '',
      linha.sl ?? '',
      linha.tp ?? '',
      linha.horarioFim,
      linha.precoFim ?? '',
      linha.lucro === null ? '' : String(linha.lucro),
      linha.mudanca,
      linha.horario,
    ]);
    const csv = [cols, ...linhasCsv].map((l) => l.join(';')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'historico-universal.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const qtdOperacoes = linhas.filter((l) => !l.movimentacao).length;
  const qtdMovimentacoes = linhas.length - qtdOperacoes;

  return (
    <>
      <main className="history-page quantum-history">
        <div className="page-head">
          <div>
            <span className="eyebrow">REGISTRO UNIVERSAL</span>
            <h1>Histórico</h1>
            <span className="muted">
              Uma linha por posição, como a aba Histórico do MT5. Entrada e
              fechamento do mesmo negócio são a mesma linha.
            </span>
          </div>
          <div className="btn-row">
            <button className="btn ghost" onClick={exportCsv} disabled={!rows.length}>
              Exportar CSV
            </button>
            <button
              className="btn primary"
              type="button"
              onClick={() => void load()}
              disabled={loading}
            >
              {loading ? 'Atualizando…' : 'Atualizar'}
            </button>
          </div>
        </div>

        <div className="card compact-card history-filter-card">
          <div className="history-filters">
            <label className="field">
              Corretora
              <select value={broker} onChange={(e) => setBroker(e.target.value)}>
                {BROKERS.map((b) => (
                  <option key={b.value} value={b.value}>
                    {b.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Ativo
              <input
                value={symbol}
                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                placeholder={
                  /*
                    O QUE O CAMPO FAZ, POR CORRETORA (06/10/2026)
                    ==============================================
                    MEDIDO: com `Todas` selecionado, o campo dizia "Obrigatorio
                    (ex.: BTCUSDT)" — e o MT5 carregava mesmo sem simbolo.
                    `useHistorico` so pula as EXCHANGES quando o simbolo esta
                    vazio (`historico.ts:408`); o MT5 entra sempre. Um campo
                    que se anuncia obrigatorio e que a tela ignora ensina o
                    operador a desconfiar do resto dos filtros.

                    Agora o texto diz a verdade de cada caso, e `Todas` mostra
                    que as exchanges ficam de fora sem simbolo.
                  */
                  broker === 'mt5'
                    ? 'Opcional (ex.: BTCUSD)'
                    : broker === 'all'
                      ? 'Opcional — sem par, só MT5 (ex.: BTCUSD)'
                      : 'Obrigatório (ex.: BTCUSDT)'
                }
              />
            </label>
            <label className="field">
              Período
              <select value={days} onChange={(e) => setDays(e.target.value)}>
                <option value="1">Hoje</option>
                <option value="7">7 dias</option>
                <option value="15">15 dias</option>
                <option value="30">30 dias</option>
                <option value="90">90 dias</option>
                <option value="365">1 ano</option>
                <option value="0">Tudo</option>
              </select>
            </label>
            <div className="history-count">
              {/*
                OPERACAO E REGISTRO SAO NUMEROS DIFERENTES.
                Uma linha por posição é uma operação; uma movimentação de saldo
                é um registro. Mostrar um número só diria quantas operações
                existem quando a pergunta é quantos registros vieram do
                gateway — e as duas coisas precisam ser ditas.

                O plural acompanha o número: "1 operação" e "2 operações". Texto
                fixo de "operações" com uma operação na tela é gramática
                quebrada no lugar onde o operador está olhando.
              */}
              <span className="muted">Exibindo</span>
              <strong>{qtdOperacoes}</strong>
              <span className="muted">{qtdOperacoes === 1 ? 'operação' : 'operações'}</span>
              {qtdMovimentacoes > 0 && (
                <>
                  <span className="muted">e</span>
                  <strong>{qtdMovimentacoes}</strong>
                  <span className="muted">
                    {qtdMovimentacoes === 1 ? 'movimentação' : 'movimentações'}
                  </span>
                </>
              )}
              {rows.length !== linhas.length && (
                <span
                  className="muted"
                  title={`${rows.length} registros do gateway, agrupados por posição em ${linhas.length} linhas. Uma posição que abre e fecha é um registro só.`}
                >
                  · {rows.length} registros
                </span>
              )}
              {updatedAt !== '--:--:--' && <span className="muted">· {updatedAt}</span>}
            </div>
          </div>
          {error && (
            <div className="placeholder" role="status">
              {error}
            </div>
          )}
          <div className="history-status-row">
            <span className="muted">Fontes: {status}</span>
          </div>
        </div>

        {/*
          A TABELA, E SO ELA.
          ====================
          Colunas na ordem da captura do MT5:
          Horario | Ativo | Bilhete | Tipo | Comentario | Volume | Preco |
          S/L | T/P | Horario | Preco | Lucro | Mudanca

          O `Bilhete` e o ticket, e o `Comentario` e o texto da corretora. Na
          captura o `Bilhete` e o ticket do FECHAMENTO e o comentario da XM
          (`CD-AST-PIC 265376085`, `Credit-In-100%-$100-NewClients`) fica logo
          depois — e mostrar o codigo da corretora e o que permite ao operador
          bater o registro com o MT5.

          O que separa operação de movimentação e o TIPO, e nao a posicao na
          tabela: `balance` e `credit` sao linhas da MESMA tabela, com Tipo
          proprio e os campos de operacao vazios. E por isso que uma
          movimentacao NUNCA tem Lucro — ver `linhasMt5`.

          A coluna `Corretora` saiu (decisao do dono, 05/10/2026): o MT5 nao
          tem essa coluna, e com o filtro em "Todas" o operador ve de qual
          corretora veio cada linha pelo Ativo e pelo Tipo. O texto da
          corretora segue visivel na coluna Comentario.

         .Stop loss e take profit SABEM o valor: vem do deal que os carrega.
          Deal sem SL/TP e operacao a mercado — que e o normal — e por isso a
          coluna escreve vazio e nao "--": "--" aqui diria "o gateway nao
          mandou", e o gateway mandou: mandou vazio.
        */}
        <div className="hist-flat">
          <table className="tbl compact-table history-grid history-deals">
            <caption className="sr-only">Histórico de operações e movimentações de saldo</caption>
            <thead>
              <tr>
                <th className="num">Hora</th>
                <th>Ativo</th>
                <th className="num">Bilhete</th>
                <th>Tipo</th>
                <th>Comentário</th>
                <th className="num">Volume</th>
                <th className="num">Preço</th>
                <th className="num">S/L</th>
                <th className="num">T/P</th>
                <th className="num">Hora</th>
                <th className="num">Preço</th>
                <th className="num">Lucro</th>
                <th className="num">Mudança</th>
              </tr>
            </thead>
            {grupos.map((grupo) => (
              <tbody key={grupo.chave} className="hist-dia">
                <tr className="hist-dia-faixa">
                  <th colSpan={COLUNAS} scope="colgroup">
                    <span className="hist-dia-texto">{grupo.rotulo}</span>
                    <span className="hist-dia-qtd">
                      {grupo.linhas.length}{' '}
                      {grupo.linhas.length === 1 ? 'linha' : 'linhas'}
                    </span>
                  </th>
                </tr>
                {grupo.linhas.map((linha) => {
                  const ehPos = linha.lucro !== null && linha.lucro > 0;
                  const ehNeg = linha.lucro !== null && linha.lucro < 0;
                  return (
                    <tr
                      key={linha.chave}
                      className={
                        linha.movimentacao
                          ? 'history-row-movimentacao'
                          : ehPos
                            ? 'history-row-positive'
                            : ehNeg
                              ? 'history-row-negative'
                              : ''
                      }
                      title={
                        linha.movimentacao
                          ? 'Movimentação de saldo: entrada ou saída de dinheiro, não operação. Por isso Ativo, Volume, Preço, S/L, T/P, Hora e Preço do fechamento, Lucro e Mudança ficam vazios.'
                          : undefined
                      }
                    >
                      {/* Horario de ABERTURA. A data completa fica no `title`. */}
                      <td className="history-when" title={stamp(linha.horario)}>
                        {hora(linha.horario)}
                      </td>
                      <td>
                        <strong>{linha.ativo || '—'}</strong>
                      </td>
                      <td className="num mono">{linha.bilhete || '—'}</td>
                      {/*
                        O TIPO como a corretora classifica, e o texto cru ao lado.
                        MEDIDO: as tres movimentacoes da conta 391773676 vieram
                        como `BALANCE`, `BALANCE` e `CREDIT`. Mostrar so o
                        rotulo traduzido impediria o operador de bater o
                        registro com o MT5.
                      */}
                      <td>
                        <span className={`chip ${linha.movimentacao ? 'warn' : 'ok'}`}>
                          {linha.tipo || '—'}
                        </span>
                      </td>
                      <td className="muted hist-comentario">
                        {/*
                          A FORMA do depósito ou do saque, lida do comentário da
                          corretora. MEDIDO: o deal de movimentação não tem campo
                          de método — o que existe é `comment` em texto livre.

                          Fica NA MESMA célula do comentário, e não numa coluna
                          própria, porque é uma LEITURA desse texto: duas colunas
                          para o mesmo dado são dois lugares para divergirem. E
                          `nao informada` aparece em itálico e apagado — é
                          ausência de informação, não erro, e mostrar em cor de
                          aviso transformaria um depósito comum num alerta falso.
                        */}
                        {linha.forma && (
                          <span
                            className={`hist-forma${linha.forma === 'nao informada' ? ' vazia' : ''}`}
                            title={
                              linha.forma === 'nao informada'
                                ? 'A corretora não informou o método no comentário'
                                : undefined
                            }
                          >
                            {linha.forma}
                          </span>
                        )}
                        {linha.comentario || '—'}
                      </td>
                      <td className="num">{volume(linha.volume)}</td>
                      <td className="num">{preco(linha.preco)}</td>
                      {/* Vazio = a mercado. "--" diria que o gateway nao mandou. */}
                      <td className="num">{preco(linha.sl)}</td>
                      <td className="num">{preco(linha.tp)}</td>
                      {/* Horario e preco do FECHAMENTO. Vazios enquanto a
                          posicao estiver aberta — repetir a hora de abertura
                          diria que ela fechou no minuto em que abriu. */}
                      <td
                        className="history-when"
                        title={
                          linha.horarioFim
                            ? stamp(linha.horarioFim)
                            : 'posição sem fechamento conhecido'
                        }
                      >
                        {hora(linha.horarioFim)}
                      </td>
                      <td className="num">{preco(linha.precoFim)}</td>
                      {/*
                        Lucro e MUDANCA so existem em operacao. Numa
                        movimentacao nao ha preco de entrada, preco de saida nem
                        resultado: o dinheiro entrou. Escrever 0,00 seria inventar
                        medida, e o resumo somaria dinheiro que ENTROU como se
                        fosse resultado.

                        E a celula fica VAZIA, sem travessao: o travessao e o
                        que o operador leria como "algo aqui, mas sem valor", e
                        numa movimentacao nao ha valor faltando — a coluna nao
                        se aplica. O `title` da linha e que diz por que.
                      */}
                      <td
                        className={`num ${ehPos ? 'pos' : ehNeg ? 'neg' : ''}`}
                        title={linha.lucro === null ? 'movimentação de saldo: não é resultado' : undefined}
                      >
                        {linha.lucro === null ? '' : money(linha.lucro)}
                      </td>
                      <td className="num">{linha.mudanca}</td>
                    </tr>
                  );
                })}
              </tbody>
            ))}
            {/*
              "NENHUM REGISTRO" SO QUANDO O DADO FOI LIDO.

              MEDIDO (06/10/2026): com o `terminal64` fechado,
              `history_deals_get` volta vazio, e a tela mostrava esta linha — que
              e uma tela de SUCESSO com zero linhas. O operador foi procurar
              erro na conta. Nao havia erro: havia um programa nao aberto.

              Sao tres situacoes que produzem a MESMA tabela vazia, e cada uma
              pede uma acao diferente:
                - MT5 sem sessao  -> ABRIR O TERMINAL
                - erro de leitura -> o que a rede disse
                - leu e nao achou -> nada a fazer

              Escrever a mesma frase nas tres e o que faz o operador parar de
              ler a tela: quando o texto e sempre o mesmo, ele deixa de esperar
              a informacao que precisa.
            */}
            {!linhas.length && !error && desconectado && (
              <tbody>
                <tr>
                  <td colSpan={COLUNAS} className="hist-vazio">
                    Sem leitura: o MetaTrader 5 está sem sessão. Abra o terminal e
                    faça login — o histórico aparece sozinho.
                  </td>
                </tr>
              </tbody>
            )}
            {!linhas.length && !error && !desconectado && (
              <tbody>
                <tr>
                  <td colSpan={COLUNAS} className="hist-vazio">
                    Nenhum registro no período.
                  </td>
                </tr>
              </tbody>
            )}
            {!linhas.length && error && (
              <tbody>
                <tr>
                  <td colSpan={COLUNAS} className="hist-vazio">
                    Sem leitura: {error}
                  </td>
                </tr>
              </tbody>
            )}

            {/*
              A LINHA DE RESUMO, com os rotulos da captura:
              `Lucro: 2,01  Credito: 5,62  Recarregar: 5,62  Retirada: 0,00  Saldo: 13,25`

              E UM `tfoot`, nao um cartao acima: no MT5 a linha fica grudada na
              tabela, e um cartao separado seria um segundo lugar para o mesmo
              numero.

              `Saldo` fica VAZIO, e isso e medido: ver o comentario do
              `resumo` acima. Escrever a soma das movimentacoes ali diria "saldo"
              para um numero que a corretora nao mediu.
            */}
            <tfoot className="hist-resumo">
              <tr>
                <td colSpan={COLUNAS}>
                  <div className="hist-resumo-grade">
                    <span className="hist-resumo-item">
                      <span className="hist-resumo-rotulo">{ROTULOS_RESUMO[0]}</span>
                      <strong className={resumo.lucro > 0 ? 'pos' : resumo.lucro < 0 ? 'neg' : ''}>
                        {money(resumo.lucro)}
                      </strong>
                    </span>
                    <span className="hist-resumo-item">
                      <span className="hist-resumo-rotulo">{ROTULOS_RESUMO[1]}</span>
                      <strong>{money(resumo.credito)}</strong>
                    </span>
                    <span className="hist-resumo-item">
                      <span className="hist-resumo-rotulo">{ROTULOS_RESUMO[2]}</span>
                      <strong>{money(resumo.recarregar)}</strong>
                    </span>
                    <span className="hist-resumo-item">
                      <span className="hist-resumo-rotulo">{ROTULOS_RESUMO[3]}</span>
                      <strong className={resumo.retirar < 0 ? 'neg' : ''}>
                        {money(resumo.retirar)}
                      </strong>
                    </span>
                    <span
                      className="hist-resumo-item"
                      title="O saldo da conta não sai do histórico. A Carteira mostra o saldo de cada corretora, e é lá que ele é medido."
                    >
                      <span className="hist-resumo-rotulo">{ROTULOS_RESUMO[4]}</span>
                      <strong>—</strong>
                    </span>
                  </div>
                </td>
              </tr>
            </tfoot>
          </table>
          <p className="csv-note">
            Depósitos, saques, créditos e bônus são entradas e saídas de dinheiro — não são
            resultado de operação, e por isso não contam para o Lucro da linha de resumo. Uma
            posição que abre e fecha é uma linha só.
          </p>
        </div>
      </main>
    </>
  );
}