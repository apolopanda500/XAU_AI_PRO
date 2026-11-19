// ===========================================================================
//  GRADE DE MODELOS 3D — PERFIS DINÂMICOS POR ATIVO (18/11/2026)
// ===========================================================================
//  ZERO ATIVO FIXO / ZERO MARCAS EXTERNAS
//  Os perfis vêm EXCLUSIVAMENTE do catálogo conectado (via
//  GET /api/models/asset-profiles) e do model_manifest.json real.
//  A cor do emblema é escolhida pela CLASSE do ativo, nunca pelo nome.
//  A inclinação 3D é GPU-only, desligada com prefers-reduced-motion.
// ===========================================================================
import React, { useCallback, useState } from 'react';

export interface DynamicAssetModelProfile {
  symbol: string;
  assetClass: string;
  timeframe: string;
  modelId: string;
  rocAuc: number;
  precisionPct: number;
  featureCount: number;
  requirements: {
    minAtrPoints: number;
    maxSpreadPoints: number;
    minAdx: number;
    preferredSession: string;
  };
  liveStatus: 'READY' | 'HIGH_SPREAD_VETO' | 'LOW_VOLATILITY';
}

interface ModelCard3DItemProps {
  profile: DynamicAssetModelProfile;
  onSelectForChart: (symbol: string) => void;
}

export function getClassPalette(assetClass: string): { accent: string; glow: string; tag: string } {
  const key = assetClass.toUpperCase();
  if (key.includes('METAL')) return { accent: '#f59e0b', glow: 'rgba(245, 158, 11, 0.22)', tag: 'METAIS' };
  if (key.includes('INDEX') || key.includes('INDICE')) return { accent: '#38bdf8', glow: 'rgba(56, 189, 248, 0.22)', tag: 'ÍNDICES' };
  if (key.includes('CRYPTO')) return { accent: '#a855f7', glow: 'rgba(168, 85, 247, 0.22)', tag: 'CRIPTO' };
  return { accent: '#10b981', glow: 'rgba(16, 185, 129, 0.22)', tag: 'CÂMBIO' };
}

const STATUS: Record<DynamicAssetModelProfile['liveStatus'], { label: string; color: string }> = {
  READY: { label: 'APTO PARA OPERAR', color: '#10b981' },
  HIGH_SPREAD_VETO: { label: 'VETO DE SPREAD', color: '#f59e0b' },
  LOW_VOLATILITY: { label: 'BAIXA VOLATILIDADE', color: '#f59e0b' },
};

function motionPermitida(): boolean {
  try {
    return !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return true;
  }
}

const ModelCard3DItem: React.FC<ModelCard3DItemProps> = ({ profile, onSelectForChart }) => {
  const [tilt, setTilt] = useState<{ rx: number; ry: number }>({ rx: 0, ry: 0 });
  const palette = getClassPalette(profile.assetClass);
  const status = STATUS[profile.liveStatus] ?? STATUS.LOW_VOLATILITY;

  const handlePointerMove = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    if (!motionPermitida()) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width - 0.5;
    const y = (e.clientY - rect.top) / rect.height - 0.5;
    setTilt({ rx: Number((-y * 8).toFixed(2)), ry: Number((x * 10).toFixed(2)) });
  }, []);
  const resetTilt = useCallback(() => setTilt({ rx: 0, ry: 0 }), []);

  return (
    <div onMouseMove={handlePointerMove} onMouseLeave={resetTilt} style={{ perspective: '900px' }}>
      <div style={{
        background: 'linear-gradient(145deg, #0f172a 0%, #070b14 100%)',
        border: `1px solid ${palette.glow}`, borderRadius: '14px', padding: '14px',
        boxShadow: `0 10px 28px -8px ${palette.glow}, inset 0 1px 0 rgba(255,255,255,0.06)`,
        transform: `rotateX(${tilt.rx}deg) rotateY(${tilt.ry}deg) translateZ(0)`,
        transition: tilt.rx === 0 && tilt.ry === 0 ? 'transform 0.25s ease' : 'transform 0.06s linear',
        willChange: 'transform',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <div>
            <span style={{ fontSize: '10px', fontWeight: 800, padding: '2px 8px', borderRadius: '4px', background: palette.glow, color: palette.accent, letterSpacing: '0.05em' }}>
              {palette.tag} · {profile.timeframe}
            </span>
            <h4 style={{ fontSize: '16px', fontWeight: 900, color: '#f8fafc', margin: '4px 0 0 0' }}>{profile.symbol}</h4>
          </div>
          <span className="badge" style={{ fontSize: '10px', padding: '3px 8px', borderRadius: '999px', background: 'rgba(15, 23, 42, 0.9)', border: `1px solid ${status.color}`, color: status.color, fontWeight: 700 }}>● {status.label}</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', padding: '8px', borderRadius: '8px', background: 'rgba(5, 8, 16, 0.75)', border: '1px solid rgba(148, 163, 184, 0.1)', marginBottom: '10px', textAlign: 'center' }}>
          <div><div style={{ fontSize: '10px', color: '#94a3b8' }}>ROC-AUC</div><div className="kpi-number" style={{ fontSize: '13px', fontWeight: 800, color: palette.accent }}>{profile.rocAuc.toFixed(3)}</div></div>
          <div><div style={{ fontSize: '10px', color: '#94a3b8' }}>PRECISÃO</div><div className="kpi-number" style={{ fontSize: '13px', fontWeight: 800, color: '#10b981' }}>{profile.precisionPct.toFixed(1)}%</div></div>
          <div><div style={{ fontSize: '10px', color: '#94a3b8' }}>FEATURES</div><div className="kpi-number" style={{ fontSize: '13px', fontWeight: 800, color: '#38bdf8' }}>{profile.featureCount}D</div></div>
        </div>
        <div style={{ fontSize: '11px', color: '#cbd5e1', display: 'flex', flexDirection: 'column', gap: '4px', marginBottom: '12px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: '#94a3b8' }}>Spread Máximo Aceito:</span><strong>{profile.requirements.maxSpreadPoints} pts</strong></div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: '#94a3b8' }}>ATR Mínimo / ADX:</span><strong>{profile.requirements.minAtrPoints} pts · ADX ≥ {profile.requirements.minAdx}</strong></div>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: '#94a3b8' }}>Janela de Liquidez:</span><strong>{profile.requirements.preferredSession}</strong></div>
        </div>
        <button type="button" onClick={() => onSelectForChart(profile.symbol)} style={{ width: '100%', background: palette.glow, border: `1px solid ${palette.accent}`, color: palette.accent, fontWeight: 800 }}>
          Abrir {profile.symbol} no Gráfico →
        </button>
      </div>
    </div>
  );
};

export const ModelCards3DGrid: React.FC<{ profiles: DynamicAssetModelProfile[]; onSelectSymbol: (symbol: string) => void }> = ({ profiles, onSelectSymbol }) => {
  if (!profiles.length) {
    return <div className="panel-box" style={{ padding: '16px', textAlign: 'center', color: '#94a3b8' }}>Aguardando catálogo dinâmico de ativos do Gateway para montar os cards 3D...</div>;
  }
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '12px' }}>
      {profiles.map((prof) => <ModelCard3DItem key={prof.symbol} profile={prof} onSelectForChart={onSelectSymbol} />)}
    </div>
  );
};

export default ModelCards3DGrid;
