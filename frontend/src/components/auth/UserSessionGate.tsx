import { isMobileRuntime } from '../../lib/api';

interface Props {
  children: React.ReactNode;
}

// Portão de sessão de usuário.
//
// APK XAU AI PRO (mobile): entra direto no app, sem tela de login/senha.
// A sincronização de conta MT5 fica nas configurações/tela de conexão do app.
// O token de gateway pode ser embutido no build (VITE_GATEWAY_TOKEN) ou
// configurado pelo usuário na tela de conexão/gateway.
//
// Desktop: sem sessão de usuário; token injetado pelo Tauri (installGatewayAuth).
export default function UserSessionGate({ children }: Props) {
  // Direto ao app em mobile e desktop. Sem travas de login no APK.
  isMobileRuntime();
  return <>{children}</>;
}
