/**
 * QuantumClock — Relógio digital LED neon quântico
 * Hora, data, fuso, com efeito de brilho e dígitos animados
 */

import React, { useEffect, useState } from 'react';

interface Props {
  compact?: boolean;
  showSeconds?: boolean;
  showDate?: boolean;
}

export const QuantumClock: React.FC<Props> = ({
  compact = false,
  showSeconds = true,
  showDate = true,
}) => {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  const pad = (n: number) => n.toString().padStart(2, '0');

  const hours = pad(now.getHours());
  const minutes = pad(now.getMinutes());
  const seconds = pad(now.getSeconds());

  const dateStr = now.toLocaleDateString('pt-BR', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  });

  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;

  if (compact) {
    return (
      <div className="quantum-clock-compact">
        <span className="clock-icon">🕐</span>
        <span className="clock-time">{hours}:{minutes}</span>
        {showSeconds && <span className="clock-secs">{seconds}</span>}
      </div>
    );
  }

  return (
    <div className="quantum-clock">
      <div className="clock-display">
        <div className="clock-digits">
          <span className="clock-num">{hours}</span>
          <span className="clock-sep">:</span>
          <span className="clock-num">{minutes}</span>
          {showSeconds && (
            <>
              <span className="clock-sep">:</span>
              <span className="clock-num seconds">{seconds}</span>
            </>
          )}
        </div>
        <div className="clock-date">{dateStr}</div>
        <div className="clock-tz">{tz}</div>
      </div>
      <div className="clock-leds">
        {Array.from({ length: 12 }).map((_, i) => (
          <span key={i} className={`clock-led ${i % 2 === 0 ? 'on' : ''}`} />
        ))}
      </div>
    </div>
  );
};

export default QuantumClock;
