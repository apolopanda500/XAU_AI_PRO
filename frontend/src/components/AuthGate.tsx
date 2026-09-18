import { useEffect, useState, type ReactNode } from 'react';
import { carregarAuth, removerPin } from '../auth/auth';
import { useAppStore } from '../hooks/useAppStore';
import LockScreen from './auth/LockScreen';
export default function AuthGate({ children }: { children: ReactNode }) {
  const enabled = useAppStore((s) => s.settings.pinEnabled);
  const [state, setState] = useState<'loading' | 'open' | 'locked'>('loading');
  useEffect(() => { let live = true; if (!enabled) { void removerPin().catch(() => undefined); setState('open'); return () => { live = false; }; } carregarAuth().then((auth) => { if (live) setState(auth ? 'locked' : 'open'); }).catch(() => { if (live) setState('open'); }); return () => { live = false; }; }, [enabled]);
  if (state === 'loading') return <div className="auth-screen"><div className="auth-card card"><strong>Carregando XAU AI PRO…</strong></div></div>;
  if (state === 'locked') return <LockScreen onUnlock={() => setState('open')} />;
  return <>{children}</>;
}
