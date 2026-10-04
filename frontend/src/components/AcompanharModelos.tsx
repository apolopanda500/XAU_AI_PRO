import { useMemo } from 'react';
import { useAutoState } from '../hooks/queries';
import { useSinaisModelo } from '../hooks/useSinaisModelo';
import { getCandles, type MarketCandle } from '../lib/marketApi';
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
// - So leitura: nenhum botao aqui envia ordem. Quem opera e o motor (AUTO)
//   ou a mesa — este painel e conferencia.
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
  return (
    <section className="card compact-card" aria-label="Acompanhar modelos">
      <div className="section-head">
        <div>
          <h2>Acompanhar modelos</h2>
          <span className="muted">
            {simbolo} · {timeframe} · {broker.toUpperCase()}
            {desatualizado ? ` · desatualizado há ${idadeSeg}s` : ' · ao vivo'}
          </span>
        </div>
        <span className={`chip ${desatualizado ? 'warn' : 'ok'}`}>
          {sinais.length ? `${sinais.length} sinais` : 'aguardando sinal'}
        </span>
      </div>
      <PriceChart
        symbol={simbolo}
        broker={broker as never}
        market={market as never}
        timeframe={timeframe as never}
        candles={candles}
        markers={markers}
        error={erroVelas}
        sourceLabel={`${broker.toUpperCase()} · sinais do modelo`}
      />
      <div className="table-scroll">
        <table className="tbl compact-table dense-grid">
          <thead>
            <tr>
              <th>Hora</th>
              <th>Sinal</th>
              <th className="num">Confiança</th>
              <th className="num">Preço</th>
              <th>Modelo</th>
            </tr>
          </thead>
          <tbody>
            {sinais.slice(0, 8).map((s, i) => (
              <tr key={`${s.time}-${i}`}>
                <td className="mono">{new Date(s.time * 1000).toLocaleTimeString('pt-BR')}</td>
                <td>
                  <span className={`chip ${s.signal === 'BUY' ? 'ok' : s.signal === 'SELL' ? 'warn' : ''}`}>
                    {s.signal}
                  </span>
                </td>
                <td className="num">{s.confidence ?? '--'}%</td>
                <td className="num">{s.price ?? '--'}</td>
                <td className="muted">{s.model || s.motivo || '--'}</td>
              </tr>
            ))}
            {!sinais.length && (
              <tr>
                <td colSpan={5} className="mt-empty">
                  Nenhum sinal ainda — a primeira leitura chega em segundos.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
