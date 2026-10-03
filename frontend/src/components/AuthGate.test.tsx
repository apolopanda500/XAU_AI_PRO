// @vitest-environment jsdom
// Testes do portao de PIN (AuthGate).
//
// O bug corrigido aqui: o AuthGate usava settings.pinEnabled (estado do front)
// como autoridade e, quando ela valia false, chamava removerPin(). Um reset de
// configuracao ou de cache apagava o auth.json e liberava o app sem PIN. A
// fonte da verdade passou a ser o auth.json no disco, e o portao nunca remove a
// credencial sozinho.
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';

const invoke = vi.fn();
vi.mock('@tauri-apps/api/core', () => ({ invoke: (...args: unknown[]) => invoke(...args) }));

const { default: AuthGate } = await import('./AuthGate');
const { useAppStore } = await import('../hooks/useAppStore');
const { useAuthStore } = await import('../auth/authStore');

const authFile = {
  salt_b64: 'c2FsdA==',
  hash_b64: 'aGFzaA==',
  iterations: 150000,
  created_at: '2026-09-25T00:00:00.000Z',
};

function stubAuth(presente: boolean) {
  invoke.mockImplementation(async (cmd: string) => {
    if (cmd === 'load_auth') return presente ? authFile : null;
    if (cmd === 'remove_auth') return null;
    return null;
  });
}

beforeEach(() => {
  invoke.mockReset();
  localStorage.clear();
  useAppStore.setState({ settings: { ...useAppStore.getState().settings, pinEnabled: false } });
  useAuthStore.setState({ phase: 'loading', hasPin: false });
});

afterEach(() => {
  cleanup();
});

describe('AuthGate', () => {
  it('exige o PIN quando existe auth.json', async () => {
    stubAuth(true);
    render(
      <AuthGate>
        <div>conteudo protegido</div>
      </AuthGate>,
    );
    await waitFor(() => expect(screen.getByText('Desbloquear')).toBeTruthy());
    expect(screen.queryByText('conteudo protegido')).toBeNull();
  });

  it('libera o app quando nao existe PIN cadastrado', async () => {
    stubAuth(false);
    render(
      <AuthGate>
        <div>conteudo protegido</div>
      </AuthGate>,
    );
    await waitFor(() => expect(screen.getByText('conteudo protegido')).toBeTruthy());
  });

  it('NUNCA apaga o auth.json ao abrir o app', async () => {
    stubAuth(true);
    render(
      <AuthGate>
        <div>conteudo protegido</div>
      </AuthGate>,
    );
    await waitFor(() => expect(screen.getByText('Desbloquear')).toBeTruthy());
    const comandos = invoke.mock.calls.map((c) => c[0]);
    expect(comandos).not.toContain('remove_auth');
  });

  it('mantem o bloqueio mesmo com pinEnabled desligado no front', async () => {
    // Regressao do bug: config/cache do front dessincronizado nao pode abrir o app.
    useAppStore.setState({ settings: { ...useAppStore.getState().settings, pinEnabled: false } });
    stubAuth(true);
    render(
      <AuthGate>
        <div>conteudo protegido</div>
      </AuthGate>,
    );
    await waitFor(() => expect(screen.getByText('Desbloquear')).toBeTruthy());
    expect(screen.queryByText('conteudo protegido')).toBeNull();
  });

  it('espelha hasPin no store de autenticacao', async () => {
    stubAuth(true);
    render(
      <AuthGate>
        <div>conteudo protegido</div>
      </AuthGate>,
    );
    await waitFor(() => expect(useAuthStore.getState().hasPin).toBe(true));
    expect(useAuthStore.getState().phase).toBe('locked');
  });
});
