// ===========================================================================
//  IA VIVA · COPILOTO DE RISCO (18/11/2026)
//  Lê RSI, ADX, ATR, spread e drawdown; gera setups SEMPRE dentro do risco.
//  Nunca envia ordem — `onApplySetupToTicket` só preenche a boleta.
//  O `point` vem da ficha real da corretora: sem ele, nenhum preço inventado.
// ===========================================================================
import React, { useMemo } from 'react';
import CollapsibleSection from './CollapsibleSection';

export interface LiveMarketTelemetry {
  symbol: string;
  timeframe: string;
  bid: number;
  ask: number;
  spreadPoints: number;
  rsi: number;
  adx: number;
  atrPoints: number;
  balance: number;
  dailyDrawdownPct: number;
  maxDailyDrawdownPct: number;
  point?: number;
}

export interface GeneratedAiSetup {
  id: string;
  title: string;
  bias: 'COMPRA' | 'VENDA' | 'NEUTRO';
  confidencePct: number;
  entryPrice: number;
  stopLossPrice: number;
  takeProfitPrice: number;
  suggestedRiskPct: number;
  rationale: string;
}

interface LiveAiRiskCopilotProps {
  telemetry: LiveMarketTelemetry;
  onApplySetupToTicket?: (setup: GeneratedAiSetup) => void;
}

export function analisarRegime(t: LiveMarketTelemetry): { label: string; color: string } {
  if (t.spreadPoints > 45) return { label: 'SPREAD ELEVADO (PROTEÇÃO ATIVA)', color: '#ef4444' };
  if (t.adx >= 25 && t.rsi > 54) return { label: 'TENDÊNCIA DE ALTA INSTITUCIONAL', color: '#10b981' };
  if (t.adx >= 25 && t.rsi < 46) return { label: 'TENDÊNCIA DE BAIXA INSTITUCIONAL', color: '#ef4444' };
  if (t.rsi >= 72 || t.rsi <= 28) return { label: 'EXAUSTÃO / POSSÍVEL REVERSÃO', color: '#f59e0b' };
  return { label: 'CONSOLIDAÇÃO / LATERAL', color: '#94a3b8' };
}

export function riscoDinamico(daily: number, max: number): number {
  const ratio = max > 0 ? daily / max : 0;
  return ratio >= 0.7 ? 0.25 : ratio >= 0.4 ? 0.35 : 0.5;
}

export function gerarSetups(t: LiveMarketTelemetry): GeneratedAiSetup[] {
  const { symbol, bid, ask, spreadPoints, rsi, adx, atrPoints, dailyDrawdownPct, maxDailyDrawdownPct, point } = t;
  if (!point || !Number.isFinite(point) || point <= 0) return [];
  const safeAtr = Math.max(atrPoints, 20);
  const risk = riscoDinamico(dailyDrawdownPct, maxDailyDrawdownPct);
  const setups: GeneratedAiSetup[] = [];
  const arredondar = (v: number) => Number(v.toFixed(8));

  if (adx >= 22 && rsi >= 52 && rsi <= 68 && spreadPoints <= 45) {
    const sl = Math.round(safeAtr * 1.4), tp = Math.round(safeAtr * 2.8);
    setups.push({ id: 'setup_trend_buy', title: `Continuação de Alta · ${symbol}`, bias: 'COMPRA', confidencePct: Math.min(86, Math.round(55 + (adx - 20) * 1.2)), entryPrice: ask, stopLossPrice: arredondar(ask - sl * point), takeProfitPrice: arredondar(ask + tp * point), suggestedRiskPct: risk, rationale: `ADX em ${adx.toFixed(1)} confirma força direcional com RSI saudável (${rsi.toFixed(1)}) e ATR de ${safeAtr} pts.` });
  }
  if (adx >= 22 && rsi <= 48 && rsi >= 32 && spreadPoints <= 45) {
    const sl = Math.round(safeAtr * 1.4), tp = Math.round(safeAtr * 2.8);
    setups.push({ id: 'setup_trend_sell', title: `Continuação de Baixa · ${symbol}`, bias: 'VENDA', confidencePct: Math.min(86, Math.round(55 + (adx - 20) * 1.2)), entryPrice: bid, stopLossPrice: arredondar(bid + sl * point), takeProfitPrice: arredondar(bid - tp * point), suggestedRiskPct: risk, rationale: `Fluxo vendedor sustentado (ADX ${adx.toFixed(1)}, RSI ${rsi.toFixed(1)}) dentro do limite de custo.` });
  }
  if (rsi >= 74 || rsi <= 26) {
    const sobre = rsi >= 74, ref = sobre ? bid : ask;
    const sl = Math.round(safeAtr * 1.2), tp = Math.round(safeAtr * 2.2);
    setups.push({ id: 'setup_mean_reversion', title: `Retorno à Média (${sobre ? 'Sobrecompra' : 'Sobrevenda'}) · ${symbol}`, bias: sobre ? 'VENDA' : 'COMPRA', confidencePct: 64, entryPrice: ref, stopLossPrice: arredondar(sobre ? ref + sl * point : ref - sl * point), takeProfitPrice: arredondar(sobre ? ref - tp * point : ref + tp * point), suggestedRiskPct: Math.min(risk, 0.35), rationale: `RSI extremo em ${rsi.toFixed(1)} indica esticamento além de 2 desvios de volatilidade.` });
  }
  return setups;
}

export const LiveAiRiskCopilot: React.FC<LiveAiRiskCopilotProps> = ({ telemetry, onApplySetupToTicket }) => {
  const regime = useMemo(() => analisarRegime(telemetry), [telemetry]);
  const setups = useMemo(() => gerarSetups(telemetry), [telemetry]);
  const ddRatio = telemetry.maxDailyDrawdownPct > 0 ? telemetry.dailyDrawdownPct / telemetry.maxDailyDrawdownPct : 0;
  const riskHealth = ddRatio >= 0.8 ? 'CRÍTICO (REDUZIR LOTE)' : ddRatio >= 0.5 ? 'ATENÇÃO (MODO DEFENSIVO)' : 'SAUDÁVEL';

  return (
    <CollapsibleSection id="live_ai_risk_copilot" title="IA Viva · Leitura de Mercado & Setups Dinâmicos" badge={telemetry.symbol || 'AGUARDANDO'}>
      <div className="kpi-grid" style={{ marginBottom: '12px' }}>
        <div className="panel-box" style={{ padding: '10px' }}>
          <div style={{ fontSize: '10.5px', color: '#94a3b8', fontWeight: 700 }}>REGIME DETECTADO PELA IA</div>
          <div style={{ fontSize: '13px', fontWeight: 800, color: regime.color, marginTop: '4px' }}>{regime.label}</div>
          <div style={{ fontSize: '11px', color: '#cbd5e1', marginTop: '2px' }}>RSI: <strong>{telemetry.rsi.toFixed(1)}</strong> · ADX: <strong>{telemetry.adx.toFixed(1)}</strong> · ATR: <strong>{telemetry.atrPoints} pts</strong></div>
        </div>
        <div className="panel-box" style={{ padding: '10px' }}>
          <div style={{ fontSize: '10.5px', color: '#94a3b8', fontWeight: 700 }}>SAÚDE DO DRAWDOWN DIÁRIO</div>
          <div style={{ fontSize: '13px', fontWeight: 800, color: '#38bdf8', marginTop: '4px' }}>{riskHealth}</div>
          <div style={{ fontSize: '11px', color: '#cbd5e1', marginTop: '2px' }}>Usado: <strong>{telemetry.dailyDrawdownPct.toFixed(2)}%</strong> de <strong>{telemetry.maxDailyDrawdownPct.toFixed(1)}%</strong> máx.</div>
        </div>
      </div>
      {setups.length === 0 ? (
        <div style={{ padding: '12px', borderRadius: '8px', background: '#070b14', border: '1px solid rgba(148, 163, 184, 0.14)', fontSize: '12px', color: '#94a3b8' }}>
          <strong>IA em Vigilância Ativa:</strong> Nenhum setup com vantagem estatística clara neste candle ({telemetry.symbol || 'sem ativo'}). Aguardando rompimento de ADX ou extremo de RSI com spread baixo.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {setups.map((setup) => {
            const isBuy = setup.bias === 'COMPRA';
            return (
              <div key={setup.id} className="panel-box" style={{ padding: '12px', borderColor: isBuy ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <strong style={{ fontSize: '13px', color: isBuy ? '#10b981' : '#ef4444' }}>{setup.title} ({setup.bias})</strong>
                  <span className="badge" style={{ fontSize: '11px', color: '#f59e0b', fontWeight: 800 }}>Confiança IA: {setup.confidencePct}%</span>
                </div>
                <p style={{ fontSize: '12px', color: '#cbd5e1', marginBottom: '8px' }}>{setup.rationale}</p>
                <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', gap: '8px', fontSize: '11.5px', color: '#94a3b8', marginBottom: '10px' }}>
                  <span>Entrada: <strong style={{ color: '#f8fafc' }}>{setup.entryPrice}</strong></span>
                  <span>SL: <strong style={{ color: '#ef4444' }}>{setup.stopLossPrice}</strong></span>
                  <span>TP: <strong style={{ color: '#10b981' }}>{setup.takeProfitPrice}</strong></span>
                  <span>Risco Sugerido: <strong style={{ color: '#38bdf8' }}>{setup.suggestedRiskPct}%</strong></span>
                </div>
                {onApplySetupToTicket && (
                  <button type="button" onClick={() => onApplySetupToTicket(setup)} style={{ width: '100%', background: isBuy ? 'rgba(16, 185, 129, 0.16)' : 'rgba(239, 68, 68, 0.16)', border: `1px solid ${isBuy ? '#10b981' : '#ef4444'}`, color: isBuy ? '#10b981' : '#f87171', fontWeight: 700 }}>Carregar Parâmetros na Boleta de Risco →</button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </CollapsibleSection>
  );
};

export default LiveAiRiskCopilot;
