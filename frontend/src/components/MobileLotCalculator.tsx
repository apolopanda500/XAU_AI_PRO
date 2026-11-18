import React, { useState } from 'react';

export const MobileLotCalculator: React.FC<{ defaultBalance?: number }> = ({ defaultBalance = 13038.61 }) => {
  const [balance, setBalance] = useState<number>(defaultBalance);
  const [riskPct, setRiskPct] = useState<number>(0.5);
  const [stopPoints, setStopPoints] = useState<number>(250);
  const [tickValuePerLot, setTickValuePerLot] = useState<number>(1.0); // XAUUSD padrão

  const riskUsd = (balance * riskPct) / 100;
  const rawLot = stopPoints > 0 && tickValuePerLot > 0 ? riskUsd / (stopPoints * tickValuePerLot) : 0;
  const safeLot = Math.max(0.01, Math.floor(rawLot * 100) / 100);

  return (
    <div style={{ padding: '12px', borderRadius: '12px', background: '#0f172a', border: '1px solid #1e293b', marginTop: '12px' }}>
      <h4 style={{ fontSize: '13px', fontWeight: 700, color: '#f59e0b', marginBottom: '10px', marginTop: 0 }}>
        CALCULADORA DE LOTE & RISCO (XAU/USD)
      </h4>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
        <label style={{ color: '#94a3b8' }}>
          Banca (USD)
          <input
            type="number"
            value={balance}
            onChange={(e) => setBalance(parseFloat(e.target.value) || 0)}
            style={{ width: '100%', marginTop: '4px', padding: '6px', borderRadius: '6px', background: '#090d16', border: '1px solid #334155', color: '#fff' }}
          />
        </label>

        <label style={{ color: '#94a3b8' }}>
          Risco (%)
          <input
            type="number"
            step="0.1"
            value={riskPct}
            onChange={(e) => setRiskPct(parseFloat(e.target.value) || 0)}
            style={{ width: '100%', marginTop: '4px', padding: '6px', borderRadius: '6px', background: '#090d16', border: '1px solid #334155', color: '#fff' }}
          />
        </label>

        <label style={{ color: '#94a3b8' }}>
          Stop Loss (Pontos)
          <input
            type="number"
            value={stopPoints}
            onChange={(e) => setStopPoints(parseFloat(e.target.value) || 0)}
            style={{ width: '100%', marginTop: '4px', padding: '6px', borderRadius: '6px', background: '#090d16', border: '1px solid #334155', color: '#fff' }}
          />
        </label>

        <label style={{ color: '#94a3b8' }}>
          Valor/Ponto (1.0 Lote)
          <input
            type="number"
            step="0.1"
            value={tickValuePerLot}
            onChange={(e) => setTickValuePerLot(parseFloat(e.target.value) || 0)}
            style={{ width: '100%', marginTop: '4px', padding: '6px', borderRadius: '6px', background: '#090d16', border: '1px solid #334155', color: '#fff' }}
          />
        </label>
      </div>

      <div
        style={{
          marginTop: '12px',
          padding: '10px',
          borderRadius: '8px',
          background: '#090d16',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 12,
        }}
      >
        <div>
          <div style={{ fontSize: '11px', color: '#94a3b8' }}>Risco Máximo</div>
          <div style={{ fontSize: '15px', fontWeight: 700, color: '#f87171' }}>${riskUsd.toFixed(2)} USD</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8' }}>Lote Recomendado</div>
          <div style={{ fontSize: '18px', fontWeight: 800, color: '#10b981' }}>{safeLot.toFixed(2)}</div>
        </div>
      </div>
    </div>
  );
};

export default MobileLotCalculator;
