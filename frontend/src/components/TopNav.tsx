import React from 'react';
import { useAppStore, TabType } from '../hooks/useAppStore';
import QuantumClock from './QuantumClock';
import { QuantumIcon } from './QuantumIcon';

const TABS: [TabType, string, string][] = [
  ['dashboard', 'Painel', 'dashboard'],
  ['market', 'Mercado', 'market'],
  ['robot', 'Robô', 'robot'],
  ['history', 'Histórico', 'history'],
  ['calendar', 'Calendário', 'calendar'],
  ['strategy-tester', 'Estratégia', 'strategy'],
];

export default function TopNav() {
  const activeTab = useAppStore((s) => s.activeTab);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const wsConnected = useAppStore((s) => s.wsConnected);
  const aiStatus = useAppStore((s) => s.aiStatus);
  const robotStatus = useAppStore((s) => s.robotStatus);

  return (
    <header className="topbar">
      <div className="topnav-tabs">
        {TABS.map(([key, label, icon]) => (
          <button
            key={key}
            className={`btn sm ${activeTab === key ? 'primary' : 'ghost'}`}
            onClick={() => setActiveTab(key)}
            title={label}
          >
            <QuantumIcon name={icon as any} size={16} glow={activeTab === key} />
            <span>{label}</span>
          </button>
        ))}
      </div>
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