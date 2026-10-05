import { useMemo } from 'react';
import { apiBase } from '../lib/api';
import { useAutoState, usePositions } from '../hooks/queries';
import { useSinaisModelo } from '../hooks/useSinaisModelo';
import { getCandles, type MarketCandle } from '../lib/marketApi';
import { notify } from '../lib/notify';
import { requestId } from '../lib/format';
import { useEffect, useState } from 'react';
import PriceChart from './charts/PriceChart';

// Acompanhar os modelos operando, ao vivo e com seguranca.
//
// O operador elogiou o grafico tempo real para operar. Faltava ver ONDE o
// modelo decide: o sinal vinha como numero solto no painel, sem contexto de
// preco nem de hora. Aqui cada sinal vira marcador no candle (BUY verde
// abaixo, SELL vermelho acima) com a confianca, e a fita mostra o historico
// com a idade de cada leitura.
//
// SEGURANCA
// =========
// - 1-clique usa LOTE/SL/TP ja configurados no motor, com confirmacao
//   explicita mostrando tudo. Sem config, o botao diz o que falta.
// - Sem resposta, a fita mostra "desatualizado ha Xs" em vez de sumir: sinal
//   velho passado por novo e o modo silencioso de operar no escuro.
// - Sem par configurado no motor, o painel diz isso em vez de adivinhar um.
export default function AcompanharModelos() {
  const autoQ = useAutoState();
  const auto = autoQ.data;
  const broker = String(auto?.broker ?? '').toLowerCase();
  const market = String(auto?.market ?? '').toLowerCase();
  const simbolo = String(auto?.simbolo ?? '').toUpperCase();
  const timeframe = String(auto?.timeframe ?? '').toUpperCase();
  const configurado = Boolean(broker && market && simbolo && timeframe);
  const limites = (auto?.limites ?? {}) as { lote?: number; sl_preco?: number; tp_preco?: number };
  const pronto1Clique =
    (limites.lote ?? 0) > 0 && (limites.sl_preco ?? 0) > 0 && (limites.tp_preco ?? 0) > 0;

  const positionsQ = usePositions();
  const posicoes = Array.isArray(positionsQ.data?.positions) ? positionsQ.data.positions : [];
  const [verEma, setVerEma] = useState(true);
  const [ocupado, setOcupado] = useState(false);

  const { sinais, idadeSeg } = useSinaisModelo(simbolo, timeframe, configurado);
  const [candles, setCandles] = useState<MarketCandle[] | undefined>(undefined);
  const [erroVelas, setErroVelas] = useState('');

  useEffect(() => {
    if (!configurado) return undefined;
    let vivo = true;
    const carregar = async () => {
      try {
        const r = await getCandles({ broker: broker as never, market: market as never, symbol: simbolo }, timeframe, 300);
        if (vivo) {
          setCandles(r.candles);
          setErroVelas('');
        }
      } catch (e) {
        if (vivo) setErroVelas(e instanceof Error ? e.message : 'Candles indisponíveis.');
      }
    };
    void carregar();
    const t = window.setInterval(carregar, 30_000);
    return () => {
      vivo = false;
      window.clearInterval(t);
    };
  }, [broker, market, simbolo, timeframe, configurado]);

  // Cada sinal ancora no candle fechado mais recente ate a hora do sinal.
  const markers = useMemo(() => {
    if (!candles?.length) return [];
    return sinais
      .map((s) => {
        let alvo = 0;
        for (const c of candles) {
          if (c.time <= s.time) alvo = c.time;
          else break;
        }
        if (!alvo) return null;
        return {
          time: alvo,
          signal: s.signal,
          text: `${s.signal} ${s.confidence ?? '--'}%`,
        };
      })
      .filter((m): m is { time: number; signal: string; text: string } => m !== null);
  }, [candles, sinais]);

  if (!configurado) {
    return (
      <section className="card compact-card" aria-label="Acompanhar modelos">
        <div className="section-head">
          <div>
            <h2>Acompanhar modelos</h2>
            <span className="muted">Configure o par no motor para ver os sinais no gráfico.</span>
          </div>
        </div>
      </section>
    );
  }

  const desatualizado = idadeSeg !== null && idadeSeg > 150;

  // Posicoes do par desenhadas no grafico: entrada, SL e TP. SL/TP com
  // ticket arrastam e aplicam ao soltar (estilo MT5).
  const linhas = useMemo(() => {
    const lista: Array<{ price: number; color: string; title: string; ticket?: number | string; kind?: 'sl' | 'tp' | 'entrada' }> = [];
    for (const p of posicoes as Array<Record<string, unknown>>) {
      if (String(p.symbol ?? '').toUpperCase() !== simbolo) continue;
      const abertura = Number(p.open_price ?? p.price_open);
      const sl = Number(p.sl);
      const tp = Number(p.tp);
      const ticket = (p.ticket ?? '') as number | string;
      if (Number.isFinite(abertura)) lista.push({ price: abertura, color: '#4f7cff', title: 'entrada' });
      if (Number.isFinite(sl) && sl > 0)
        lista.push({ price: sl, color: '#ef4444', title: `SL ${ticket}`, ticket, kind: 'sl' });
      if (Number.isFinite(tp) && tp > 0)
        lista.push({ price: tp, color: '#22c55e', title: `TP ${ticket}`, ticket, kind: 'tp' });
    }
    return lista;
  }, [posicoes, simbolo]);

  // Soltou a linha: aplica na hora (MT5 nao pergunta). Erro volta sozinho
  // no proximo refresh das posicoes — a linha mentirosa nao fica.
  const moverLinha = async (ticket: number | string, kind: 'sl' | 'tp', price: number) => {
    try {
      const corpo: Record<string, unknown> =
        kind === 'sl' ? { sl: price } : { tp: price };
      const r = await fetch(`${apiBase()}/api/trade/modify-position`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticket, ...corpo, request_id: requestId(), confirm: true }),
        signal: AbortSignal.timeout(15000),
      });
      const d = (await r.json().catch(() => ({}))) as { ok?: boolean; error?: string };
      notify(
        r.ok && d.ok !== false ? 'Proteção movida' : 'Movimento recusado',
        r.ok && d.ok !== false
          ? `${kind.toUpperCase()} do ticket ${ticket} em ${price}.`
          : String(d.error ?? `HTTP ${r.status}`),
      );
      void positionsQ.refetch();
    } catch (e) {
      notify('Gateway indisponível', e instanceof Error ? e.message : 'erro');
      void positionsQ.refetch();
    }
  };

  // 1-clique no grafico: mercado, com LOTE/SL/TP do motor e confirmacao.
  // Exchanges nao tem ordem manual: o botao diz, em vez de fingir.
  const umClique = async (lado: 'BUY' | 'SELL') => {
    if (ocupado || !configurado) return;
    if (broker !== 'mt5') {
      notify('Ordem manual indisponível', 'Exchanges operam pelo motor automático.');
      return;
    }
    if (!pronto1Clique) {
      notify('Falta configurar', 'Defina LOTE, SL e TP no painel de operação automática.');
      return;
    }
    const lote = Number(limites.lote);
    if (!window.confirm(`${lado} ${lote} ${simbolo} a mercado\nSL ${limites.sl_preco} · TP ${limites.tp_preco}\nConfirma?`)) return;
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
          volume: lote,
          sl: limites.sl_preco,
          tp: limites.tp_preco,
          request_id: requestId(),
          confirm: true,
        }),
        signal: AbortSignal.timeout(15000),
      });
      const d = (await r.json().catch(() => ({}))) as { ok?: boolean; error?: string };
      notify(r.ok && d.ok !== false ? 'Ordem enviada' : 'Ordem recusada', r.ok && d.ok !== false ? `${lado} ${lote} ${simbolo}.` : String(d.error ?? `HTTP ${r.status}`));
      void positionsQ.refetch();
    } catch (e) {
      notify('Gateway indisponível', e instanceof Error ? e.message : 'erro');
    } finally {
      setOcupado(false);
    }
  };
  return (
    <section className="card robo-grafico" aria-label="Gráfico operacional ao vivo">
      <div className="section-head">
        <div>
          <h2>Gráfico ao vivo</h2>
          <span className="muted">
            {simbolo} · {timeframe} · {broker.toUpperCase()}
            {desatualizado ? ` · desatualizado há ${idadeSeg}s` : ' · ao vivo'}
          </span>
        </div>
        <span className={`chip ${desatualizado ? 'warn' : 'ok'}`}>
          {sinais.length ? `${sinais.length} sinais no gráfico` : 'aguardando sinal'}
        </span>
      </div>
      <PriceChart
        symbol={simbolo}
        broker={broker as never}
        market={market as never}
        timeframe={timeframe as never}
        candles={candles}
        markers={markers}
        lines={linhas}
        ema={verEma}
        onMoveLine={(ticket, kind, price) => void moverLinha(ticket, kind, price)}
        error={erroVelas}
        sourceLabel={`${broker.toUpperCase()} · sinais do modelo`}
      />
      <div className="btn-row" role="group" aria-label="Operar no gráfico">
        <button type="button" className="btn sm success" onClick={() => void umClique('BUY')} disabled={ocupado}>
          Comprar 1-clique
        </button>
        <button type="button" className="btn sm danger" onClick={() => void umClique('SELL')} disabled={ocupado}>
          Vender 1-clique
        </button>
        <label className="chip" style={{ cursor: 'pointer' }}>
          <input type="checkbox" checked={verEma} onChange={(e) => setVerEma(e.target.checked)} />
          EMA 12/26
        </label>
        <span className="muted">usa LOTE/SL/TP do motor · com confirmação</span>
      </div>
      {/*
        A TABELA DE SINAIS FOI REMOVIDA.
        ======================================
        O dono: "nada de prever tabela de previsao — isso nao ajuda em nada, o
        que importa e operar, ordens ao vivo, grafico operacional".

        Os sinais NAO sumiram: eles continuam desenhados como MARCADORES no
        candle (BUY verde abaixo do preco, SELL vermelho acima), que e onde o
        operador olha o preco de qualquer forma. A tabela repetia os mesmos
        numeros em texto — hora, sinal, confianca, preco, modelo — num bloco que
        ocupava a tela abaixo dos botoes de operar.

        Um dado mostrado em dois lugares faz o operador desconfiar dos dois.
        Agora o sinal existe em um lugar so, e a tela inteira e para operar.
      */}
    </section>
  );
}
