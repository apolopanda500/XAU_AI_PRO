import { useEffect, useState } from 'react';
import { verificarPin } from '../../auth/auth';
import {
  estaBloqueado,
  formatarEspera,
  lerLockout,
  limparFalhas,
  registrarFalha,
  tentativasRestantes,
  type LockoutState,
} from '../../auth/lockout';

interface Props {
  onUnlock: () => void;
}

// Tela de bloqueio por PIN. O contador de tentativas e persistido, de modo que
// reabrir o app nao concede tentativas extras a quem esta forçando o PIN.
export default function LockScreen({ onUnlock }: Props) {
  const [pin, setPin] = useState('');
  const [erro, setErro] = useState<string | null>(null);
  const [estado, setEstado] = useState<LockoutState>(() => lerLockout());
  const [restante, setRestante] = useState(0);

  useEffect(() => {
    function sincronizar() {
      const agora = Date.now();
      const atual = lerLockout();
      setEstado(atual);
      setRestante(Math.max(0, Math.ceil((atual.bloqueadoAte - agora) / 1000)));
    }
    sincronizar();
    const timer = window.setInterval(sincronizar, 1000);
    return () => window.clearInterval(timer);
  }, []);

  const bloqueado = estaBloqueado(estado, Date.now());

  async function submeter(e: React.FormEvent) {
    e.preventDefault();
    if (bloqueado) return;
    setErro(null);
    try {
      const ok = await verificarPin(pin);
      if (ok) {
        limparFalhas();
        setPin('');
        onUnlock();
        return;
      }
      const proximo = registrarFalha(estado, Date.now());
      setEstado(proximo);
      const espera = proximo.bloqueadoAte - Date.now();
      if (espera > 0) {
        setRestante(Math.ceil(espera / 1000));
        setErro(`PIN incorreto. Acesso bloqueado por ${formatarEspera(espera)}.`);
      } else {
        setErro(`PIN incorreto (${tentativasRestantes(proximo)} tentativa(s) restante(s)).`);
      }
      setPin('');
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
            disabled={bloqueado}
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
          />
        </div>
        {erro && <span className="auth-erro">{erro}</span>}
        <div className="auth-actions">
          <span className="muted">
            {bloqueado ? `Acesso bloqueado por ${restante}s` : 'Sessao protegida por PIN'}
          </span>
          <button className="btn primary" type="submit" disabled={bloqueado || pin.length < 4}>
            Desbloquear
          </button>
        </div>
      </form>
    </div>
  );
}
