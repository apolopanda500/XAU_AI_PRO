import { useState } from 'react';
import { isLoginError, loginUser } from '../../lib/api';
import { isMobileRuntime } from '../../lib/api';
import {
  alertaSeguranca,
  gatewayConfigurado,
  limparGateway,
  salvarGateway,
  testarGateway,
  HOST_EMULADOR,
  type Resultado,
} from '../../lib/gatewayConfig';

interface Props {
  onAutenticado: () => void;
}

// Tela de login por usuário.
//
// Só é exigida no runtime mobile. No desktop o token chega pelo Tauri
// (installGatewayAuth) e não existe sessão de usuário para fazer.
//
// O painel de gateway existe porque o APK caía em 127.0.0.1 sem nenhum jeito de
// corrigir: a chave de configuração era lida, mas nenhuma tela a escrevia. No
// emulador, 10.0.2.2 alcança o PC do trader; em producao, https/wss.
export default function LoginScreen({ onAutenticado }: Props) {
  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [mostrarGateway, setMostrarGateway] = useState(false);
  const [atual, setAtual] = useState(gatewayConfigurado);
  const [apiBase, setApiBase] = useState(atual.apiBase);
  const [wsUrl, setWsUrl] = useState(atual.wsUrl);
  const [aviso, setAviso] = useState<string | null>(null);
  const [teste, setTeste] = useState<Resultado | null>(null);
  const mobile = isMobileRuntime();

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

  function gravar() {
    setTeste(null);
    const avisoTls = alertaSeguranca(apiBase, mobile);
    if (avisoTls) {
      setAviso(avisoTls);
      return;
    }
    const r = salvarGateway(apiBase, wsUrl);
    if (!r.ok) {
      setAviso(r.erro ?? 'configuracao invalida');
      return;
    }
    setAtual({ apiBase: r.apiBase, wsUrl: r.wsUrl });
    setApiBase(r.apiBase);
    setWsUrl(r.wsUrl);
    setAviso('Gateway salvo. O proximo login usa esta configuracao.');
  }

  async function testar() {
    setTeste(null);
    setTeste(await testarGateway(apiBase));
  }

  function usarHostLocal() {
    setApiBase(HOST_EMULADOR);
    setWsUrl(`${HOST_EMULADOR.replace(/^http/i, 'ws')}/ws/market`);
    setAviso('Preenchido com o host da maquina, visto do emulador.');
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

        <div className="field">
          <label htmlFor="login-gateway">
            Gateway: {atual.apiBase || 'nao configurado (vai tentar 127.0.0.1)'}
          </label>
          <button
            type="button"
            className="btn ghost sm"
            onClick={() => setMostrarGateway((v) => !v)}
            aria-expanded={mostrarGateway}
          >
            {mostrarGateway ? 'Ocultar' : 'Configurar'} gateway
          </button>
        </div>

        {mostrarGateway && (
          <div className="field">
            <input
              id="login-gateway"
              className="input"
              type="url"
              inputMode="url"
              placeholder="https://gateway.exemplo.com"
              value={apiBase}
              onChange={(e) => setApiBase(e.target.value)}
            />
            <input
              className="input"
              type="url"
              inputMode="url"
              placeholder="wss://gateway.exemplo.com/ws/market"
              value={wsUrl}
              onChange={(e) => setWsUrl(e.target.value)}
            />
            <div className="btn-row">
              <button type="button" className="btn sm primary" onClick={gravar}>Salvar</button>
              <button type="button" className="btn sm ghost" onClick={() => void testar()}>Testar</button>
              {mobile && (
                <button type="button" className="btn sm ghost" onClick={usarHostLocal}>
                  Usar host do PC
                </button>
              )}
              <button
                type="button"
                className="btn sm ghost"
                onClick={() => {
                  limparGateway();
                  const limpo = gatewayConfigurado();
                  setAtual(limpo);
                  setApiBase(limpo.apiBase);
                  setWsUrl(limpo.wsUrl);
                  setTeste(null);
                  setAviso('Configuracao de gateway removida.');
                }}
              >
                Limpar
              </button>
            </div>
            {mobile && (
              <p className="hint">
                No emulador, o PC do trader aparece como <code>10.0.2.2</code>. Em producao use
                <code> https://</code> e <code>wss://</code>.
              </p>
            )}
            {teste && (
              <p className={teste.ok ? 'hint' : 'auth-erro'}>
                {teste.ok
                  ? `${teste.detalhe} em ${teste.latencia_ms} ms`
                  : `${teste.erro} - ${teste.dica}`}
              </p>
            )}
          </div>
        )}

        {aviso && <p className="hint" role="status">{aviso}</p>}

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
