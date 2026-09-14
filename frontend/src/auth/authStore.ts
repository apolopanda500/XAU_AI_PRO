import { create } from 'zustand';

export type AuthPhase = 'loading' | 'onboarding' | 'locked' | 'ready';

interface AuthState {
  phase: AuthPhase;
  hasPin: boolean;
  setPhase: (phase: AuthPhase) => void;
  setHasPin: (has: boolean) => void;
}

// Estado de sessao (nao persistido): controla onboarding, bloqueio e splash
export const useAuthStore = create<AuthState>((set) => ({
  phase: 'loading',
  hasPin: false,
  setPhase: (phase) => set({ phase }),
  setHasPin: (hasPin) => set({ hasPin }),
}));
