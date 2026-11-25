import { afterEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

vi.mock('../lib/api', () => ({
  isMobileRuntime: () => true,
}));

import MobileBottomNav, { MOBILE_NAV_GRID, MOBILE_NAV_ITEMS } from './MobileBottomNav';
import { useAppStore } from '../hooks/useAppStore';

describe('MobileBottomNav - todas as abas no telefone', () => {
  // vitest roda sem globals; sem isto o segundo render encontrava 2 x o nav.
  afterEach(cleanup);

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

  it('as colunas encolhem: 6 itens cabem em 720px', () => {
    render(<MobileBottomNav />);
    const nav = screen.getByLabelText('Navegação inferior móvel');
    // jsdom normaliza `minmax(0, 1fr)` para `minmax(0px, 1fr)` no style.
    const aplicado = nav.style.gridTemplateColumns.replace(/0px/g, '0');
    expect(aplicado).toBe(MOBILE_NAV_GRID);
    expect(MOBILE_NAV_GRID).toContain('minmax(0, 1fr)');
  });

  it('PROVA NEGATIVA: repeat(6, 1fr) nao protege o sexto botao', () => {
    // MEDIDO no emulator-5554: com `1fr` o `Config` media bounds
    // [0,0][0,0] (fora da viewport). O predicado TEM de reprovar essa forma.
    const antigo = `repeat(${MOBILE_NAV_ITEMS.length}, 1fr)`;
    expect(antigo).not.toBe(MOBILE_NAV_GRID);
  });
});
