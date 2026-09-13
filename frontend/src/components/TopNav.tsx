import React, { useEffect, useState } from 'react';
import { useAppStore, TabType } from '../hooks/useAppStore';

const TABS: [TabType, string][] = [
  ['dashboard', 'Painel'],
  ['market', 'Mercado'],
  ['positions', 'Carteira'],
  ['charts', 'Gráficos'],
  ['robot', 'Robô'],
  ['strategy-tester', 'Estratégias'],
];

export default function TopNav() {
  const activeTab = useAppStore((s) => s.activeTab);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const wsConnected = useAppStore((s) => s.wsConnected);
  const aiStatus = useAppStore((s) => s.aiStatus);
  const robotStatus = useAppStore((s) => s.robotStatus);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="topbar">
      <div className="topnav-tabs">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            className={`btn sm ${activeTab === key ? 'primary' : 'ghost'}`}
            onClick={() => setActiveTab(key)}
          >
            {label}
          </button>
        ))}
      </div>
      <div className="topnav-status">
        <span className="status">
          <i className={`dot ${wsConnected ? 'on' : ''}`} /> WS {wsConnected ? 'Online' : 'Offline'}
        </span>
        <span className="status">🤖 AI: {aiStatus}</span>
        <span className="status">EA: {robotStatus}</span>
        <span className="muted">{time.toLocaleTimeString('pt-BR')}</span>
      </div>
    </header>
  );
}