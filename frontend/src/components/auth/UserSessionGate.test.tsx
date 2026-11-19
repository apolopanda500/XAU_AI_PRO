import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import React from 'react';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';

// Estado do aparelho controlado pelo teste: token e prazo salvo.
let sessao = { token: '', expirou: false };
vi.mock('../../lib/api', () => ({
  isMobileRuntime: () => true,
  sessionToken: () => sessao.token,
  sessionExpirou: () => sessao.token !== '' && sessao.expirou,
  clearSessionToken: () => {
    sessao = { token: '', expirou: false };
  },
}));
vi.mock('../FirstRunWizard', () => ({
  default: ({ onComplete }: { onComplete: () => void }) => (
    <div data-testid="wizard">
      <button type="button" onClick={onComplete}>concluir-onboarding</button>
    </div>
  ),
}));
vi.mock('./LoginScreen', () => ({
  default: () => <div data-testid="login">Login</div>,
}));
vi.mock('../MobileBiometricLock', () => ({
  default: () => <div data-testid="lock">Lock</div>,
}));

import UserSessionGate from './UserSessionGate';

describe('UserSessionGate — primeiro acesso', () => {
  beforeEach(() => {
    sessao = { token: '', expirou: false };
    window.localStorage.clear();
  });
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('mostra o assistente quando a instalação é nova', () => {
    render(
      <UserSessionGate>
        <div data-testid="app">app</div>
      </UserSessionGate>,
    );
    expect(screen.getByTestId('wizard')).toBeTruthy();
    expect(screen.queryByTestId('login')).toBeNull();
    expect(screen.queryByTestId('app')).toBeNull();
  });

  it('pula o assistente quando xau_onboarding_done já foi gravado', () => {
    window.localStorage.setItem('xau_onboarding_done', '1');
    render(
      <UserSessionGate>
        <div data-testid="app">app</div>
      </UserSessionGate>,
    );
    expect(screen.queryByTestId('wizard')).toBeNull();
    expect(screen.getByTestId('login')).toBeTruthy();
  });

  it('após concluir o onboarding, chega na tela de login', () => {
    render(
      <UserSessionGate>
        <div data-testid="app">app</div>
      </UserSessionGate>,
    );
    fireEvent.click(screen.getByText('concluir-onboarding'));
    expect(screen.queryByTestId('wizard')).toBeNull();
    expect(screen.getByTestId('login')).toBeTruthy();
  });

  it('sessão vencida (lembrar expirado) volta para o fluxo de login', () => {
    sessao = { token: 'abc', expirou: true };
    window.localStorage.setItem('xau_onboarding_done', '1');
    render(
      <UserSessionGate>
        <div data-testid="app">app</div>
      </UserSessionGate>,
    );
    expect(screen.queryByTestId('app')).toBeNull();
    expect(screen.getByTestId('login')).toBeTruthy();
  });

  it('sessão válida entra direto no app', () => {
    sessao = { token: 'abc', expirou: false };
    window.localStorage.setItem('xau_onboarding_done', '1');
    render(
      <UserSessionGate>
        <div data-testid="app">app</div>
      </UserSessionGate>,
    );
    expect(screen.getByTestId('app')).toBeTruthy();
  });
});
