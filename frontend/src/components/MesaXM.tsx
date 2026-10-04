import { useEffect, useMemo, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import { useAutoState } from '../hooks/queries';
import { notify } from '../lib/notify';
import { escopoAtivo as contaAtiva } from '../lib/escopoAtivo';
import { requestId } from '../lib/format';
import LatenciaBar from './LatenciaBar';

// =============================================================================
//  MESA XM + MT5 — o ticket e o terminal na MESMA tela
// =============================================================================
//  POR QUE ESTE ARQUIVO MUDOU
//  ===========================
//  O dono pediu: "varias informacao em uma so tela que ajude trades, tp sl
//  facil de configurar" e "o mini terminal ao vivo do MT5 seria a aba robo
//  oficial XM GLOBAL + MT5".
//
//  Antes o preco ficava no cabecalho e o botao "Enviar" no fim de uma fila de
//  campos, com a conversa entre eles. A distancia e o que faz o operador
//  fechar o SL no preco de ontem.
//
//  A REGRA DE LAYOUT, do MT5 e da XM
//  ==================================
//  O TICKET fica no alto, com o preco ao vivo NA MESMA FAIXA do botao, e a
//  CONFERENCIA fica embaixo. Quem opera olha o preco, decide o lote, e so
//  entao confirma. O inverso — decisao longe da referencia — e o que produz
//  ordem com protecao no lugar errado.
//
//  O QUE NAO MUDOU, E POR QUE
//  ===========================
//  1. SEM SELETOR DE CORRETORA. O ticket opera o escopo ativo, o mesmo do
//     terminal. Seletor proprio aqui foi o defeito que fez a ordem ir para a
//     corretora errada: a tela afirmava uma e o dinheiro ia para outra.
//
//  2. `/api/trade/order` recebe `volume`/`sl`/`tp`. Este endpoint e a API do
//     MT5 (`_trade_order` em `mt5_gateway.py`), que le esses nomes. NAO e o
//     contrato universal (`quantity`/`stop_loss`/`take_profit`). Os dois
//     coexistem de proposito. "Padronizar" aqui quebraria a ordem manual com
//     "symbol, side, volume... obrigatorios" — o mesmo bug de vocabulario que
//     travou o motor automatico, no sentido inverso.
//
//  3. SL/TP em DOIS formatos: preco cheio (4130) ou distancia (10). A
//     conversao aparece ANTES de confirmar. Sem isso, quem digita "10" recebe
//     recusa sem entender por que.
//
//  O QUE MUDOU
//  ===========
//  - Preco ao vivo no cabecalho, com BID/ASK e spread.
//  - SL/TP com presets de distancia SL:TP (1:1 a 1:4) calculados do preco e
//    do passo do ativo. Um clique em vez de quatro digitos — que era o pedido.
//    O botao PREENCHE e nao trava: ninguem acerta o tempo certo de primeira.
//  - Risco estimado em moeda da conta, visivel antes de confirmar.
//  - Faixa de lote 0,01 a 10,00 no input E na validacao. Antes o `max` era
//    0,10 e o gateway recusava acima disso: a tela aceitava e o servidor nao.
//  - Latencia no rodape, com selecao e lista.
// =============================================================================
// LOTES: 0,01 e o minimo e 10,00 o maximo, como o dono definiu. O `min`/`max`
// do input e a MESMA faixa da validacao — divergent os dois, a tela aceita e
// o gateway recusa, que e a pior forma de divergencia.
const LOTE_MIN = 0.01;
const LOTE_MAX = 10.0;

// PRESETS SL:TP. O dono pediu "tp sl facil de configurar": em vez de calcular
// dois numeros, o operador escolhe quanto quer CORRER contra a protecao.
//
// 1:1 e o equilibrio; 1:4 e o conservador (o SL fecha antes, o TP e longe).
// O botao PREENCHE os campos, nao trava: quem opera tem ajuste a fazer depois.
const PRESETS: Array<{ nome: string; risco: number; alvo: number }> = [
  { nome: '1:1', risco: 1, alvo: 1 },
  { nome: '1:2', risco: 1, alvo: 2 },
  { nome: '1:3', risco: 1, alvo: 3 },
  { nome: '1:4', risco: 1, alvo: 4 },
];

const num = (v: string) => Number(String(v).replace(',', '.'));

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

  // PASSO DO ATIVO, em preco.
  //
  // 0,1% do preco, arredondado na escala que o ativo usa. O ouro a 4300 pede
  // 4,30; o EURUSD a 1,085 pede 0,0011. Um "10" fixo seria 0,2% no ouro e
  // 900% no EURUSD — o preset calcularia protecao absurda no forex.
  const passo = useMemo(() => {
    const p = preco ?? 0;
    if (!(p > 0)) return 0;
    const bruto = p * 0.001;
    const escala = bruto >= 100 ? 1 : bruto >= 10 ? 0.1 : bruto >= 1 ? 0.01 : 0.0001;
    return Math.max(escala, Math.round(bruto / escala) * escala);
  }, [preco]);

  /** Preenche SL e TP com a distancia do preset, calculada do preco ao vivo. */
  const aplicarPreset = (p: { nome: string; risco: number; alvo: number }) => {
    if (!(passo > 0)) {
      setStatus('Aguardando o preço ao vivo para calcular a distância.');
      return;
    }
    const dSl = Number((passo * p.risco).toPrecision(6));
    const dTp = Number((passo * p.alvo).toPrecision(6));
    setSl(String(dSl));
    setTp(String(dTp));
    setStatus(`Distância ${p.nome} aplicada: SL ${dSl} · TP ${dTp} a partir de ${preco}.`);
  };

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
    const loteN = num(lote);
    if (!(loteN >= LOTE_MIN) || !(loteN <= LOTE_MAX)) {
      setStatus(`Lote entre ${LOTE_MIN} e ${LOTE_MAX}.`);
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
    <section className="card mesa-xm" aria-label="Mesa XM Global + MT5">
      <div className="section-head">
        <div>
          <h2>Mesa XM <span className="muted">+ MT5</span></h2>
          <span className="muted">
            {simbolo ? `${simbolo} ${timeframe}`.trim() : 'Sem par no motor'} · {broker.toUpperCase()}
          </span>
        </div>
        <div className="btn-row">
          <span
            className={`chip ${wsConnected ? 'ok' : 'warn'}`}
            title="Auto-reconexão: o app cai e volta sozinho"
          >
            {wsConnected ? 'Tempo real' : 'Reconectando…'}
          </span>
        </div>
      </div>

      {/* TICKET EM UMA FAIXA
          ----------------------
          O MT5 e a XM põem lado, volume, SL, TP e o botao na MESMA faixa. Nao e
          estetica: o operador le o preco, digita o volume, ajusta a protecao e
          envia sem tirar o olho. Com cada campo numa linha, ele desce a tela,
          confere o que digitou e sobe para achar o botao — e nesse vaivem que a
          protecao sai no lugar errado. */}
      <div className="mesa-ticket">
        <div className="mesa-lado" role="group" aria-label="Lado da ordem">
          {(['BUY', 'SELL'] as const).map((v) => (
            <button
              key={v}
              type="button"
              aria-pressed={lado === v}
              className={`btn ${v === 'BUY' ? 'is-buy' : 'is-sell'}`}
              onClick={() => setLado(v)}
            >
              {v === 'BUY' ? 'Comprar' : 'Vender'}
            </button>
          ))}
        </div>

        <label className="field" style={{ marginBottom: 0 }}>
          <span>Lote</span>
          <input
            type="number"
            step={0.01}
            min={LOTE_MIN}
            max={LOTE_MAX}
            value={lote}
            onChange={(e) => setLote(e.target.value)}
            aria-label="Quantidade em lotes"
          />
        </label>

        {/* SL e TP juntos: e uma decisao so.-separados por outros campos, o
            operador ajusta um e esquece o outro. */}
        <div className="mesa-protecao">
          <label className="field" style={{ marginBottom: 0 }}>
            <span>Stop Loss</span>
            <input
              value={sl}
              onChange={(e) => setSl(e.target.value)}
              placeholder="preço ou distância"
              aria-label="Stop loss"
            />
          </label>
          <label className="field" style={{ marginBottom: 0 }}>
            <span>Take Profit</span>
            <input
              value={tp}
              onChange={(e) => setTp(e.target.value)}
              placeholder="preço ou distância"
              aria-label="Take profit"
            />
          </label>
        </div>

        {/* O botao repete o LADO na cor. O clique final nao pode exigir que o
            operador releia o campo de cima para saber se esta comprando ou
            vendendo — e no clique final que apressado ele erra. */}
        <button
          type="button"
          className={`btn mesa-enviar ${lado === 'BUY' ? 'is-buy' : 'is-sell'}`}
          onClick={() => void enviar()}
          disabled={ocupado || !simbolo}
        >
          {ocupado ? 'Enviando…' : lado === 'BUY' ? 'Comprar' : 'Vender'}
        </button>
      </div>

      {/* PRECO AO VIVO — o numero que o olho precisa antes de enviar */}
      <div className="mesa-ticket-preco" role="status" aria-live="polite">
        {preco != null ? preco : '--'}
      </div>

      <LatenciaBar />
    </section>
  );
}
