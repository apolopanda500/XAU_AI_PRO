import { useState } from 'react';
import { isLoginError, loginUser } from '../../lib/api';

interface Props {
  onAutenticado: () => void;
}

// Tela de login por usuário.
//
// Só é exigida no runtime mobile. No desktop o token chega pelo Tauri
// (installGatewayAuth) e não existe sessão de usuário para fazer.
//
// Exibe a URL do gateway em texto: se o app cair em 401 logo após o login, a
// causa mais provável é o host errado, e o usuário precisa enxergar qual está
// configurado para Diagnóstico.
export default function LoginScreen({ onAutenticado }: Props) {
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  async function submeter(e: React.FormEvent) {
    e.preventDefault();
    if (enviando) return;
    setErro(null);
    setEnviando(true);
    const r = await loginUser(email.trim(), senha);
    setEnviando(false);
    if (isLoginError(r)) {
      setErro(r.error);
      return;
    }
    setSenha('');
    onAutenticado();
  }

  return (
    <div className="auth-screen">
      <form className="auth-card card" onSubmit={submeter}>
        <div className="auth-logo">
          XAU <span>AI PRO</span>
        </div>
        <p className="auth-sub">Entre com sua conta para acessar o terminal</p>
        <div className="field">
          <label htmlFor="login-email">E-mail</label>
          <input
            id="login-email"
            type="email"
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="login-senha">Senha</label>
          <input
            id="login-senha"
            type="password"
            autoComplete="current-password"
            required
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
          />
        </div>
        {erro && <span className="auth-erro">{erro}</span>}
        <div className="auth-actions">
          <span className="muted">Sessao com validade limitada</span>
          <button className="btn primary" type="submit" disabled={enviando || !email || !senha}>
            {enviando ? 'Entrando...' : 'Entrar'}
          </button>
        </div>
      </form>
    </div>
  );
}
