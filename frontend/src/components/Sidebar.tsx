import React from 'react';
import { useAppStore, TabType } from '../hooks/useAppStore';
import { QuantumIcon } from './QuantumIcon';
import type { IconName } from './QuantumIcon';

const ITEMS: [TabType, string, IconName][] = [
  ['dashboard', 'Painel', 'dashboard'],
  ['market', 'Mercado', 'market'],
  ['robot', 'Robô', 'robot'],
  ['history', 'Histórico', 'history'],
  ['calendar', 'Calendário', 'calendar'],
  ['system', 'Sistema', 'system'],
  ['strategy-tester', 'Estratégia', 'strategy'],
  ['settings', 'Config', 'settings'],
];

export default function Sidebar() {
  const activeTab = useAppStore((s) => s.activeTab);
  const setActiveTab = useAppStore((s) => s.setActiveTab);
  const sidebarOpen = useAppStore((s) => s.sidebarOpen);
  const setSidebarOpen = useAppStore((s) => s.setSidebarOpen);

  return (
    <aside className={`sidebar ${sidebarOpen ? '' : 'collapsed'}`}>
      <div className="brand">
        <span className="brand-mark">◆</span>
        <span className="brand-name">XAU AI PRO</span>
        <button className="btn ghost sm collapse-btn" title={sidebarOpen ? 'Recolher' : 'Expandir'} onClick={() => setSidebarOpen(!sidebarOpen)}>{sidebarOpen ? '‹' : '›'}</button>
      </div>
      <nav className="nav-list">
        {ITEMS.map(([key, label, icon]) => (
          <button key={key} className={`nav-item ${activeTab === key ? 'active' : ''}`} onClick={() => setActiveTab(key)} title={label}>
            <QuantumIcon name={icon} size={24} glow={activeTab === key} />
            {sidebarOpen && <span className="nav-label">{label}</span>}
          </button>
        ))}
      </nav>
      {sidebarOpen && <div className="sidebar-footer muted">XAU AI PRO · Operação manual segura</div>}
    </aside>
  );
}
