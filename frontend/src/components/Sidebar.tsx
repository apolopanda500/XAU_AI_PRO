import { useAppStore, type TabType } from '../hooks/useAppStore';
import { QuantumIcon, type IconName } from './QuantumIcon';

const ITEMS: Array<[TabType, string, IconName]> = [
  ['portfolio', 'Patrimônio', 'wallet'],
  ['market', 'Mercado', 'market'],
  ['robot', 'Robô', 'robot'],
  ['strategy-tester', 'Testador de estratégia', 'strategy'],
  ['history', 'Histórico', 'history'],
  ['calendar', 'Calendário', 'calendar'],
  ['system', 'Sistema', 'system'],
  ['settings', 'Configuração', 'settings'],
  ['risk', 'Risco', 'warning'],
  ['alert', 'Alertas', 'bell'],
  ['analytics', 'Analytics', 'chart'],
  ['ai', 'Inteligência Artificial', 'quantum'],
];

export default function Sidebar() {
  const active = useAppStore((state) => state.activeTab === 'dashboard' ? 'portfolio' : state.activeTab);
  const setActive = useAppStore((state) => state.setActiveTab);
  const open = useAppStore((state) => state.sidebarOpen);
  const setOpen = useAppStore((state) => state.setSidebarOpen);
  return <aside className={`sidebar ${open ? '' : 'collapsed'}`} aria-label="Navegação principal"><div className="brand"><img className="brand-mark brand-image" src="/xau-ai-pro-mark.png" alt="XAU AI PRO"/>{open && <span className="brand-name">XAU AI PRO</span>}<button type="button" className="btn ghost sm collapse-btn" title={open ? 'Recolher' : 'Expandir'} aria-label={open ? 'Recolher menu' : 'Expandir menu'} onClick={() => setOpen(!open)}>{open ? '‹' : '›'}</button></div><nav className="nav-list">{ITEMS.map(([key, label, icon]) => <button key={key} type="button" className={`nav-item ${active === key ? 'active' : ''}`} aria-label={label} aria-current={active === key ? 'page' : undefined} onClick={() => setActive(key)} title={label}><QuantumIcon name={icon} size={24} glow={active === key}/>{open && <span className="nav-label">{label}</span>}</button>)}</nav>{open && <div className="sidebar-footer muted"><span>XAU AI PRO · Operação segura</span><small>Versão 1.2.0</small></div>}</aside>;
}
