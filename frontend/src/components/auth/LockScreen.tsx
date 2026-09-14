import { useState } from 'react';
import { verificarPin } from '../../auth/auth';

interface Props {
  onUnlock: () => void;
}

const MAX_TENTATIVAS = 5;

// Tela de bloqueio por PIN: aparece ao iniciar (com PIN cadastrado) ou ao travar
export default function LockScreen({ onUnlock }: Props) {
  const [pin, setPin] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [tentativas, setTentativas] = useState(0);
  const [travado, setTravado] = useState(false);

  async function submeter(e: React.FormEvent) {
    e.preventDefault();
    if (travado) return;
    setErro(null);
    try {
      const ok = await verificarPin(pin);
      if (ok) {
        onUnlock();
      } else {
        const t = tentativas + 1;
        setTentativas(t);
        if (t >= MAX_TENTATIVAS) {
          setTravado(true);
          setErro('Muitas tentativas. Feche e reabra o aplicativo para tentar novamente.');
        } else {
          setErro(`PIN incorreto (${MAX_TENTATIVAS - t} tentativa(s) restante(s)).`);
          setPin('');
        }
      }
    } catch (err) {
      setErro(`Erro ao verificar PIN: ${String(err)}`);
    }
  }

  return (
    <div className="auth-screen">
      <form className="auth-card card" onSubmit={submeter}>
        <div className="auth-logo">
          XAU <span>AI PRO</span>
        </div>
        <p className="auth-sub">Digite seu PIN para acessar o terminal</p>
        <div className="field">
          <label htmlFor="pin">PIN</label>
          <input
            id="pin"
            type="password"
            inputMode="numeric"
            autoComplete="current-password"
            maxLength={8}
            autoFocus
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
          />
        </div>
        {erro && <span className="auth-erro">{erro}</span>}
        <div className="auth-actions">
          <span className="muted">{travado ? 'Acesso bloqueado' : 'Sessao protegida por PIN'}</span>
          <button className="btn primary" type="submit" disabled={travado || pin.length < 4}>
            Desbloquear
          </button>
        </div>
      </form>
    </div>
  );
}
