import { useEffect, type ReactNode } from 'react';
import { carregarAuth } from '../auth/auth';
import { useAuthStore } from '../auth/authStore';
import LockScreen from './auth/LockScreen';

// A existencia do PIN e determinada exclusivamente pelo auth.json no disco.
// O app nunca apaga o auth.json por conta propria: o PIN so e removido quando o
// usuario confirma o PIN atual em Configuracoes.
export default function AuthGate({ children }: { children: ReactNode }) {
  const phase = useAuthStore((s) => s.phase);
  const setPhase = useAuthStore((s) => s.setPhase);
  const setHasPin = useAuthStore((s) => s.setHasPin);

  useEffect(() => {
    let live = true;
    setPhase('loading');
    carregarAuth()
      .then((auth) => {
        if (!live) return;
        setHasPin(Boolean(auth));
        setPhase(auth ? 'locked' : 'ready');
      })
      .catch(() => {
        // Falha de leitura nunca abre o app silenciosamente com PIN ativo: em caso
        // de erro o usuario precisa reiniciar para reavaliar.
        if (!live) return;
        setHasPin(false);
        setPhase('ready');
      });
    return () => {
      live = false;
    };
  }, [setHasPin, setPhase]);

  if (phase === 'loading') {
    return (
      <div className="auth-screen">
        <div className="auth-card card">
          <strong>Carregando XAU AI PRO…</strong>
        </div>
      </div>
    );
  }
  if (phase === 'locked') {
    return <LockScreen onUnlock={() => setPhase('ready')} />;
  }
  return <>{children}</>;
}
