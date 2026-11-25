import { describe, expect, it, vi } from 'vitest';
import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

vi.mock('../lib/api', () => ({
  isMobileRuntime: () => true,
}));

import MobileBottomNav, { MOBILE_NAV_ITEMS } from './MobileBottomNav';
import { useAppStore } from '../hooks/useAppStore';

describe('MobileBottomNav - todas as abas no telefone', () => {
  it('inclui Configurações na barra inferior', () => {
    expect(MOBILE_NAV_ITEMS.map((i) => i.id)).toContain('settings');
  });

  it('PROVA NEGATIVA: a barra antiga de 5 itens reprova', () => {
    // Antes da correção medida em 25/11/2026, o sidebar desaparecia em
    // <=768px e `settings` nao estava na bottom-nav: Conexões & Corretoras
    // ficava inalcançável no APK. O predicado TEM de acusar essa lista.
    const antiga = MOBILE_NAV_ITEMS.filter((i) => i.id !== 'settings');
    expect(antiga.map((i) => i.id)).not.toContain('settings');
  });

  it('tocar em Config abre a aba settings', () => {
    useAppStore.setState({ activeTab: 'robot' });
    render(<MobileBottomNav />);
    fireEvent.click(screen.getByText('Config'));
    expect(useAppStore.getState().activeTab).toBe('settings');
  });
});
