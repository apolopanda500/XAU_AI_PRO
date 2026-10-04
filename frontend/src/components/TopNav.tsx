import React from 'react';
import { useAppStore } from '../hooks/useAppStore';
import QuantumClock from './QuantumClock';

// A navegacao vive em Sidebar.tsx (ITEMS). Este arquivo usava declarar um
// TABS proprio com 4 entradas que nunca eram renderizadas — uma terceira lista
// de abas que divergia da Sidebar conforme as abas eram adicionadas.

export default function TopNav() {
  const wsConnected = useAppStore((s) => s.wsConnected);
  const aiStatus = useAppStore((s) => s.aiStatus);
  const robotStatus = useAppStore((s) => s.robotStatus);

  return (
    <header className="topbar">
      <div className="topnav-status">
        <span className="status">
          <i className={`dot ${wsConnected ? 'on' : ''}`} /> WS {wsConnected ? 'Online' : 'Offline'}
        </span>
        <span className="status">🤖 AI: {aiStatus}</span>
        <span className="status">EA: {robotStatus}</span>
        <QuantumClock compact showSeconds={false} showDate={false} />
      </div>
    </header>
  );
}
