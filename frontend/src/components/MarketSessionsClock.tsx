import React, { useEffect, useState } from 'react';

interface SessionInfo {
  name: string;
  openGmt: number;
  closeGmt: number;
}

const SESSIONS: SessionInfo[] = [
  { name: 'Sydney', openGmt: 22, closeGmt: 7 },
  { name: 'Tóquio (Ásia)', openGmt: 0, closeGmt: 9 },
  { name: 'Londres (UE)', openGmt: 8, closeGmt: 17 },
  { name: 'Nova York (EUA)', openGmt: 13, closeGmt: 22 },
];

function isSessionOpen(hourGmt: number, open: number, close: number): boolean {
  if (open < close) return hourGmt >= open && hourGmt < close;
  return hourGmt >= open || hourGmt < close;
}

export const MarketSessionsClock: React.FC = () => {
  const [now, setNow] = useState<Date>(() => new Date());

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 10000);
    return () => clearInterval(timer);
  }, []);

  const hourGmt = now.getUTCHours();
  const isGoldOverlap = hourGmt >= 13 && hourGmt < 17;

  return (
    <div style={{ padding: '12px', borderRadius: '12px', background: '#0f172a', border: '1px solid #1e293b' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px', gap: 8, flexWrap: 'wrap' }}>
        <span style={{ fontSize: '12px', fontWeight: 700, color: '#cbd5e1' }}>
          SESSÕES GLOBAIS ({now.toISOString().slice(11, 16)} GMT)
        </span>
        {isGoldOverlap && (
          <span
            style={{
              fontSize: '10px',
              fontWeight: 800,
              padding: '2px 8px',
              borderRadius: '999px',
              background: 'rgba(245, 158, 11, 0.15)',
              color: '#f59e0b',
              border: '1px solid rgba(245, 158, 11, 0.4)',
            }}
          >
            ALTA LIQUIDEZ XAU (LDN + NY)
          </span>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: '6px' }}>
        {SESSIONS.map((s) => {
          const active = isSessionOpen(hourGmt, s.openGmt, s.closeGmt);
          return (
            <div
              key={s.name}
              style={{
                padding: '6px 8px',
                borderRadius: '8px',
                background: active ? 'rgba(16, 185, 129, 0.12)' : '#090d16',
                border: `1px solid ${active ? 'rgba(16, 185, 129, 0.35)' : '#1e293b'}`,
                textAlign: 'center',
                minWidth: 0,
              }}
            >
              <div style={{ fontSize: '11px', fontWeight: 700, color: active ? '#10b981' : '#64748b' }}>
                {s.name.split(' ')[0]}
              </div>
              <div style={{ fontSize: '10px', color: active ? '#a7f3d0' : '#475569' }}>
                {active ? 'ABERTA' : 'FECHADA'}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default MarketSessionsClock;
