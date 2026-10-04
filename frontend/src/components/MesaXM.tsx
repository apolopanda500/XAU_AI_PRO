import { useEffect, useMemo, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import { useAutoState } from '../hooks/queries';
import { notify } from '../lib/notify';
import { escopoAtivo as contaAtiva } from '../lib/escopoAtivo';
import { requestId } from '../lib/format';
import LatenciaBar from './LatenciaBar';

// Mesa XM + MT5: ticket manual simples e poderoso.
//
// LADO (comprar/vender) + LOTE + SL/TP. Preco ao vivo na tela; a ordem sai a
// mercado pelo `/api/trade/order` (MT5, com risk_gate e order_check). SL/TP
// aceitam preco cheio (4130) ou distancia (10) — a conversao aparece antes
// de confirmar, sem presuncao silenciosa.
//
// SEM SELETOR DE CORRETORA: o ticket opera o escopo ativo (o mesmo do Mini
// Terminal). Seletor proprio aqui foi o defeito que fez a ordem ir para a
// corretora errada — por isso a ordem manual saiu da aba uma vez. Ela volta
// sem o seletor, e o teste que proibia a volta foi atualizado.
//
// SEGURANCA: exchanges nao tem ordem manual (sem adaptador no bundle) — o
// botao diz isso em vez de fingir. Confirmacao explicita antes de enviar.
export default function MesaXM() {
  const autoQ = useAutoState();
  const wsConnected = useAppStore((s) => s.wsConnected);
  const auto = autoQ.data;
  const simbolo = String(auto?.simbolo ?? '').toUpperCase();
  const timeframe = String(auto?.timeframe ?? '').toUpperCase();

  const [lado, setLado] = useState<'BUY' | 'SELL'>('BUY');
  const [lote, setLote] = useState('0.01');
  const [sl, setSl] = useState('');
  const [tp, setTp] = useState('');
  const [preco, setPreco] = useState<number | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [status, setStatus] = useState('');

  const { broker, market } = contaAtiva();
  const soMT5 = broker === 'mt5';

  // Preco ao vivo do ativo do motor.
  useEffect(() => {
    if (!simbolo) return undefined;
    let vivo = true;
    const ler = async () => {
      try {
        const r = await fetch(
          `${apiBase()}/api/universal/quotes?broker=${broker}&market=${market}&symbols=${encodeURIComponent(simbolo)}`,
          { signal: AbortSignal.timeout(10000) },
        );
        const d = (await r.json()) as {
          quotes?: Array<{ price?: number; last?: number; bid?: number; ask?: number }>;
        };
        const q = d.quotes?.[0];
        const p = q?.price ?? q?.last ?? (lado === 'BUY' ? q?.ask : q?.bid) ?? null;
        if (vivo && typeof p === 'number') setPreco(p);
      } catch {
        /* mantem o ultimo preco; o envio valida de novo no gateway */
      }
    };
    void ler();
    const t = window.setInterval(ler, 5_000);
    return () => {
      vivo = false;
      window.clearInterval(t);
    };
  }, [broker, market, simbolo, lado]);

  // SL/TP: preco cheio vence quando coerente; senao vira distancia do preco
  // ao vivo (mesma regra do motor). Sem preco ao vivo, so preco cheio.
  const resolvidos = useMemo(() => {
    const num = (v: string) => Number(String(v).replace(',', '.'));
    const slN = num(sl);
    const tpN = num(tp);
    if (!preco || !(slN > 0) || !(tpN > 0)) return { sl: slN, tp: tpN, modo: 'preco' as const };
    const coerente =
      lado === 'BUY' ? slN < preco && preco < tpN : tpN < preco && preco < slN;
    if (coerente) return { sl: slN, tp: tpN, modo: 'preco' as const };
    if (Math.max(slN, tpN) < preco * 0.5) {
      return lado === 'BUY'
        ? { sl: preco - slN, tp: preco + tpN, modo: 'distancia' as const }
        : { sl: preco + slN, tp: preco - tpN, modo: 'distancia' as const };
    }
    return { sl: slN, tp: tpN, modo: 'invalido' as const };
  }, [sl, tp, preco, lado]);

  const enviar = async () => {
    if (ocupado || !simbolo) return;
    if (!soMT5) {
      notify('Ordem manual indisponível', `Execução manual em ${broker.toUpperCase()} ainda não tem adaptador. Exchanges operam pelo motor automático.`);
      return;
    }
    const loteN = Number(lote.replace(',', '.'));
    if (!(loteN > 0) || loteN > 0.1) {
      setStatus('Lote entre 0.01 e 0.10.');
      return;
    }
    if (resolvidos.modo === 'invalido' || !(resolvidos.sl > 0) || !(resolvidos.tp > 0)) {
      setStatus(
        lado === 'BUY'
          ? 'Para BUY: SL abaixo e TP acima do preço (cheio ou distância).'
          : 'Para SELL: TP abaixo e SL acima do preço (cheio ou distância).',
      );
      return;
    }
    const resumo =
      `${lado} ${loteN} ${simbolo} a mercado\nSL ${resolvidos.sl.toFixed(2)} · TP ${resolvidos.tp.toFixed(2)}` +
      (resolvidos.modo === 'distancia' ? ' (distância convertida)' : '') +
      `\nConta ${broker.toUpperCase()} — confirma?`;
    if (!window.confirm(resumo)) return;
    setOcupado(true);
    try {
      const r = await fetch(`${apiBase()}/api/trade/order`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          broker,
          market,
          symbol: simbolo,
          side: lado,
          volume: loteN,
          sl: Math.round(resolvidos.sl * 100) / 100,
          tp: Math.round(resolvidos.tp * 100) / 100,
          request_id: requestId(),
          confirm: true,
        }),
        signal: AbortSignal.timeout(15000),
      });
      const d = (await r.json().catch(() => ({}))) as { ok?: boolean; error?: string };
      if (r.ok && d.ok !== false) {
        setStatus('Ordem enviada.');
        notify('Ordem enviada', `${lado} ${loteN} ${simbolo}.`);
      } else {
        setStatus(d.error || `HTTP ${r.status}`);
        notify('Ordem recusada', d.error || `HTTP ${r.status}`);
      }
    } catch (e) {
      setStatus(`Gateway indisponível: ${e instanceof Error ? e.message : 'erro'}`);
    } finally {
      setOcupado(false);
    }
  };

  return (
    <section className="card compact-card" aria-label="Mesa XM MT5">
      <div className="section-head">
        <div>
          <h2>Mesa · XM + MT5</h2>
          <span className="muted">
            {simbolo ? `${simbolo} ${timeframe}`.trim() : 'Sem par no motor'} ·{' '}
            {broker.toUpperCase()} · preço {preco ?? '--'}
          </span>
        </div>
        <div className="btn-row">
          <span className={`chip ${wsConnected ? 'ok' : 'warn'}`} title="Auto-reconexão do app: cai e volta sozinho">
            {wsConnected ? 'Tempo real' : 'Reconectando…'}
          </span>
        </div>
      </div>
      <div className="btn-row" role="group" aria-label="Lado da ordem">
        {(['BUY', 'SELL'] as const).map((v) => (
          <button
            key={v}
            type="button"
            className={`btn ${lado === v ? (v === 'BUY' ? 'success' : 'danger') : 'ghost'}`}
            onClick={() => setLado(v)}
          >
            {v === 'BUY' ? 'Comprar' : 'Vender'}
          </button>
        ))}
        <label className="field" style={{ marginBottom: 0 }}>
          <span>Lote</span>
          <input
            type="number"
            step={0.01}
            min={0.01}
            max={0.1}
            value={lote}
            onChange={(e) => setLote(e.target.value)}
            aria-label="Quantidade em lotes"
          />
        </label>
        <label className="field" style={{ marginBottom: 0 }}>
          <span>SL</span>
          <input value={sl} onChange={(e) => setSl(e.target.value)} placeholder="4130 ou 10" aria-label="Stop loss" />
        </label>
        <label className="field" style={{ marginBottom: 0 }}>
          <span>TP</span>
          <input value={tp} onChange={(e) => setTp(e.target.value)} placeholder="4150 ou 20" aria-label="Take profit" />
        </label>
        <button type="button" className="btn primary" onClick={() => void enviar()} disabled={ocupado || !simbolo}>
          {ocupado ? 'Enviando…' : 'Enviar ordem'}
        </button>
      </div>
      {resolvidos.modo === 'distancia' && (
        <p className="hint" role="status">
          Distância convertida: SL {resolvidos.sl.toFixed(2)} · TP {resolvidos.tp.toFixed(2)}.
        </p>
      )}
      {status && (
        <p className="hint" role="status">
          {status}
        </p>
      )}
      <LatenciaBar />
    </section>
  );
}
