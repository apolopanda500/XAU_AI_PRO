import { offsetMinutos, horaNaZona, rotuloOffset } from '../lib/fuso';
import { zonaAtual } from '../hooks/useFuso';
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

  /*
    O FUSO ESCOLHIDO PELA TELA (05/10/2026)

    MEDIDO na XM: o rodape mostra `21:01:24 UTC-3` — o OFFSET, nao a cidade, e
    `auto` em azul como padrao. Antes isto era
    `Intl.DateTimeFormat().resolvedOptions().timeZone`, ou seja, o fuso do
    NAVEGADOR e nada mais: nao havia escolha nenhuma para o dono fazer.

    A hora tambem mudou de origem: era `now.getHours()`, que ignora a escolha.
  */
  const zona = zonaAtual();

  const pad = (n: number) => n.toString().padStart(2, '0');

  /*
    A HORA vem de `horaNaZona(zona)`, e nao de `now.getHours()`.

    MEDIDO: `getHours()` devolve a hora do NAVEGADOR, que ignora a escolha. Com
    o fuso em Londres e o navegador em Sao Paulo, o relogio marcaria a hora de
    Sao Paulo enquanto o rotulo diria `UTC+1` — relogio e rotulo discordando na
    mesma linha, que e o pior formato possivel.
  */
  const hhmm = horaNaZona(zona, now).split(':');
  const hours = hhmm[0];
  const minutes = hhmm[1];
  const seconds = hhmm[2];

  /** `UTC-3` — o que a XM escreve no rodape. */
  const rotuloFuso = rotuloOffset(offsetMinutos(zona, now));

  const dateStr = new Intl.DateTimeFormat('pt-BR', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: zona,
  }).format(now);


  if (compact) {
    return (
      <div className="quantum-clock-compact">
        <span className="clock-icon">🕐</span>
        <span className="clock-time">
          {hours}:{minutes}
        </span>
        {showSeconds && <span className="clock-secs">{seconds}</span>}
        <span className="clock-fuso">{rotuloFuso}</span>
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
        <div className="clock-tz">{zona}</div>
      </div>
      <div className="clock-leds">
        {Array.from({ length: 12 }).map((_, i) => (
          <span key={i} className={`clock-led ${i % 2 === 0 ? 'on' : ''}`} />
        ))}
      </div>
              <span className="clock-fuso">{rotuloFuso}</span>
</div>
  );
};

export default QuantumClock;
