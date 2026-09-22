// Tela de abertura exibida enquanto o estado de autenticacao e verificado
export default function Splash() {
  return (
    <div className="auth-screen">
      <div className="auth-card card" style={{ textAlign: 'center' }}>
        <img className="splash-brand-image" src="/xau-ai-pro-mark.png" alt="XAU AI PRO" />
        <div className="auth-logo">
          XAU <span>AI PRO</span>
        </div>
        <p className="auth-sub">Verificando configuracoes...</p>
        <span className="spinner" aria-label="Carregando" />
      </div>
    </div>
  );
}
