import React from 'react';
import { useAppStore, type TabType } from '../hooks/useAppStore';
import { isMobileRuntime } from '../lib/api';

type Item = { id: TabType; label: string; icon: string };

/*
  MEDIDO 25/11/2026 no emulator-5554 (720px): o sidebar some em <=768px e a
  bottom-nav tinha so 5 itens, sem `settings`. Isso deixava
  Configurações -> Conexões & Corretoras (onde o dono vincula a conta MT5)
  ALCANZAVEL SOMENTE no desktop/celular largo. O comentario do CSS dizia que
  a barra inferior cobria todas as abas — mentira medida. `settings` entra
  aqui para o APK entrar direto no app e ainda permitir vincular a conta.
*/
export const MOBILE_NAV_ITEMS: Item[] = [
  { id: 'robot', label: 'Operar', icon: '📈' },
  { id: 'portfolio', label: 'Carteira', icon: '💼' },
  { id: 'history', label: 'Histórico', icon: '🕘' },
  { id: 'calendar', label: 'Calendário', icon: '📅' },
  { id: 'system', label: 'Sistema', icon: '⚙️' },
  { id: 'settings', label: 'Config', icon: '🔧' },
];

export const MobileBottomNav: React.FC = () => {
  const mobile = isMobileRuntime();
  const active = useAppStore((s) => (s.activeTab === 'dashboard' ? 'portfolio' : s.activeTab));
  const setActive = useAppStore((s) => s.setActiveTab);

  if (!mobile) return null;

  return (
    <nav
      aria-label="Navegação inferior móvel"
      style={{
        position: 'sticky',
        bottom: 0,
        zIndex: 20,
        display: 'grid',
        gridTemplateColumns: `repeat(${MOBILE_NAV_ITEMS.length}, 1fr)`,
        gap: 4,
        padding: '6px 6px calc(6px + env(safe-area-inset-bottom, 0px))',
        background: 'rgba(7, 11, 20, 0.96)',
        borderTop: '1px solid rgba(148, 163, 184, 0.2)',
        backdropFilter: 'blur(10px)',
      }}
      className="mobile-bottom-nav"
    >
      {MOBILE_NAV_ITEMS.map((item) => {
        const isActive = active === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => setActive(item.id)}
            aria-current={isActive ? 'page' : undefined}
            style={{
              border: 'none',
              borderRadius: 10,
              padding: '8px 4px',
              background: isActive ? 'rgba(245, 158, 11, 0.16)' : 'transparent',
              color: isActive ? '#fbbf24' : '#cbd5e1',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 2,
              fontSize: 11,
              fontWeight: 700,
              minHeight: 52,
            }}
          >
            <span aria-hidden="true" style={{ fontSize: 16, lineHeight: 1 }}>{item.icon}</span>
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
};

export default MobileBottomNav;
