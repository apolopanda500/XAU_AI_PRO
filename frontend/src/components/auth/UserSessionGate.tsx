import { useEffect, useState } from 'react';
import { isMobileRuntime, sessionToken } from '../../lib/api';
import MobileBiometricLock from '../MobileBiometricLock';
import LoginScreen from './LoginScreen';

interface Props {
  children: React.ReactNode;
}

// Portão de sessão de usuário.
//
// Só atua no runtime mobile. No desktop não há sessão de usuário: o token é
// injetado pelo Tauri (installGatewayAuth) e o app entra direto.
//
// Fora do mobile este componente retorna os filhos, então não interfere no
// AuthGate (PIN) nem em nada do desktop.
export default function UserSessionGate({ children }: Props) {
  const mobile = isMobileRuntime();
  // o token é lido uma vez na montagem: a tela de login é a que troca a sessão
  const [autenticado, setAutenticado] = useState(() => !mobile || Boolean(sessionToken()));
  const [bloqueado, setBloqueado] = useState(false);

  useEffect(() => {
    if (!mobile || !autenticado) {
      setBloqueado(false);
      return;
    }
    const lockEnabled = typeof window !== 'undefined' && window.localStorage.getItem('xau_mobile_lock') === '1';
    const unlocked = typeof window !== 'undefined' && window.sessionStorage.getItem('xau_mobile_unlocked') === '1';
    setBloqueado(lockEnabled && !unlocked);
  }, [mobile, autenticado]);

  if (!mobile) return <>{children}</>;
  if (!autenticado) return <LoginScreen onAutenticado={() => setAutenticado(true)} />;
  if (bloqueado) {
    return (
      <MobileBiometricLock
        onUnlocked={() => {
          try {
            window.sessionStorage.setItem('xau_mobile_unlocked', '1');
          } catch {
            // ignore
          }
          setBloqueado(false);
        }}
      />
    );
  }
  return <>{children}</>;
}
