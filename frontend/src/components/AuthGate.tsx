import { useEffect } from 'react';
import { useAuthStore } from '../auth/authStore';
import { useAppStore } from '../hooks/useAppStore';
import { isTauri } from '../lib/tauri';
import { carregarAuth } from '../auth/auth';
import Splash from './auth/Splash';
import LockScreen from './auth/LockScreen';
import Onboarding from './auth/Onboarding';
import type { ReactNode } from 'react';

// Gate de autenticacao: decide entre Splash / Onboarding / LockScreen / App
export default function AuthGate({ children }: { children: ReactNode }) {
  // Verificacao inicial: existe auth.json (PIN)? O onboarding ja foi concluido?
  useEffect(() => {
    let vivo = true;
    (async () => {
      let existePin = false;
      try {
        if (isTauri()) {
          const auth = await carregarAuth();
          existePin = Boolean(auth);
        }
      } catch {
        existePin = false;
      }
      if (!vivo) return;
      const onboardingDone = useAppStore.getState().onboardingDone;
      useAuthStore.getState().setHasPin(existePin);
      useAuthStore
        .getState()
        .setPhase(existePin ? 'locked' : onboardingDone ? 'ready' : 'onboarding');
    })();
    return () => {
      vivo = false;
    };
  }, []);

  return <AuthRouter>{children}</AuthRouter>;
}

function AuthRouter({ children }: { children: ReactNode }) {
  const phase = useAuthStore((s) => s.phase);
  const setPhase = useAuthStore((s) => s.setPhase);
  const hasPin = useAuthStore((s) => s.hasPin);

  if (phase === 'loading') return <Splash />;
  if (phase === 'onboarding') {
    return <Onboarding comPin={!hasPin} onConcluir={() => setPhase('ready')} />;
  }
  if (phase === 'locked') return <LockScreen onUnlock={() => setPhase('ready')} />;
  return <>{children}</>;
}
