import { useState } from 'react';
import { isMobileRuntime, sessionToken } from '../../lib/api';
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

  if (!mobile || autenticado) return <>{children}</>;
  return <LoginScreen onAutenticado={() => setAutenticado(true)} />;
}
