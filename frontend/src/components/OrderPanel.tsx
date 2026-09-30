// Painel de execucao.
//
// O QUE ESTE PAINEL FAZ
// =====================
// Comandos que um robou automatico de topo tem hoje: entrada rapida em um
// clique, fechamento, cancelamento, gestao de posicao e parada de
// emergencia. Nada disto abre posicao sozinho: o operador aperta, o gateway
// valida, e a rota depende da corretora escolhida.
//
// MESA UNIVERSAL
// ==============
// MT5     -> /api/trade/*     (order_check antes do order_send, SL/TP
//                              obrigatorios, teto de volume 0.10)
// demais  -> /api/universal/order com execute=true, que aciona o adaptador
//            da corretora e a gate dela (XAU_ENABLE_<BROKER>_EXECUTION).
//            Quantidade sem teto de 0.10, SL/TP opcionais, e a conta vem de
//            uma conexao cadastrada (account_id).
//
// O QUE NAO FOI REMOVIDO
// ======================
// O gate de execucao. Toda rota continua exigindo `confirm: true` +
// `request_id` idempotente, e passa por risk_gate, intent_log e audit_log.
// O TIPO de conta nao e criterio: DEMO e REAL passam pelo mesmo caminho. A
// confirmacao de tela (checkbox + digitar CONFIRMO) ja saiu, a pedido do
// operador. Saque e transferencia nao existem em nenhuma rota.
//
// PARADA DE EMERGENCIA
// ====================
// Ela fica disponivel MESMO em conta real e mesmo com o gateway negando
// ordens, porque parar sempre e seguro. E o unico botao vermelho cheio do
// painel.
import { useEffect, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import { notify } from '../lib/notify';

const GATEWAY = `${apiBase()}`;
const MAX_VOLUME = 0.1;

// Mesa universal: a mesma tela serve o MT5 e as corretoras de cripto. O roteio
// muda sozinho — MT5 vai para /api/trade/* (order_check + risk_gate) e as
// demais para /api/universal/order com execute=true, que aciona o adaptador
// da propria corretora e a gate dela (XAU_ENABLE_<BROKER>_EXECUTION).
type Broker = 'mt5' | 'mexc' | 'binance' | 'bybit' | 'okx';

const BROKERS: Array<{ id: Broker; rotulo: string }> = [
  { id: 'mt5', rotulo: 'MetaTrader 5' },
  { id: 'mexc', rotulo: 'MEXC' },
  { id: 'binance', rotulo: 'Binance' },
  { id: 'bybit', rotulo: 'Bybit' },
  { id: 'okx', rotulo: 'OKX' },
];

const MERCADOS_CRYPTO = ['crypto-spot', 'crypto-futures'] as const;

// Sem MT5 nao existe as travas de SL/TP obrigatorios nem o teto de 0.10: elas
// sao regras do terminal, nao da corretora.
const ehUniversal = (b: Broker) => b !== 'mt5';

// Icones do card sao SVG inline de proposito: o repo nao tem biblioteca de
// icones e a interface precisa compilar offline, dentro do Tauri.
type IconName =
  | 'ingot' | 'clock' | 'shield' | 'arrowUp' | 'arrowDown' | 'check'
  | 'alert' | 'layers' | 'bolt' | 'target' | 'pie' | 'lock' | 'unlock'
  | 'xCircle' | 'power' | 'send';

const ICONS: Record<IconName, JSX.Element> = {
  ingot: (
    <>
      <path d="M4.4 15.5h15.2l-2.1-5.9a2 2 0 0 0-1.9-1.3H8.4a2 2 0 0 0-1.9 1.3L4.4 15.5Z" fill="currentColor" stroke="none" />
      <path d="M2.6 18.4h18.8" />
    </>
  ),
  clock: (<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>),
  shield: (<><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" /><path d="m9 12 2 2 4-4" /></>),
  arrowUp: (<><path d="M12 19V5" /><path d="m5 12 7-7 7 7" /></>),
  arrowDown: (<><path d="M12 5v14" /><path d="m19 12-7 7-7-7" /></>),
  check: <path d="M20 6 9 17l-5-5" />,
  alert: (<><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" /><path d="M12 9v4" /><path d="M12 17h.01" /></>),
  layers: (<><path d="m12 2 9 5-9 5-9-5 9-5Z" /><path d="m3 12 9 5 9-5" /><path d="m3 17 9 5 9-5" /></>),
  bolt: <path d="M13 2 3 14h8l-1 8 10-12h-8l1-8Z" />,
  target: (<><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="4" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /></>),
  pie: (<><path d="M21.2 15.9A10 10 0 1 1 8 2.8" /><path d="M22 12A10 10 0 0 0 12 2v10Z" /></>),
  lock: (<><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></>),
  unlock: (<><rect x="4" y="11" width="16" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 7.9-1" /></>),
  xCircle: (<><circle cx="12" cy="12" r="9" /><path d="m15 9-6 6M9 9l6 6" /></>),
  power: (<><path d="M12 4v8" /><path d="M18.4 6.6a9 9 0 1 1-12.8 0" /></>),
  send: (<><path d="m22 2-7 20-4-9-9-4 20-7Z" /><path d="M22 2 11 13" /></>),
};

function Ico({ name, size = 15 }: { name: IconName; size?: number }) {
  return (
    <svg
      width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth={2} strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true" focusable="false"
    >
      {ICONS[name]}
    </svg>
  );
}

type AccountMode = 'DEMO' | 'REAL' | 'UNKNOWN' | 'indisponível';
type OrderResult = {
  ok: boolean; stage?: string; retcode?: number; comment?: string;
  order?: number; deal?: number; demo?: boolean; error?: string;
  order_type?: string; price?: number; sl?: number; tp?: number; side?: string;
  count?: number; emergency_stop?: boolean;
  status?: string; code?: string; ticket?: number | string;
  intent_id?: string; withdrawals_enabled?: boolean;
};

type Conexao = { id?: string; broker?: string; market?: string; active?: boolean };

const novoRequestId = () =>
  `xau-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;

const CAMPOS = ['Volume', 'Stop Loss', 'Take Profit'] as const;

function sessaoAgora(): { nome: string; ativo: boolean }[] {
  // Sessoes do forex em UTC. Informativas: nao bloqueiam nada.
  const agora = new Date().getUTCHours() + new Date().getUTCMinutes() / 60;
  const faixas: Array<[string, number, number]> = [
    ['Sydney', 22, 7],
    ['Tokyo', 0, 9],
    ['Londres', 8, 17],
    ['Nova York', 13, 22],
  ];
  return faixas.map(([nome, ini, fim]) => {
    const ativo = ini < fim ? agora >= ini && agora < fim : agora >= ini || agora < fim;
    return { nome, ativo };
  });
}

export default function OrderPanel() {
  const symbol = useAppStore((s) => s.selectedSymbol);
  const [broker, setBroker] = useState<Broker>('mt5');
  const [mercado, setMercado] = useState<string>('crypto-spot');
  const [accountId, setAccountId] = useState('');
  const [conexoes, setConexoes] = useState<Conexao[]>([]);
  const [mode, setMode] = useState<AccountMode>('indisponível');
  const [tradeAllowed, setTradeAllowed] = useState(false);
  const [volume, setVolume] = useState('0.01');
  const [sl, setSl] = useState('');
  const [tp, setTp] = useState('');
  const [kind, setKind] = useState<'market' | 'limit' | 'stop'>('market');
  const [price, setPrice] = useState('');
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<OrderResult | null>(null);
  const [statusMsg, setStatusMsg] = useState('Aguardando gateway…');
  const [sessao, setSessao] = useState(sessaoAgora);
  const [emergencia, setEmergencia] = useState(false);

  // Lê o modo real da conta (trade_mode do MT5) — somente leitura.
  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const r = await fetch(`${GATEWAY}/api/status`, { signal: AbortSignal.timeout(4000) });
        const d = (await r.json()) as {
          account?: { mode?: string; trade_allowed?: boolean };
        };
        if (!active) return;
        const m = (d.account?.mode ?? 'UNKNOWN').toUpperCase();
        setMode(m === 'DEMO' || m === 'REAL' ? m : 'UNKNOWN');
        setTradeAllowed(Boolean(d.account?.trade_allowed));
        setStatusMsg(
          m === 'DEMO'
            ? 'Conta de teste confirmada pelo MT5.'
            : m === 'REAL'
              ? 'Conta real ativa: as ordens vao para o mercado.'
              : 'Modo da conta desconhecido; verifique o login do MT5.',
        );
      } catch {
        if (!active) return;
        setMode('indisponível');
        setStatusMsg('Gateway indisponível (porta 9001 offline).');
      }
    };
    void load();
    const t = window.setInterval(load, 15000);
    return () => {
      active = false;
      window.clearInterval(t);
    };
  }, []);

  // Conexoes cadastradas: necessaria para a mesa universal, porque o gateway
  // exige um account_id ativo que bata com corretora + mercado.
  const universal = ehUniversal(broker);
  useEffect(() => {
    if (!universal) return undefined;
    let ativo = true;
    const carregar = async () => {
      try {
        const r = await fetch(`${GATEWAY}/api/connections`, { signal: AbortSignal.timeout(4000) });
        const d = (await r.json()) as { connections?: Conexao[] };
        if (!ativo) return;
        const lista = (d.connections ?? []).filter(
          (c) => c.active !== false && c.broker === broker && c.market === mercado,
        );
        setConexoes(lista);
        setAccountId((atual) => (lista.some((c) => c.id === atual) ? atual : lista[0]?.id ?? ''));
      } catch {
        if (!ativo) return;
        setConexoes([]);
      }
    };
    void carregar();
    const t = window.setInterval(carregar, 30_000);
    return () => {
      ativo = false;
      window.clearInterval(t);
    };
  }, [broker, mercado, universal]);

  // Sessao de mercado: informativa, atualiza a cada minuto.
  useEffect(() => {
    const t = window.setInterval(() => setSessao(sessaoAgora()), 60_000);
    return () => window.clearInterval(t);
  }, []);

  const num = (v: string) => Number(String(v).replace(',', '.'));
  const vol = num(volume);
  const slNum = num(sl);
  const tpNum = num(tp);
  const priceNum = num(price);
  const fieldsValid = universal
    ? Boolean(symbol) && vol > 0 && Boolean(accountId) && (kind === 'market' || priceNum > 0)
    : Boolean(symbol) && vol > 0 && vol <= MAX_VOLUME && slNum > 0 && tpNum > 0 &&
      (kind === 'market' || priceNum > 0);
  const contaConhecida = universal ? Boolean(accountId) : mode === 'DEMO' || mode === 'REAL';
  const canSend = !busy && fieldsValid && contaConhecida && (universal || tradeAllowed);

  const post = async (path: string, body: Record<string, unknown>) => {
    setBusy(true);
    setResult(null);
    try {
      const r = await fetch(`${GATEWAY}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(12_000),
      });
      const d = (await r.json()) as OrderResult;
      setResult(d);
      return d;
    } catch (e) {
      const erro: OrderResult = {
        ok: false,
        error: `Gateway indisponível: ${e instanceof Error ? e.message : 'erro'}`,
      };
      setResult(erro);
      return erro;
    } finally {
      setBusy(false);
    }
  };

  // Comandos de gestao: passam pelo mesmo gate do gateway (confirm).
  // So existem no MT5: trailing, breakeven, protecao e cancelamento sao
  // endpoints /api/trade/*, que nao tem equivalente nas corretoras de cripto.
  const sendCommand = async (path: string, extra: Record<string, unknown> = {}) => {
    if (busy || !contaConhecida || !tradeAllowed || universal) return;
    const d = await post(path, { symbol, confirm: true, ...extra });
    void notify(
      d.ok ? 'Comando aceito' : 'Comando recusado',
      d.ok ? `${path} executado.` : (d.error ?? 'Veja o resultado no painel.'),
    );
  };

  // Fechar a posicao do simbolo: MT5 usa o endpoint proprio; as corretoras de
  // cripto passam pelo roteador universal, que devolve o motivo real quando a
  // acao nao tem implementacao naquela corretora.
  const fecharPosicao = async () => {
    if (busy || !contaConhecida || (!universal && !tradeAllowed)) return;
    if (!universal) {
      await sendCommand('/api/trade/close-symbol');
      return;
    }
    const d = await post('/api/universal/close', {
      execute: true,
      broker,
      market: mercado,
      symbol,
      account_id: accountId,
      request_id: novoRequestId(),
      confirm: true,
    });
    void notify(
      d.ok ? 'Comando aceito' : 'Comando recusado',
      d.ok ? 'Fechamento enviado.' : (d.error ?? 'Veja o resultado no painel.'),
    );
  };

  const send = async (alvo: 'BUY' | 'SELL') => {
    if (!canSend) return;
    if (universal) {
      await post('/api/universal/order', {
        execute: true,
        broker,
        market: mercado,
        symbol,
        side: alvo.toLowerCase(),
        order_type: kind,
        quantity: vol,
        ...(kind === 'market' ? {} : { price: priceNum }),
        ...(slNum > 0 ? { stop_loss: slNum } : {}),
        ...(tpNum > 0 ? { take_profit: tpNum } : {}),
        account_id: accountId,
        request_id: novoRequestId(),
        confirm: true,
      });
      return;
    }
    const body: Record<string, unknown> = kind === 'market'
      ? { symbol, side: alvo, volume: vol, sl: slNum, tp: tpNum, confirm: true }
      : { symbol, side: alvo, kind, price: priceNum, volume: vol, sl: slNum, tp: tpNum, confirm: true };
    await post(kind === 'market' ? '/api/trade/order' : '/api/trade/pending', body);
  };

  // Parada de emergencia: sempre disponivel, inclusive em conta real.
  // `confirm: true` e obrigatorio no gateway — sem ele o handler devolve 422 e
  // o corpo ja traz `emergency_stop`, o que fazia o painel vitoriar sem parar
  // nada. O confirm vem aqui, e so aqui.
  const pararEmergencia = async () => {
    if (busy) return;
    const d = await post('/api/universal/emergency-stop', { symbol, confirm: true });
    if (d.ok) {
      setEmergencia(true);
      void notify('Parada de emergencia ativada', 'Toda execucao foi cortada no gateway.');
    } else {
      void notify('Parada nao ativada', d.error ?? 'Veja o resultado no painel.');
    }
  };

  const retomar = async () => {
    if (busy) return;
    const d = await post('/api/universal/emergency-resume', { confirm: true });
    if (d.ok) {
      setEmergencia(false);
      void notify('Retomada', 'Execucao liberada.');
    } else {
      void notify('Retomada bloqueada', d.error ?? 'Veja o resultado no painel.');
    }
  };

  const bloqueado = busy || !contaConhecida || (!universal && !tradeAllowed);
  const sessaoAtiva = sessao.find((s) => s.ativo)?.nome ?? 'fechado';

  return (
    <div className="card order-panel" style={{ marginTop: 14 }}>
      <div className="xau-head" style={{ marginTop: 0 }}>
        <div className="xau-title-row">
          <span className="xau-badge"><Ico name="ingot" size={15} /> XAU AI PRO</span>
          <div>
            <h2 style={{ margin: 0 }}>
              Execução · <span className="xau-symbol">{symbol || 'ativo não selecionado'}</span>
            </h2>
            <span className="muted">
              {universal
                ? `${broker.toUpperCase()} · /api/universal/order · saque e transferência desligados`
                : 'order_check → order_send · volume máx 0.10 · SL/TP obrigatórios'}
            </span>
          </div>
        </div>
        <div className="btn-row" style={{ justifyContent: 'flex-end', flexWrap: 'wrap' }}>
          <span className="xau-chip"><Ico name="clock" size={13} /> Sessão {sessaoAtiva}</span>
          <span className={`xau-chip ${mode === 'REAL' ? 'is-real' : mode === 'DEMO' ? 'is-demo' : ''}`}>
            <span className="xau-dot" />
            {universal
              ? `${broker.toUpperCase()} · ${mercado}`
              : mode === 'DEMO' ? 'Conta DEMO' : mode === 'REAL' ? 'Conta REAL' : mode}
          </span>
        </div>
      </div>

      {/* Mesa universal: escolher a corretora muda o roteio, as travas e os
          campos. MT5 mantem as regras do terminal; as demais vao para o
          adaptador proprio com a gate de cada corretora. */}
      <div className="btn-row" style={{ marginTop: 10, flexWrap: 'wrap', gap: 8 }}>
        {BROKERS.map((b) => (
          <button
            key={b.id}
            type="button"
            className={`btn sm${b.id === broker ? ' primary' : ''}`}
            aria-pressed={b.id === broker}
            onClick={() => setBroker(b.id)}
            title={b.id === 'mt5' ? 'Endpoint /api/trade/* do terminal' : `Rota /api/universal/* · gate XAU_ENABLE_${b.id.toUpperCase()}_EXECUTION`}
          >
            {b.rotulo}
          </button>
        ))}
        {universal && (
          <select
            aria-label="Mercado"
            value={mercado}
            onChange={(e) => setMercado(e.target.value)}
            style={{ marginLeft: 'auto' }}
          >
            {MERCADOS_CRYPTO.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        )}
      </div>
      {universal && (
        <div className="grid cols-2" style={{ marginTop: 10 }}>
          <div className="field">
            <label htmlFor="xau-conta">Conta da corretora</label>
            <select id="xau-conta" value={accountId} onChange={(e) => setAccountId(e.target.value)}>
              {conexoes.length === 0 && <option value="">sem conexão cadastrada</option>}
              {conexoes.map((c) => <option key={c.id} value={c.id ?? ''}>{c.id}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="xau-conta-status">Situação</label>
            <input
              id="xau-conta-status"
              readOnly
              value={conexoes.length === 0
                ? 'Cadastre a conexão em Conexões antes de enviar.'
                : `${conexoes.length} conexão(ões) ativa(s) para ${broker}/${mercado}`}
            />
          </div>
        </div>
      )}

      {/* Faixa de protecao: o operador ve a trava antes de apertar qualquer botao. */}
      <div className="xau-guard">
        <Ico name="shield" size={15} />
        <span>
          {universal
            ? `${broker.toUpperCase()} · confirm=true + request_id idempotente · passa por risk_gate, intent_log e auditoria · saque e transferência permanecem desligados`
            : <>SL e TP obrigatórios · volume ≤ {MAX_VOLUME.toFixed(2)} · order_check antes do
              order_send · {mode === 'REAL' ? 'ordens vão ao mercado' : mode === 'DEMO' ? 'conta de teste' : 'modo da conta ainda não lido'}</>}
        </span>
      </div>

      {/* Entrada rapida em um clique: usa os campos abaixo (volume, SL, TP). */}
      <div className="btn-row" style={{ marginTop: 12, gap: 10 }}>
        <button
          className="btn quick-buy"
          type="button"
          onClick={() => void send('BUY')}
          disabled={!canSend}
          aria-label={`Comprar ${symbol} a mercado`}
          style={{ flex: 1, minHeight: 54, fontWeight: 700, letterSpacing: 0.4 }}
        >
          <Ico name="arrowUp" size={24} />
          <span className="quick-label">
            <b>COMPRAR</b>
            <small>{symbol || 'sem ativo'}</small>
          </span>
        </button>
        <button
          className="btn quick-sell"
          type="button"
          onClick={() => void send('SELL')}
          disabled={!canSend}
          aria-label={`Vender ${symbol} a mercado`}
          style={{ flex: 1, minHeight: 54, fontWeight: 700, letterSpacing: 0.4 }}
        >
          <Ico name="arrowDown" size={24} />
          <span className="quick-label">
            <b>VENDER</b>
            <small>{symbol || 'sem ativo'}</small>
          </span>
        </button>
      </div>

      <div className="grid cols-4" style={{ marginTop: 12 }}>
        <div className="field"><label htmlFor="xau-volume">{universal ? 'Quantidade' : `Volume (máx ${MAX_VOLUME.toFixed(2)})`}</label><input id="xau-volume" type="number" min="0" step="any" value={volume} onChange={(e) => setVolume(e.target.value)} /></div>
        <div className="field"><label htmlFor="xau-sl">{universal ? 'Stop Loss' : 'Stop Loss *'}</label><input id="xau-sl" type="number" step="any" value={sl} onChange={(e) => setSl(e.target.value)} /></div>
        <div className="field"><label htmlFor="xau-tp">{universal ? 'Take Profit' : 'Take Profit *'}</label><input id="xau-tp" type="number" step="any" value={tp} onChange={(e) => setTp(e.target.value)} /></div>
        <div className="field"><label htmlFor="xau-kind">Execução</label>
          <select id="xau-kind" value={kind} onChange={(e) => setKind(e.target.value as 'market' | 'limit' | 'stop')}>
            <option value="market">Mercado (imediata)</option>
            <option value="limit">Limit (pendente, preço alvo)</option>
            <option value="stop">Stop (pendente, rompimento)</option>
          </select>
        </div>
        {kind !== 'market' && (
          <div className="field"><label htmlFor="xau-price">Preço alvo *</label><input id="xau-price" type="number" step="any" value={price} onChange={(e) => setPrice(e.target.value)} /></div>
        )}
      </div>
      {/* Sem select de Lado e sem botao "Enviar": COMPRAR/VENDER ja mandam o
          lado certo e ja respeitam "Execução" e preço-alvo. Era o mesmo
          comando escrito duas vezes na mesma tela — o operador escolhia o
          lado aqui embaixo e depois de novo nos dois botões grandes. */}

      <div className="xau-section"><Ico name="layers" size={14} /> Posição aberta</div>
      <div className="btn-row" style={{ marginTop: 8, flexWrap: 'wrap' }}>
        <button className="btn ghost danger" type="button" disabled={bloqueado} onClick={() => void fecharPosicao()} title={universal ? 'POST /api/universal/close' : 'Fecha a posição do símbolo atual'}><Ico name="xCircle" size={14} /> Fechar símbolo</button>
        <button className="btn ghost" type="button" disabled={bloqueado || universal} onClick={() => void sendCommand('/api/trade/trailing')} title={universal ? 'Comando MT5: trailing stop só existe no terminal' : 'Trailing stop ativo na posição'}><Ico name="bolt" size={14} /> Trailing</button>
        <button className="btn ghost" type="button" disabled={bloqueado || universal} onClick={() => void sendCommand('/api/trade/breakeven')} title={universal ? 'Comando MT5: break-even só existe no terminal' : 'Move o SL para o preço de entrada (break-even)'}><Ico name="target" size={14} /> Break-even</button>
        <button className="btn ghost" type="button" disabled={bloqueado || universal} onClick={() => void sendCommand('/api/trade/set-protection', { sl: slNum, tp: tpNum })} title={universal ? 'Comando MT5: proteção só existe no terminal' : 'Aplica SL/TP informados na posição'}><Ico name="lock" size={14} /> Proteção</button>
      </div>

      {/* O que saiu daqui e o que ja existe em outro lugar da mesma tela:
          "Fechar tudo" = "Fechar todas" do Mini Terminal logo abaixo;
          "Parcial" e "Remover prot." nao eram usados nem citados em teste;
          "Cancelar ordem" repetia "Cancelar todas" para um caso so.
          Sobram os quatro comandos que o operador aperta de verdade. */}
      <div className="xau-section"><Ico name="clock" size={14} /> Ordens pendentes</div>
      <div className="btn-row" style={{ marginTop: 8, flexWrap: 'wrap' }}>
        <button className="btn ghost danger" type="button" disabled={bloqueado || universal} onClick={() => void sendCommand('/api/trade/cancel-all-orders')} title={universal ? 'Comando MT5: cancelamento em massa só existe no terminal' : 'Cancela todas as ordens pendentes'}><Ico name="xCircle" size={14} /> Cancelar todas</button>
      </div>

      <div className="hint" style={{ marginTop: 6 }}>{kind === 'market' ? 'Mercado: solicita execução com SL/TP obrigatórios; confirme o resultado no MT5.' : `Pendente ${kind.toUpperCase()}: solicita entrada no preço alvo com SL/TP. O preenchimento e a proteção dependem da corretora; não há garantia de OCO.`} Sempre via gateway.</div>

      <div className="hint" style={{ marginTop: 8 }}>
        {universal ? (
          <>
            {conexoes.length === 0
              ? 'Sem conexão cadastrada para esta corretora/mercado: cadastre em Conexões.'
              : `Rota ${broker.toUpperCase()} · /api/universal/${kind === 'market' ? 'order' : 'order'}.`}
            {!fieldsValid && (vol <= 0 ? ' Informe a quantidade.' : !accountId ? ' Escolha a conta.' : ' Preencha quantidade e preço alvo.')}
            {fieldsValid && !canSend && ' Envio indisponível no momento.'}
          </>
        ) : (
          <>
            {statusMsg} {!tradeAllowed && mode !== 'indisponível' && 'Negociação bloqueada no terminal. '}
            {!fieldsValid && 'Preencha volume ≤ 0.10, SL e TP.'}
            {kind !== 'market' && !priceNum && ' Preço alvo obrigatório.'}
            {fieldsValid && !canSend && contaConhecida && !tradeAllowed && ' Negociação bloqueada no terminal. '}
          </>
        )}
      </div>
      {result && (
        <div className={`xau-result ${result.ok ? 'is-ok' : 'is-neg'}`} role="status">
          <Ico name={result.ok ? 'check' : 'alert'} size={15} />
          <span>
            {result.ok
              ? <span>Ordem aceita{result.status ? ` · ${result.status}` : ''}{result.stage ? ` · stage ${result.stage}` : ''}{result.retcode !== undefined ? ` · retcode ${result.retcode}` : ''}{result.order ? ` · ticket ${result.order} · deal ${result.deal}` : ''}{!result.order && result.ticket !== undefined ? ` · ticket ${result.ticket}` : ''}{result.intent_id ? ` · intent ${result.intent_id}` : ''}{result.count !== undefined ? ` · ${result.count} itens` : ''}{result.order_type ? ` · ${result.order_type}` : ''}{result.price ? ` · @ ${result.price}` : ''}{result.comment ? ` · ${result.comment}` : ''}</span>
              : <span>Recusada{result.code ? ` · ${result.code}` : ''}{result.status ? ` · ${result.status}` : ''}{result.stage ? ` · stage ${result.stage}` : ''}{result.retcode !== undefined ? ` · retcode ${result.retcode}` : ''}{result.comment ? ` · ${result.comment}` : ''}{result.error ? ` · ${result.error}` : ''}</span>}
          </span>
        </div>
      )}

      {/* A PARADA DE EMERGENCIA SAIU DESTE PAINEL em 2026-09-29.

          Ela aparecia aqui E no `RiskTab`, na mesma aba ROBÔ: dois botões com o
          mesmo efeito, em lados opostos da tela, era exatamente o tipo de
          duplicidade que faz o operador clicar no errado. O `RiskTab` ficou
          como o unico lugar, logo acima dos limites, onde a leitura do risco
          justifica a acao.

          O endpoint `/api/universal/emergency-stop` continua intacto e e
          acionado pelo `RiskTab`; o que saiu foi a segunda porta de entrada. */}
      <div className="hint" style={{ marginTop: 6 }}>{CAMPOS.join(' · ')} são os campos usados pelos botões rápidos acima.</div>
    </div>
  );
}
