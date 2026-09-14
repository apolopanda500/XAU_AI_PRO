// Tela de abertura exibida enquanto o estado de autenticacao e verificado
export default function Splash() {
  return (
    <div className="auth-screen">
      <div className="auth-card card" style={{ textAlign: 'center' }}>
        <div className="auth-logo">
          XAU <span>AI PRO</span>
        </div>
        <p className="auth-sub">Verificando configuracoes...</p>
        <span className="spinner" aria-label="Carregando" />
      </div>
    </div>
  );
}
