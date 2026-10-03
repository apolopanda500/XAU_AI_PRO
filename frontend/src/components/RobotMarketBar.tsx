// Referencia de mercado dentro da aba Robo.
//
// POR QUE FICOU AQUI E NAO EM UMA ABA SOLTA
// ===========================================
// Operar exige ver o preco no mesmo lugar onde se clica em comprar. Com o
// mercado em outra aba, o operador alternava entre duas telas e a cotacao que
// viu podia ser de outro ativo. Aqui a faixa le o MESMO `selectedSymbol` que o
// painel de execucao usa, entao o preco mostrado e o ativo que sera operado.
import { useCallback, useEffect, useMemo, useState } from 'react';
import { getQuotes, normalizeMarketSource, type MarketQuote, type MarketSource } from '../lib/marketApi';
import { escopoAtivo } from '../lib/escopoAtivo';
import { brokerLabel, MARKET_LABELS } from '../lib/brokerCatalog';
import { useAppStore } from '../hooks/useAppStore';
import { formatNumber, formatTime, isMarketStale } from '../lib/marketFormat';
import '../theme/robot-market-bar.css';

const REFRESH_MS = 2_000;

export default function RobotMarketBar() {
  const selectedSymbol = useAppStore((state) => state.selectedSymbol);
  const setSelectedSymbol = useAppStore((state) => state.setSelectedSymbol);
  const escopo = escopoAtivo();
  // `normalizeMarketSource` recebe broker e mercado em separado e devolve
  // `null` para fonte desativada. O fallback e o mesmo usado pela leitura de
  // mercado: sem fallback, uma conta desativada deixaria a faixa sem preco.
  const source = useMemo(
    () => normalizeMarketSource(escopo.broker, escopo.market) ?? { broker: 'mt5', market: 'other' } as MarketSource,
    [escopo.broker, escopo.market],
  );
  const [quote, setQuote] = useState<MarketQuote | null>(null);
  const [age, setAge] = useState<number | null>(null);
  const [agora, setAgora] = useState(() => Date.now());
  const [erro, setErro] = useState('');

  const simbolo = (selectedSymbol || 'XAUUSD').toUpperCase();

  const carregar = useCallback(async (signal: AbortSignal) => {
    if (!simbolo) return;
    const resposta = await getQuotes(source, [simbolo], { signal });
    setQuote(resposta.quotes.find((item) => item.symbol.toUpperCase() === simbolo) ?? null);
    setAge(Date.now());
    setErro('');
  }, [source, simbolo]);

  useEffect(() => {
    const controller = new AbortController();
    setQuote(null);
    setErro('');
    const tick = () => { void carregar(controller.signal).catch(() => { if (!controller.signal.aborted) setErro('Gateway indisponível'); }); };
    void tick();
    const timer = window.setInterval(tick, REFRESH_MS);
    return () => { controller.abort(); window.clearInterval(timer); };
  }, [carregar]);

  // O relogio de staleness roda em 1s: sem isso a faixa marcaria "vencida" com
  // o tempo de espera da proxima leitura e piscaria sem motivo.
  useEffect(() => {
    const timer = window.setInterval(() => setAgora(Date.now()), 1_000);
    return () => window.clearInterval(timer);
  }, []);

  const vencida = age !== null && isMarketStale(age, agora);
  const temPreco = Boolean(quote && (quote.bid !== null || quote.ask !== null || quote.last !== null));

  return (
    <section className="card compact-card robot-market-bar" aria-label="Mercado do ativo selecionado">
      <div className="rmb-top">
        <button
          type="button"
          className="rmb-symbol"
          onClick={() => {
            const next = window.prompt('Ativo para operar', simbolo);
            if (next?.trim()) setSelectedSymbol(next.trim().toUpperCase());
          }}
          title="Clique para trocar o ativo"
        >
          {simbolo || '—'}
        </button>
        <span className="muted">{brokerLabel(source.broker)} · {MARKET_LABELS[source.market] ?? source.market}</span>
        <span className={`chip ${temPreco && !vencida ? 'ok' : 'warn'}`}>
          {erro ? 'sem gateway' : !temPreco ? 'sem preço' : vencida ? 'vencida' : 'ao vivo'}
        </span>
        <span className="muted rmb-time">{quote?.received_at ? formatTime(quote.received_at) : '--:--:--'}</span>
      </div>
      <div className="rmb-quotes">
        <div><em>Último</em><strong className="num">{formatNumber(quote?.last)}</strong></div>
        <div><em>Compra</em><strong className="num">{formatNumber(quote?.bid)}</strong></div>
        <div><em>Venda</em><strong className="num">{formatNumber(quote?.ask)}</strong></div>
        <div><em>Spread</em><strong className="num">{formatNumber(quote?.spread)}</strong></div>
      </div>
    </section>
  );
}
