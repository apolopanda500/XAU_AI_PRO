import { useMemo } from 'react';
import { apiBase } from '../lib/api';
import {
  useCoreStatus,
  useAccount,
  usePositions,
  useJournal,
  useAllCryptoAccounts,
  useAutoState,
} from '../hooks/queries';
import { fmtNum, clsPnl, sideOfPosition, extractSymbol, requestId } from '../lib/format';
import { notify } from '../lib/notify';
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
  free_margin?: number;
  margin_level?: number;
  profit?: number;
  leverage?: number | string;
};

// Escopo de corretora/mercado ativo: fonte única em lib/escopoAtivo.ts.
// Este terminal usava um leitor proprio com o market sem passar por
// compatibleMarket, enquanto RobotCommandActions passava — os dois paineis
// podiam resolver o mesmo par para mercados diferentes.
import { escopoAtivo as activeAccount } from '../lib/escopoAtivo';

export default function UniversalLiveTerminal() {
  const statusQ = useCoreStatus();
  const accountQ = useAccount();
  const positionsQ = usePositions();
  const journalQ = useJournal(10); // journal MT5: 10s (baixa latência)
  const cryptoQ = useAllCryptoAccounts(); // cripto: 30s (fundo de Rede)
  const autoQ = useAutoState(); // motor automático: 5s

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
      const kind = /trade|order|execut|buy|sell|close|fill/i.test(message)
        ? 'TRADES'
        : /warn|alert/i.test(message)
          ? 'WARN'
          : /error|fail/i.test(message)
            ? 'ERROR'
            : 'INFO';
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
    // Contas de cripto (Spot/Futuros de MEXC e Binance) — conteúdo de conta real, não "informação básica"
    for (const c of cryptoQ.data ?? []) {
      if (!c.ok) {
        rows.push({
          id: `cry-${c.broker}-${c.market}`,
          source: c.broker.toUpperCase(),
          info: `${c.market === 'crypto-spot' ? 'Spot' : 'Futuros'} indisponível`,
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
  }, [journalQ.data, cryptoQ.data]);

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

  const floating = positions.reduce((s, p) => s + (Number(p.profit) || 0), 0);
  const volume = positions.reduce((s, p) => s + (Number(p.volume) || 0), 0);
  const margin = Number(account?.margin ?? 0);
  const freeMargin = Number(account?.free_margin ?? 0);
  const marginLevel = Number(account?.margin_level ?? 0);
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
        <h2>Mini Terminal</h2>
        <div className="btn-row">
          <span className={`chip ${modoTone}`} title="Modo da conta no MT5">
            {modoLabel}
          </span>
          <span className={`chip ${connected ? 'ok' : 'warn'}`}>
            {connected ? 'Conectado' : 'Desconectado'}
          </span>
          <span className={`chip ${eaHeartbeat.live ? 'ok' : 'warn'}`}>
            EA {eaHeartbeat.live ? `${eaHeartbeat.age_sec ?? 0}s` : 'off'}
          </span>
          <button
            type="button"
            className="btn xs ghost"
            onClick={refreshAll}
            disabled={busy}
            aria-label="Atualizar Mini Terminal"
          >
            {busy ? 'Atualizando…' : 'Atualizar'}
          </button>
        </div>
      </div>

      {/* Faixa de conta no estilo da barra de status do MT5: uma linha, celulas
        coladas, sem card e sem rotulo descritivo. As 8 caixas empilhadas
        ocupavam meia aba para repetir o que o MT5 mostra numa faixa. */}
      <div className="mt-status-strip">
        <span>
          <em>Conta</em>
          <strong className="mono">{account?.login ?? '--'}</strong>
        </span>
        <span>
          <em>Servidor</em>
          <strong>{account?.server || '--'}</strong>
        </span>
        <span>
          <em>Saldo</em>
          <strong className="num">{fmtNum(account?.balance)}</strong>
        </span>
        <span>
          <em>Patrimônio</em>
          <strong className="num">{fmtNum(account?.equity)}</strong>
        </span>
        <span>
          <em>Flutuante</em>
          <strong className={`num ${clsPnl(floating)}`}>{fmtNum(floating)}</strong>
        </span>
        <span>
          <em>Margem</em>
          <strong className="num">{fmtNum(margin)}</strong>
        </span>
        <span>
          <em>Livre</em>
          <strong className="num">{fmtNum(freeMargin)}</strong>
        </span>
        <span>
          <em>Nível</em>
          <strong className={`num ${marginLevel > 0 && marginLevel < 200 ? 'neg' : ''}`}>
            {marginLevel > 0 ? `${marginLevel.toFixed(0)}%` : '--'}
          </strong>
        </span>
        <span>
          <em>Posições</em>
          <strong className="num">{positions.length}</strong>
        </span>
        <span title="Motor de operação automática — liga e desliga na sub-aba Automação">
          <em>Auto</em>
          <strong className={autoAtivo ? 'auto-on' : ''}>
            {autoAtivo
              ? `Ligado · ${auto?.simbolo ?? '--'} ${auto?.timeframe ?? ''} · ciclo ${auto?.ciclo ?? 0}`
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
