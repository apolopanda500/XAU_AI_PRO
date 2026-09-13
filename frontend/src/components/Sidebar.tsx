import React from 'react';
import { useAppStore, TabType } from '../hooks/useAppStore';

const ITEMS: [TabType, string, string][] = [
  ['dashboard', 'Painel', '📊'],
  ['market', 'Mercado', '📈'],
  ['positions', 'Carteira', '💼'],
  ['charts', 'Gráficos', '📉'],
  ['robot', 'Robô MT5', '🤖'],
  ['strategy-tester', 'Teste de Estratégia', '🧪'],
  ['robot-vision', 'Robô Vision', '👁️'],
  ['tools', 'Ferramentas', '🛠️'],
  ['integrations', 'Integrações', '🔌'],
  ['settings', 'Configurações', '⚙️'],
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
            <span className="nav-icon">{icon}</span>
            {sidebarOpen && <span className="nav-label">{label}</span>}
          </button>
        ))}
      </nav>
      <div className="sidebar-footer muted">v0.1.0 • Rust Core + Tauri</div>
    </aside>
  );
}