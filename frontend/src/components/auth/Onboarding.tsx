import { useState } from 'react';
import { useAppStore } from '../../hooks/useAppStore';
import { THEMES } from '../../hooks/useTheme';
import type { ThemeName } from '../../hooks/useAppStore';
import { definirPin, validarPin } from '../../auth/auth';

interface Props {
  comPin: boolean;
  onConcluir: () => void;
}

const PASSOS = ['Boas-vindas', 'Aparencia', 'Seguranca', 'Resumo'];

// Wizard de primeiro uso: boas-vindas, tema, PIN opcional e resumo
export default function Onboarding({ comPin, onConcluir }: Props) {
  const [passo, setPasso] = useState(0);
  const settings = useAppStore((s) => s.settings);
  const setSettings = useAppStore((s) => s.setSettings);
  const completeOnboarding = useAppStore((s) => s.completeOnboarding);

  const [pin, setPin] = useState('');
  const [pinConf, setPinConf] = useState('');
  const [pularPin, setPularPin] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  function avancar() {
    setErro(null);
    // Passo 2 (PIN): so avanca se coerente
    if (passo === 2 && comPin && !pularPin && (pin || pinConf)) {
      const invalidez = validarPin(pin);
      if (invalidez) {
        setErro(invalidez);
        return;
      }
      if (pin !== pinConf) {
        setErro('Os PINs nao coincidem.');
        return;
      }
    }
    setPasso((p) => Math.min(p + 1, PASSOS.length - 1));
  }

  function voltar() {
    setErro(null);
    setPasso((p) => Math.max(p - 1, 0));
  }

  async function concluir() {
    setErro(null);
    let pinFinal: string | null = null;
    if (comPin && !pularPin) {
      if (pin !== pinConf) {
        setErro('Os PINs nao coincidem.');
        return;
      }
      const invalidez = validarPin(pin);
      if (invalidez) {
        setErro(invalidez);
        return;
      }
      pinFinal = pin;
    }
    setSalvando(true);
    try {
      if (pinFinal) await definirPin(pinFinal);
      completeOnboarding();
      onConcluir();
    } catch (err) {
      setErro(`Falha ao salvar: ${String(err)}`);
      setSalvando(false);
    }
  }

  return (
    <div className="auth-screen">
      <div className="auth-card card">
        <div className="auth-logo">
          XAU <span>AI PRO</span>
        </div>
        <p className="auth-sub">
          Configuracao inicial — passo {passo + 1} de {PASSOS.length}
        </p>
        <div className="stepper" aria-label={`Passo ${passo + 1} de ${PASSOS.length}`}>
          {PASSOS.map((_, i) => (
            <i key={i} className={i <= passo ? 'on' : ''} />
          ))}
        </div>

        {passo === 0 && (
          <div>
            <h2 style={{ marginBottom: 8 }}>Bem-vindo ao XAU AI PRO</h2>
            <p className="muted">
              Terminal de trading com Core Rust de alta performance, dados de mercado em tempo real
              e integracao MT5. Este assistente prepara aparencia, seguranca e preferencias basicas.
            </p>
          </div>
        )}

        {passo === 1 && (
          <div>
            <div className="field">
              <label htmlFor="ob-tema">Tema da interface</label>
              <select
                id="ob-tema"
                value={settings.theme}
                onChange={(e) => setSettings({ theme: e.target.value as ThemeName })}
              >
                {THEMES.map((t) => (
                  <option key={t.id} value={t.id}>{t.label}</option>
                ))}
              </select>
              <span className="hint">Voce pode alterar depois em Configuracoes.</span>
            </div>
            <div className="switch-row">
              <div>
                <div className="switch-label">Notificacoes</div>
                <div className="switch-desc">Alertas do sistema operacional</div>
              </div>
              <button
                className={`switch ${settings.notifications ? 'on' : ''}`}
                aria-label="Alternar notificacoes"
                onClick={() => setSettings({ notifications: !settings.notifications })}
              />
            </div>
          </div>
        )}

        {passo === 2 && (
          <div>
            <div className="field">
              <label htmlFor="ob-pin">PIN de acesso (4 a 8 digitos)</label>
              <input
                id="ob-pin"
                type="password"
                inputMode="numeric"
                autoComplete="new-password"
                maxLength={8}
                placeholder="Deixe vazio para nao usar PIN"
                value={pin}
                onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
              />
              <span className="hint">
                O PIN protege o terminal nesta maquina. Hash PBKDF2-SHA256 com salt — o PIN nunca e
                gravado em disco.
              </span>
            </div>
            <div className="field">
              <label htmlFor="ob-pin-conf">Confirmar PIN</label>
              <input
                id="ob-pin-conf"
                type="password"
                inputMode="numeric"
                autoComplete="new-password"
                maxLength={8}
                value={pinConf}
                onChange={(e) => setPinConf(e.target.value.replace(/\D/g, ''))}
              />
            </div>
            <div className="switch-row">
              <div>
                <div className="switch-label">Nao quero PIN</div>
                <div className="switch-desc">Pular protecao por PIN (menos seguro)</div>
              </div>
              <button
                className={`switch ${pularPin ? 'on' : ''}`}
                aria-label="Alternar uso de PIN"
                onClick={() => setPularPin((v) => !v)}
              />
            </div>
          </div>
        )}

        {passo === 3 && (
          <div>
            <h2 style={{ marginBottom: 8 }}>Tudo pronto</h2>
            <p className="muted">
              Resumo da configuracao inicial. Voce pode ajustar tudo depois em Configuracoes.
            </p>
            <ul className="ob-resumo">
              <li>
                Tema: <strong>{THEMES.find((t) => t.id === settings.theme)?.label ?? settings.theme}</strong>
              </li>
              <li>
                Notificacoes: <strong>{settings.notifications ? 'ativadas' : 'desativadas'}</strong>
              </li>
              <li>
                PIN: <strong>{comPin && !pularPin && pin ? 'cadastrado' : 'nao configurado'}</strong>
              </li>
              <li>
                Configuracoes em: <code>%APPDATA%\XAU_AI_PRO</code>
              </li>
            </ul>
          </div>
        )}

        {erro && (
          <span className="auth-erro" role="alert">
            {erro}
          </span>
        )}

        <div className="auth-actions">
          <button className="btn ghost" onClick={voltar} disabled={passo === 0 || salvando}>
            Voltar
          </button>
          {passo < PASSOS.length - 1 ? (
            <button className="btn primary" onClick={avancar}>
              Continuar
            </button>
          ) : (
            <button className="btn primary" onClick={concluir} disabled={salvando}>
              {salvando ? 'Salvando...' : 'Concluir'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
