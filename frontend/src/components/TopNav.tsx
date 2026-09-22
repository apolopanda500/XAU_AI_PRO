import React from 'react';
import { useAppStore, TabType } from '../hooks/useAppStore';
import QuantumClock from './QuantumClock';


const TABS: [TabType, string, string][] = [
  ['dashboard', 'Painel', 'dashboard'],
  ['portfolio', 'Patrimônio', 'wallet'],
  ['robot', 'Robô', 'robot'],
  ['history', 'Histórico', 'history'],
];

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
