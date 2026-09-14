/**
 * QuantumIcon — Renderizador de ícones quânticos SVG neon
 */

import React from 'react';
import { dashboard } from './icons/dashboard';
import { market } from './icons/market';
import { positions } from './icons/positions';
import { robot } from './icons/robot';
import { charts } from './icons/charts';
import { vision } from './icons/vision';
import { strategy } from './icons/strategy';
import { tools } from './icons/tools';
import { movements } from './icons/movements';
import { balances } from './icons/balances';
import { history } from './icons/history';
import { calendar } from './icons/calendar';
import { news } from './icons/news';
import { system } from './icons/system';
import { settings } from './icons/settings';
import { info } from './icons/info';
import { wallet } from './icons/wallet';
import { lock } from './icons/lock';
import { quantum } from './icons/quantum';

export type IconName =
  | 'dashboard' | 'market' | 'positions' | 'robot' | 'charts'
  | 'vision' | 'strategy' | 'tools' | 'integrations' | 'settings'
  | 'calendar' | 'news' | 'system' | 'info' | 'movements'
  | 'balances' | 'history' | 'quantum' | 'wallet' | 'lock';

interface Props {
  name: IconName;
  size?: 16 | 24 | 32 | 48;
  className?: string;
  glow?: boolean;
}

const iconMap: Record<IconName, (c: string, a: string) => React.ReactNode> = {
  dashboard, market, positions, robot, charts, vision, strategy, tools,
  movements, balances, history, calendar, news, system, settings, info,
  wallet, lock, quantum,
  integrations: tools, // fallback
};

export const QuantumIcon: React.FC<Props> = ({ name, size = 24, className, glow = true }) => {
  const color = 'var(--quantum-primary, #00d4ff)';
  const accent = 'var(--quantum-accent, #ff6b35)';
  const render = iconMap[name] || quantum;

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      className={className}
      style={{ filter: glow ? 'drop-shadow(0 0 4px var(--quantum-glow, #00d4ff))' : undefined }}
    >
      {render(color, accent)}
    </svg>
  );
};

export default QuantumIcon;
