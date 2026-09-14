/**
 * MiningRig — Visual de rig de mineração animado
 * GPUs com LEDs piscando, hashrate, temperatura, ventoinhas
 */

import React, { useEffect, useState } from 'react';

interface Props {
  hashrate?: number;       // MH/s
  temperature?: number;    // °C
  fanSpeed?: number;       // RPM
  powerUsage?: number;     // Watts
  accepted?: number;       // shares aceitos
  rejected?: number;       // shares rejeitados
  uptime?: number;         // segundos
  compact?: boolean;
}

export const MiningRig: React.FC<Props> = ({
  hashrate = 0,
  temperature = 0,
  fanSpeed = 0,
  powerUsage = 0,
  accepted = 0,
  rejected = 0,
  uptime = 0,
  compact = false,
}) => {
  const [leds, setLeds] = useState<boolean[]>(Array(8).fill(false));
  const [gpuLeds, setGpuLeds] = useState<boolean[]>(Array(6).fill(false));

  // LEDs piscando aleatoriamente (simula atividade de mineração)
  useEffect(() => {
    const interval = setInterval(() => {
      setLeds(prev => prev.map(() => Math.random() > 0.3));
      setGpuLeds(prev => prev.map(() => Math.random() > 0.4));
    }, 150);
    return () => clearInterval(interval);
  }, []);

  const fmtUptime = (s: number) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    return `${h}h ${m}m`;
  };

  if (compact) {
    return (
      <div className="mining-rig-compact">
        <div className="mining-hashrate">
          <span className="mining-hash-icon">⛏️</span>
          <span className="mining-hash-value">{hashrate.toFixed(1)}</span>
          <span className="mining-hash-unit">MH/s</span>
        </div>
        <div className="mining-temp-badge" style={{
          color: temperature > 80 ? '#ef4444' : temperature > 70 ? '#f59e0b' : '#22c55e'
        }}>
          {temperature}°C
        </div>
        <div className="mining-leds-row">
          {leds.slice(0, 6).map((on, i) => (
            <span key={i} className={`mining-led ${on ? 'on' : 'off'}`} />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="mining-rig">
      {/* Header do Rig */}
      <div className="mining-rig-header">
        <div className="mining-rig-title">
          <span className="mining-rig-icon">⛏️</span>
          <span>MINING RIG</span>
        </div>
        <div className="mining-rig-status">
          <span className={`mining-status-dot ${hashrate > 0 ? 'active' : 'idle'}`} />
          <span className="mining-status-text">{hashrate > 0 ? 'MINING' : 'IDLE'}</span>
        </div>
      </div>

      {/* Corpo do Rig - GPUs */}
      <div className="mining-gpus">
        {[0, 1, 2, 3].map((gpu) => (
          <div key={gpu} className="mining-gpu">
            <div className="mining-gpu-body">
              <div className="mining-gpu-fans">
                <span className="mining-fan spinning">🌀</span>
                <span className="mining-fan spinning-reverse">🌀</span>
              </div>
              <div className="mining-gpu-leds">
                {gpuLeds.map((on, i) => (
                  <span key={i} className={`gpu-led ${on ? 'led-green' : 'led-off'}`} />
                ))}
              </div>
              <div className="mining-gpu-label">GPU {gpu + 1}</div>
              <div className="mining-gpu-hash">{(hashrate / 4 + Math.random() * 5).toFixed(1)} MH/s</div>
            </div>
          </div>
        ))}
      </div>

      {/* Stats do Rig */}
      <div className="mining-stats">
        <div className="mining-stat">
          <span className="mining-stat-label">HASHRATE</span>
          <span className="mining-stat-value hash-value">{hashrate.toFixed(2)} <small>MH/s</small></span>
        </div>
        <div className="mining-stat">
          <span className="mining-stat-label">TEMP</span>
          <span className={`mining-stat-value ${temperature > 80 ? 'danger' : temperature > 70 ? 'warn' : 'ok'}`}>
            {temperature}°C
          </span>
        </div>
        <div className="mining-stat">
          <span className="mining-stat-label">FAN</span>
          <span className="mining-stat-value">{fanSpeed} <small>RPM</small></span>
        </div>
        <div className="mining-stat">
          <span className="mining-stat-label">POWER</span>
          <span className="mining-stat-value">{powerUsage} <small>W</small></span>
        </div>
      </div>

      {/* Shares */}
      <div className="mining-shares">
        <div className="mining-share accepted">
          <span className="share-dot green" />
          <span>Accepted: {accepted}</span>
        </div>
        <div className="mining-share rejected">
          <span className="share-dot red" />
          <span>Rejected: {rejected}</span>
        </div>
        <div className="mining-share uptime">
          <span>⏱️ {fmtUptime(uptime)}</span>
        </div>
      </div>

      {/* LEDs de atividade */}
      <div className="mining-activity-bar">
        {leds.map((on, i) => (
          <span key={i} className={`activity-led ${on ? 'active' : ''}`} />
        ))}
      </div>
    </div>
  );
};

export default MiningRig;
