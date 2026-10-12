import { useMemo } from 'react';
import { apiBase } from '../lib/api';
import {
  useCoreStatus,
  useAccount,
  usePositions,
  useJournal,
  useAllCryptoAccounts,
  useAutoState,
  useUniversalOverview,
  useUniversalAccount,
  useUniversalPositions,
} from '../hooks/queries';
import { fmtNum, clsPnl, sideOfPosition, extractSymbol, requestId } from '../lib/format';
import { notify } from '../lib/notify';
import { classificarJournal } from '../lib/journalKind';
import '../theme/mini-terminal.css';
import '../theme/mt5-terminal.css';

const API = `${apiBase()}`;
type Position = {
  ticket?: number | string;
  symbol?: string;
  type?: number | string;
  volume?: number;
  open_price?: number;
  price_current?: number;
  sl?: number;
  tp?: number;
  profit?: number;
  swap?: number;
};
type Account = {
  login?: number | string;
  name?: string;
  server?: string;
  currency?: string;
  balance?: number;
  equity?: number;
  margin?: number;
  /*
    `margin_free`, E NAO `free_margin` (09/10/2026)
    ===============================================
    MEDIDO na captura de 07/10 00:33, no app instalado, na faixa "Terminal ao
    vivo": `Saldo 2,78 | Patrimonio 8,40 | Flutuante 0,00 | Margem 0,00 |
    Livre 0,00 | Nivel --`. A conta tem patrimonio, e margem livre 0,00 com
    patrimonio 8,40 e um numero que nao existe.

    A CAUSA, e ela e nome de campo — o AGENTS.md §5
    ================================================
    O PRODUTOR, `backend/mt5_gateway.py:1617`, manda `margin_free`:

        "margin_free": optional_number(getattr(info, "margin_free", None)),

    E o MT5 tambem chama assim: `account_info().margin_free`. O `queries.ts:197`
    le a chave certa no `TelemetrySnapshot`.

    O CONSUMIDOR lia `free_margin`. Como `free_margin` nao existe no payload,
    o `?? 0` do `Number(...)` convertia o desencontro em `0,00` — silencioso,
    sem erro, sem log, e com o TIPO repetindo o erro, entao `tsc` ficava limpo.

    O QUE ISSO TIRAVA DO OPERADOR
    ==============================
    A trava de risco usa `MinFreeMargin` (medido em 15,48 contra piso 10,00 na
    conta 391773676). O operador lia `Livre 0,00` numa conta que tinha folga —
    e `0,00` era a leitura que diria "a trava esta no chao". Um numero que
    nunca sai do zero ensina a desconfiar da tela inteira.

    E O TESTE, que passava pelo motivo errado
    =========================================
    `UniversalLiveTerminal.journal.test.tsx:30` montava o mock com
    `margin_free: 0` — a chave CERTA — e nunca olhava a celula `Livre`. O
    `0` no mock escondia justamente o valor que estava errado. Um teste que
    so verifica o que ja funciona nao pega o que esta quebrado (AGENTS.md §6).
  */
  margin_free?: number;
  margin_level?: number;
  profit?: number;
  leverage?: number | string;
};

// Escopo de corretora/mercado ativo: fonte única em lib/escopoAtivo.ts.
// Este terminal usava um leitor proprio com o market sem passar por
// compatibleMarket, enquanto RobotCommandActions passava — os dois paineis
// podiam resolver o mesmo par para mercados diferentes.
import { escopoAtivo as activeAccount } from '../lib/escopoAtivo';

type DecisaoMotor = {
  timestamp?: string;
  sinal?: string;
  symbol?: string;
  timeframe?: string;
  motivo?: string;
  confianca?: number;
  edge?: number | null;
  modelo?: string;
};

/**
 * Uma decisao do motor, com os nomes do BACKEND.
 *
 * POR QUE EXISTE
 * ==============
 * A tela lia `d.ts`, `d.side` e `d.simbolo`. O `Decisao` do backend envia
 * `timestamp`, `sinal` e `symbol`. Os tres nomes do painel nao existem no
 * payload, e o resultado era o sintoma do dono: a coluna "Decisao" mostrava
 * `--` e "sem sinal", e "quando" mostrava a hora atual em vez da do ciclo
 * (`new Date(undefined)` e invalido e caia no `now`).
 *
 * REGRA: PRECEDENCIA DO CANONICO
 * -------------------------------
 * Quando os dois nomes vem, o do backend vence. A alternativa — o primeiro
 * que aparecer — faria o resultado depender da ordem das chaves do objeto,
 * que o `JSON.parse` nao garante. O mesmo formato de precedencia foi aplicado
 * em `UniversalOrderRequest.from_payload` para `quantity`/`volume`.
 */
export function normalizarDecisao(bruto: Record<string, unknown> | null | undefined): DecisaoMotor {
  const d = (bruto ?? {}) as Record<string, unknown>;
  const texto = (v: unknown): string => (typeof v === 'string' ? v.trim() : '');
  return {
    timestamp: texto(d.timestamp) || texto(d.ts),
    sinal: texto(d.sinal) || texto(d.side),
    symbol: texto(d.symbol) || texto(d.simbolo),
    timeframe: texto(d.timeframe),
    motivo: texto(d.motivo),
    confianca: typeof d.confianca === 'number' ? d.confianca : 0,
    edge: typeof d.edge === 'number' ? d.edge : null,
    modelo: texto(d.modelo),
  };
}

export default function UniversalLiveTerminal() {
  const statusQ = useCoreStatus();
  const accountQ = useAccount();
  const positionsQ = usePositions();
  const journalQ = useJournal(10); // journal MT5: 10s (baixa latência)
  const cryptoQ = useAllCryptoAccounts(); // cripto: 30s (fundo de Rede)
  const autoQ = useAutoState(); // motor automático: 5s
  /*
    CONTAS CONECTADAS, SEM MT5 ABERTO (12/10/2026).
    MEDIDO nas capturas MT5 do dia: `Observação do Mercado` (cotações),
    gráfico BTCUSD M15, `Caixa de ferramentas` (posição sell 0.01) e faixa
    `Saldo 11.47 / Capital 16.53 / Margem 0.83 / Livre 15.70 / Nível
    1991.57%`. O terminal lia tudo por `/api/account` + `/api/positions`
    (MT5 fixo): com o terminal fechado a tela apagava, mesmo com
    Binance/MEXC conectadas.
    O overview (`/api/universal/overview`) lista cada conexão com `status`
    próprio e `mt5_required: false`: MT5 pode estar `offline` e a exchange
    `conectada` na mesma resposta. Conta e posições abaixo preferem o
    universal da corretora ativa; o legado MT5 fica como reserva.
  */
  const overviewQ = useUniversalOverview();
  const conexoes = Array.isArray(overviewQ.data?.connections) ? overviewQ.data!.connections! : [];
  const { broker, market } = activeAccount();
  const uniAccountQ = useUniversalAccount(broker, market);
  const uniPositionsQ = useUniversalPositions(broker, market);

  // O motor roda em background, a sub-aba Automação pode estar fechada. O
  // operador precisa ver AQUI se ele está ligado e sobre qual par — é a
  // prova de que "ativar automático" teve efeito, sem abrir a configuração.
  const auto = autoQ.data;
  const autoAtivo = Boolean(auto?.ativo);
  // A decisao mais recente do motor: o historico vem do mais novo para o mais
  // velho (ver `MotorAuto._registrar`), entao o indice 0 e o ultimo ciclo.
  const ultimaDecisao = Array.isArray(auto?.decisoes) ? auto.decisoes[0] : undefined;
  // O nome do modelo que REALMENTE rodou neste ciclo, lido do `.meta.json`
  // pelo backend. Antes o terminal montava `random_forest_${simbolo}_${tf}`
  // aqui dentro - um nome que ele fabricava, sem nunca ter lido o artefato.
  const modeloDoCiclo = String(ultimaDecisao?.modelo ?? '').trim();

  // O modo da conta (DEMO/REAL) aparece AQUI e em mais lugar nenhum da
  // interface: o Mini Terminal ja mostra saldo, patrimonio e posicoes, entao
  // e o ponto unico onde o operador ve se esta em conta de teste ou real.
  const statusAccount = (statusQ.data?.account ?? {}) as { mode?: string; trade_allowed?: boolean };
  const accountMode = String(statusAccount.mode ?? '').toUpperCase();
  const modoLabel = accountMode === 'DEMO' ? 'DEMO' : accountMode === 'REAL' ? 'REAL' : '—';
  const modoTone = accountMode === 'DEMO' ? 'ok' : accountMode === 'REAL' ? 'danger' : 'warn';

  const connected = Boolean(statusQ.data?.terminal_connected);
  const eaHeartbeat = (statusQ.data?.ea_heartbeat ?? {}) as {
    live?: boolean;
    age_sec?: number;
    symbol?: string;
  };
  const accountRaw = accountQ.data as Record<string, unknown> | undefined;
  const account =
    accountRaw && typeof accountRaw === 'object'
      ? ((accountRaw.account ?? accountRaw) as Account)
      : null;
  const positions = useMemo(
    () =>
      Array.isArray(positionsQ.data?.positions) ? (positionsQ.data.positions as Position[]) : [],
    [positionsQ.data],
  );

  const events = useMemo(() => {
    const now = new Date();
    const rows: Array<{ id: string; source: string; info: string; at: Date; kind: string }> = [];
    // Journal MT5 (grade trader: tipo + símbolo + mensagem)
    for (const line of (journalQ.data?.lines ?? []) as Array<Record<string, unknown>>) {
      const message = String(line?.message ?? '').trim();
      if (!message) continue;
      //
      // O TIPO VEM DE `classificarJournal`, que le o VALOR que o EA escreveu.
      // Antes era uma cascata de regex sobre a PALAVRA, e medido: ela errava
      // em 5 das 6 linhas reais do journal. Os sete checks de saude que
      // diziam "AI: OK | Failures: 0 | Error:" apareciam ERROR, porque
      // `Failures` e `Error:` sao NOME DE CAMPO e a regex casava o nome; e
      // `[SAFETY]` (63.837 linhas) e `[CIRCUIT]` (29.574) apareciam INFO,
      // que sao as duas travas que impediram operacao. O operador via
      // vermelho no saudavel e branco no que travava. Ver `lib/journalKind`.
      const kind = classificarJournal(message);
      const rawTime = line?.time ?? line?.timestamp;
      const parsed = rawTime
        ? new Date(String(rawTime).replace(/^(\d{4})\.(\d{2})\.(\d{2}) /, '$1-$2-$3T'))
        : now;
      rows.push({
        id: `mt5-${rows.length}-${message.slice(0, 24)}`,
        source: 'MT5',
        info: message,
        at: Number.isNaN(parsed.getTime()) ? now : parsed,
        kind,
      });
    }
    // DECISOES DO MOTOR NO FEED (04/10/2026)
    //
    // O feed tinha journal do MT5 e contas cripto, e nao tinha o motor. O
    // operador via "Auto: Ligado" na faixa e nenhuma linha dizendo o que o
    // motor respondeu — e ligar o automatico sem ver resposta e indistinguivel
    // de um motor que ligou e nao faz nada.
    //
    // Entra aqui pelo mesmo caminho do resto: a mesma fonte (`autoQ`), sem
    // polling novo — seria o mesmo endpoint lido duas vezes.
    //
    // OS NOMES DESACARAM (corrigido em 04/10/2026)
    // -------------------------------------------
    // A tela lia `d.ts`, `d.side` e `d.simbolo`. O `Decisao` do backend manda
    // `timestamp`, `sinal` e `symbol` — tres nomes que nao existem no payload.
    // O resultado era exatamente o sintoma do dono: a coluna "Decisao" mostrava
    // "--" e "sem sinal", e "quando" mostrava a hora atual em vez da hora do
    // ciclo, porque `new Date(undefined)` e invalido e caia no `now`.
    //
    // `normalizarDecisao` aceita os DOIS nomes. Sem isso, corrigir o nome na
    // tela quebraria o outro consumidor, e vice-versa: e a terceira vez que o
    // mesmo par de nomes diverge (`volume`/`quantity`, `ts`/`timestamp`).
    for (const bruto of (auto?.decisoes ?? []).slice(0, 6)) {
      const d = normalizarDecisao(bruto);
      const quando = d.timestamp ? new Date(d.timestamp) : now;
      const valido = !Number.isNaN(quando.getTime());
      const rotulo = [d.symbol, d.timeframe].filter(Boolean).join(' ') || '--';
      const resposta = d.sinal ? `${d.sinal} ${fmtNum(d.confianca, 1)}%` : 'sem sinal';
      rows.push({
        id: `auto-${d.timestamp ?? rotulo}`,
        source: 'MOTOR',
        info: `${rotulo} · ${resposta} · ${d.motivo || 'sem motivo'}`,
        at: valido ? quando : now,
        // Uma decisao com `sinal` e uma acao do modelo; sem `sinal` e recusa
        // ou erro, que o operador precisa distinguir de uma ordem.
        kind: d.sinal ? 'TRADES' : /erro|recus|fail/i.test(String(d.motivo ?? '')) ? 'ERROR' : 'WARN',
      });
    }

    // Contas de cripto (Spot/Futuros de MEXC e Binance) — conteúdo de conta real, não "informação básica"
    for (const c of cryptoQ.data ?? []) {
      if (!c.ok) {
        /*
          O MOTIVO VAI NA LINHA (12/10/2026). "Spot indisponível" sozinho fez
          o dono perguntar o que havia de errado com a conta: chave invalida,
          IP bloqueado e gateway fora produziam a mesma linha. O motivo vem em
          `c.error` (ver `queries.ts`); cortado em 90 para a linha continuar
          sendo uma linha. Sem motivo, o texto continua o de sempre.
        */
        const motivo = String(c.error ?? '').trim().slice(0, 90);
        rows.push({
          id: `cry-${c.broker}-${c.market}`,
          source: c.broker.toUpperCase(),
          info: `${c.market === 'crypto-spot' ? 'Spot' : 'Futuros'} indisponível${motivo ? `: ${motivo}` : ''}`,
          at: now,
          kind: 'WARN',
        });
        continue;
      }
      const bal = fmtNum(c.balance, 2);
      const assets = c.assets.length ? ` · ${c.assets.length} ativos` : '';
      rows.push({
        id: `cry-${c.broker}-${c.market}`,
        source: c.broker.toUpperCase(),
        info: `${c.market === 'crypto-spot' ? 'Conta Spot' : 'Conta Futuros'} · saldo ${bal} ${c.currency}${assets}`,
        at: now,
        kind: 'INFO',
      });
    }
    return rows.sort((a, b) => b.at.getTime() - a.at.getTime()).slice(0, 14);
  }, [journalQ.data, cryptoQ.data, auto]);

  // Fechamento de posição via gateway.
  //
  // O campo obrigatorio e `confirm` (backend/mt5_gateway.py:1872,
  // `_require_trade_command`). Este componente mandava `confirm`,
  // `confirm_live` e `authorize_execution`, que o gateway ignora: o
  // fechamento era recusado com 403 em todas as tentativas.
  //
  // O caminho MT5 e o unico com adaptador de execucao. Para corretora de
  // exchange nao existe adaptador wired no processo empacotado, entao o botao
  // diz isso em vez de fingir que enviou.
  const closePosition = async (p: Position) => {
    const { broker, market } = activeAccount();
    // SEM CONTA, SEM FECHAMENTO (11/10/2026, nada de MT5 fixo). Sem esta
    // guarda a mensagem sairia "Execução em ainda não tem adaptador" — recusa
    // sem sujeito, que manda o operador adivinhar o que falta.
    if (!broker) {
      notify(
        'Fechamento indisponível',
        'Escolha a conta em Configurações → Conexões (botão Ativar da conexão).',
      );
      return;
    }
    if (broker !== 'mt5') {
      notify(
        'Fechamento indisponível',
        `Execução em ${broker.toUpperCase()} ainda não tem adaptador. Use MT5.`,
      );
      return;
    }
    if (
      !window.confirm(
        `Fechar posição ${p.ticket ?? ''} (${p.symbol ?? '--'}) via EA em conta DEMO?`,
      )
    )
      return;
    try {
      const r = await fetch(`${API}/api/ea/close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          broker,
          market,
          symbol: p.symbol ?? '',
          ticket: p.ticket ?? 0,
          request_id: requestId(),
          confirm: true,
          action: 'close',
        }),
        signal: AbortSignal.timeout(10000),
      });
      const d = (await r.json()) as { error?: string; stage?: string; status?: string };
      if (r.ok) {
        notify(
          'Fechamento de posição',
          `Comando de fechamento enviado para ${p.symbol ?? 'posição'} (ticket ${p.ticket ?? '--'}).`,
        );
        void positionsQ.refetch();
      } else {
        notify('Fechamento rejeitado', d.error || `HTTP ${r.status}`);
      }
    } catch {
      notify('Gateway indisponível', 'Não foi possível enviar o fechamento agora.');
    }
  };
  const closeAllPositions = async () => {
    if (!positions.length) return;
    if (
      !window.confirm(
        `Fechar ${positions.length} posição(ões) do EA? Esta ação envia comandos reais para conta DEMO.`,
      )
    )
      return;
    await Promise.all(positions.map((position) => closePosition(position)));
    void positionsQ.refetch();
  };

  /*
  O FLUTUANTE E O DO MT5, E NAO A SOMA DA NOSSA LISTA (09/10/2026)
  ================================================================
  MEDIDO: a faixa mostrava `Flutuante 0,00` enquanto o proprio MT5, na mesma
  conta e no mesmo instante, mostrava `Lucro: -5,65`.

  A soma das posicoes que a tela tem e uma SEGUNDA medida: se a lista de
  posicoes vier vazia — e ela vinha vazia quando o gateway ainda nao tinha
  lido a conta — a soma e zero, e o zero e mostrado como se fosse o numero.
  O `account_info().profit` e a medida do MT5, e e a que o operador ve no
  terminal dele.

  Por isso: o do MT5 quando existe, e a soma das posicoes so como reserva.
  Duas medidas para o mesmo numero e o AGENTS.md §5 de novo.
*/
const flutuanteDoMt5 = account?.profit;
  const floating =
    typeof flutuanteDoMt5 === 'number' && Number.isFinite(flutuanteDoMt5)
      ? flutuanteDoMt5
      : positions.reduce((s, p) => s + (Number(p.profit) || 0), 0);
  const volume = positions.reduce((s, p) => s + (Number(p.volume) || 0), 0);
  const margin = Number(account?.margin ?? 0);
  // `margin_free`, nao `free_margin`: e o nome que o gateway manda e o que o
  // MT5 devolve. Ver o motivo, medido, na declaracao do tipo acima.
  const freeMargin = Number(account?.margin_free ?? 0);
  const marginLevel = Number(account?.margin_level ?? 0);
  // MEDIDO em 09/10: `account_info().leverage = 1000` e a XM escreve
  // `Alavancagem 1000:1` no painel `Gerir`. Sao o mesmo numero, dos dois lados.
  const alavancagem = account?.leverage;
  /*
    SEM CONTA LIDA, O NUMERO E `--`, E NAO `0,00` (09/10/2026)
    ============================================================
    MEDIDO no app instalado, 19:37, com o MT5 fechado:

        SALDO --  PATRIMONIO --  FLUTUANTE 0,00  MARGEM 0,00  LIVRE 0,00

    `fmtNum(account?.balance)` devolve `--` quando a conta nao veio — porque
    `fmtNum(undefined)` nao e numero. Mas `freeMargin`, `margin` e `floating` ja
    tinham virado `0` pelo `?? 0`, e `fmtNum(0)` escreve `0,00`.

    Resultado: `LIVRE 0,00` ao lado de `SALDO --` na MESMA faixa. O operador
    lia "a margem livre e zero" numa tela que, duas casas antes, dizia que nao
    leu conta nenhuma. Um zero que nao foi medido e o pior numero da tela: e
    o que a trava de risco `MinFreeMargin` leria.

    A regra: sem leitura, `--`. Zero so quando o zero foi lido.
  */
  const semConta = !account;
  const numSemConta = (n: number) => (semConta ? '--' : fmtNum(n));
  const busy = statusQ.isFetching || accountQ.isFetching || positionsQ.isFetching;
  const refreshAll = () => {
    void statusQ.refetch();
    void accountQ.refetch();
    void positionsQ.refetch();
    void cryptoQ.refetch();
  };

  return (
    <div className="card compact-card robot-live-latest">
      <div className="section-head mini-terminal-head">
        {/* NOME COMPLETO, UMA VEZ. O painel chamava este bloco de "Mini
            Terminal" e o `RobotTabs` envolvia em "Posições ao vivo": sao dois
            nomes para a mesma coisa, e o operador nao sabia se eram telas
            diferentes. Agora o cabecalho diz o que e: o terminal. */}
        <h2>Terminal ao vivo</h2>
        <div className="btn-row">
          <span className={`chip ${modoTone}`} title="Modo da conta: DEMO (teste) ou REAL (dinheiro de verdade)">
            {modoLabel}
          </span>
          <span className={`chip ${connected ? 'ok' : 'warn'}`} title="Conexão do terminal MetaTrader 5">
            {connected ? 'MT5 conectado' : 'MT5 desconectado'}
          </span>
          <span
            className={`chip ${eaHeartbeat.live ? 'ok' : 'warn'}`}
            title="Expert Advisor: seconds since the last heartbeat"
          >
            EA {eaHeartbeat.live ? `viva · ${eaHeartbeat.age_sec ?? 0}s` : 'off'}
          </span>
          <span
            className={`chip ${autoAtivo ? 'ok' : 'warn'}`}
            title="Motor de operação automática"
          >
            Motor {autoAtivo ? 'ligado' : 'desligado'}
          </span>
          <button
            type="button"
            className="btn xs ghost"
            onClick={refreshAll}
            disabled={busy}
            aria-label="Atualizar todos os dados do terminal"
          >
            {busy ? 'Atualizando…' : 'Atualizar'}
          </button>
        </div>
      </div>

      {/* Faixa de conta no estilo da barra de status do MT5: UMA LINHA, celulas
        coladas, sem card e sem rotulo descritivo.

        MEDIDO nas capturas da XM (`my.xm.com`, 06/10 20:37) e do MT5 desktop
        (08/10 22:14), os doisMostram o MESMO formato:

            Saldo: $4.88  Capital: $10.50  Margem Livre: $10.50  Margem: -
            Lucro: -5.65  Crédito: 6.27  Recarregar: 16.67  Saldo: 17.29

        Rotulo e valor NA MESMA LINHA, separados por dois pontos, com o valor em
        negrito e o rotulo em cinza. Antes o rotulo ficava EM CIMA do valor, em
        caixa propria com piso de 78px — e dez casas empilhadas ocupavam meia
        aba para repetir o que o MT5 mostra numa faixa.

        O que entrou a mais, e tudo medido no payload que o PRODUTOR ja manda
        (`backend/mt5_gateway.py:1608`): `alavancagem` e `moeda`. Faltavam, e o
        operador so encontrava um dos dois descendo a tela ate o painel de ordem.
      */}
      <div className="mt-status-strip">
        <span className="mt-celula">
          <em>Saldo</em>
          <strong className="num">{fmtNum(account?.balance)}</strong>
        </span>
        <span className="mt-celula">
          <em>Patrimônio</em>
          <strong className="num">{fmtNum(account?.equity)}</strong>
        </span>
        <span className="mt-celula">
          <em>Flutuante</em>
          <strong className={`num ${clsPnl(floating)}`}>{numSemConta(floating)}</strong>
        </span>
        <span className="mt-celula">
          <em>Margem</em>
          <strong className="num">{numSemConta(margin)}</strong>
        </span>
        <span className="mt-celula">
          <em>Livre</em>
          <strong className="num">{numSemConta(freeMargin)}</strong>
        </span>
        <span className="mt-celula">
          <em>Nível</em>
          <strong className={`num ${marginLevel > 0 && marginLevel < 200 ? 'neg' : ''}`}>
            {marginLevel > 0 ? `${marginLevel.toFixed(0)}%` : '--'}
          </strong>
        </span>
        {/*
          ALAVANCAGEM: e a que decide se um lote cabe. MEDIDO em 09/10 na conta
          391773676: `account_info().leverage = 1000`, e a XM escreve
          `Alavancagem 1000:1` no painel `Gerir`. Sao o mesmo numero, lidos de
          dois lados.

          Sem isso na tela, o operador so descobria a alavancagem descendo ate o
          painel de ordem — e a escada de lotes (0,01 a 0,05 nesta conta)
          depende dela.
        */}
        {alavancagem !== undefined && Number(alavancagem) > 0 && (
          <span className="mt-celula">
            <em>Alav.</em>
            <strong className="num">{`${Number(alavancagem)}:1`}</strong>
          </span>
        )}
        <span className="mt-celula">
          <em>Posições</em>
          <strong className="num">{positions.length}</strong>
        </span>
        {account?.currency && (
          <span className="mt-celula">
            <em>Moeda</em>
            <strong>{String(account.currency)}</strong>
          </span>
        )}
        <span className="mt-celula mt-celula-conta">
          <em>Conta</em>
          <strong className="mono">{account?.login ?? '--'}</strong>
        </span>
        <span className="mt-celula">
          <em>Servidor</em>
          <strong>{account?.server || '--'}</strong>
        </span>
        <span className="mt-celula mt-celula-auto" title="Motor de operação automática — liga e desliga na sub-aba Automação">
          <em>Auto</em>
          <strong className={autoAtivo ? 'auto-on' : ''}>
            {/*
              SEM O CONTADOR DE CICLO (09/10/2026, pedido do dono)
              =================================================
              MEDIDO na captura de 20:17: `AUTO Ligado · BTCUSD H1 · ciclo 2`.

              O numero do ciclo e um contador INTERNO do motor. Ele nao diz ao
              operador nada que ele possa usar: nao diz o que o motor decidiu, nem
              se a decisao foi boa. E sobe sozinho — o operador ve `ciclo 2` e
              nao sabe se o motor workingou 2 vezes ou se o contador reiniciou.

              Trocar por `último ciclo`, que e o que o operador PRECISA ver: se o
              motor avaliou alguma vez. Ver a celula de decisao logo abaixo, que ja
              mostra o ultimo sinal e o motivo.

              O pedido foi "remover nomes ciclo 1,2,3,4,5,6".
            */}
            {autoAtivo
              ? `Ligado · ${auto?.simbolo ?? '--'} ${auto?.timeframe ?? ''} · último ciclo`
              : autoQ.isError
                ? 'sem leitura'
                : 'Desligado'}
          </strong>
        </span>
        {/* O QUE O MOTOR ESTA FAZENDO AGORA (2026-09-29).

          O painel de cima so dizia "Ligado". O operador nao tinha como saber,
          sem abrir outra aba, qual modelo estava rodando nem o que ele
          respondeu no ultimo ciclo. Ligar o automatico e ficar olhando um
          "Ligado" sem sinal algum e indistinguivel de um motor que ligou e
          nao faz nada — que era exatamente o bug do "erro no ciclo".

          Aqui o par vem do proprio motor, o modelo vem do nome do artefato e
          a ultima decisao vem do historico que `ciclo_unico` ja gravava. */}
        {autoAtivo && (
          <span title="Modelo e última decisão do ciclo em execução">
            <em>Modelo</em>
            <strong>
              {/* O nome vem da DECISAO registrada pelo motor, nao de
                `auto.simbolo`/`auto.timeframe`. Antes era montado aqui como
                `random_forest_${simbolo}_${timeframe}` - o terminal mostrava
                um nome que o motor nunca leu do disco. Se o ciclo ainda nao
                rodou, mostra o par (verdadeiro) em vez de um algoritmo
                inventado. */}
              {modeloDoCiclo ||
                (auto?.simbolo && auto?.timeframe ? `${auto.simbolo}_${auto.timeframe}` : '—')}
            </strong>
          </span>
        )}
        {autoAtivo && ultimaDecisao && (
          <span title="Última decisão do motor automático">
            <em>Último sinal</em>
            <strong
              className={
                /buy|compra/i.test(String(ultimaDecisao.side ?? ''))
                  ? 'ok'
                  : /sell|venda/i.test(String(ultimaDecisao.side ?? ''))
                    ? 'warn'
                    : ''
              }
            >
              {ultimaDecisao.side || ultimaDecisao.acao || 'NEUTRAL'}
              {typeof ultimaDecisao.confianca === 'number'
                ? ` ${ultimaDecisao.confianca.toFixed(0)}%`
                : ''}
            </strong>
          </span>
        )}
        {autoAtivo && ultimaDecisao?.motivo && (
          <span title="Por que o motor decidiu isso">
            <em>Motivo</em>
            <strong className="muted">{ultimaDecisao.motivo}</strong>
          </span>
        )}
      </div>

      <div className="table-scroll">
        <table className="tbl compact-table positions-table mt5-table">
          <thead>
            <tr>
              <th>Ticket</th>
              <th>Ativo</th>
              <th>Lado</th>
              <th className="num">Vol</th>
              <th className="num">Abertura</th>
              <th className="num">Atual</th>
              <th className="num">SL</th>
              <th className="num">TP</th>
              <th className="num">Swap</th>
              <th className="num">PnL</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <tr key={String(p.ticket)}>
                <td className="mono">{p.ticket ?? '--'}</td>
                <td>
                  <strong>{p.symbol ?? '--'}</strong>
                </td>
                <td>
                  <span className={`chip ${sideOfPosition(p) === 'BUY' ? 'ok' : 'warn'}`}>
                    {sideOfPosition(p)}
                  </span>
                </td>
                <td className="num">{fmtNum(p.volume, 2)}</td>
                <td className="num">{fmtNum(p.open_price, 2)}</td>
                <td className="num">{fmtNum(p.price_current, 2)}</td>
                <td className="num">{p.sl ? fmtNum(p.sl, 2) : '--'}</td>
                <td className="num">{p.tp ? fmtNum(p.tp, 2) : '--'}</td>
                <td className="num">{fmtNum(p.swap ?? 0, 2)}</td>
                <td className={`num ${clsPnl(Number(p.profit ?? 0))}`}>{fmtNum(p.profit, 2)}</td>
                <td className="mt-actions-cell">
                  <button
                    type="button"
                    className="btn xs danger mt-close-btn"
                    onClick={() => void closePosition(p)}
                  >
                    Fechar
                  </button>
                </td>
              </tr>
            ))}
            {!positions.length && (
              <tr>
                <td colSpan={11} className="mt-empty">
                  {positionsQ.isFetching ? 'Carregando…' : 'Nenhuma posição aberta.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="btn-row mt-footer-actions">
        <button
          type="button"
          className="btn xs danger"
          onClick={() => void closeAllPositions()}
          disabled={!positions.length || busy}
        >
          Fechar todas ({positions.length})
        </button>
        <span className="muted">Vol {fmtNum(volume, 2)} · atualiza a cada 5s</span>
      </div>

      <div className="table-scroll">
        <table className="tbl compact-table mt-events">
          <thead>
            <tr>
              <th>Hora</th>
              <th>Fonte</th>
              <th>Tipo</th>
              <th>Informação</th>
            </tr>
          </thead>
          <tbody>
            {events.map((event) => (
              <tr key={event.id}>
                <td className="mono">{event.at.toLocaleTimeString('pt-BR')}</td>
                <td>
                  <span className={`mt-source ${event.source.toLowerCase()}`}>{event.source}</span>
                </td>
                <td>
                  <span className={`ev-kind ${event.kind}`}>{event.kind}</span>
                </td>
                <td>{event.info}</td>
              </tr>
            ))}
            {!events.length && (
              <tr>
                <td colSpan={4} className="mt-empty">
                  {journalQ.isFetching ? 'Lendo journal…' : 'Nenhum evento.'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
