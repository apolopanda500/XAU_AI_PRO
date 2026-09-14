import { useState } from 'react';
import { useAppStore } from '../../hooks/useAppStore';
import { THEMES } from '../../hooks/useTheme';
import type { ThemeName } from '../../hooks/useAppStore';
import { useAuthStore } from '../../auth/authStore';
import { definirPin, removerPin, validarPin, verificarPin } from '../../auth/auth';

export default function SettingsTab() {
  const settings = useAppStore((s) => s.settings);
  const setSettings = useAppStore((s) => s.setSettings);
  const resetSettings = useAppStore((s) => s.resetSettings);

  // Estado da secao Seguranca
  const hasPin = useAuthStore((s) => s.hasPin);
  const setHasPin = useAuthStore((s) => s.setHasPin);
  const setPhase = useAuthStore((s) => s.setPhase);
  const [pinAtual, setPinAtual] = useState('');
  const [novoPin, setNovoPin] = useState('');
  const [confirmaPin, setConfirmaPin] = useState('');
  const [msgSeg, setMsgSeg] = useState<{ tipo: 'ok' | 'erro'; texto: string } | null>(null);

  async function cadastrarPin(): Promise<void> {
    const erro = validarPin(novoPin);
    if (erro) return setMsgSeg({ tipo: 'erro', texto: erro });
    if (novoPin !== confirmaPin) return setMsgSeg({ tipo: 'erro', texto: 'Os PINs nao coincidem.' });
    try {
      await definirPin(novoPin);
      setHasPin(true);
      limparCamposPin();
      setMsgSeg({ tipo: 'ok', texto: 'PIN cadastrado com sucesso.' });
    } catch {
      setMsgSeg({ tipo: 'erro', texto: 'Falha ao gravar o auth.json.' });
    }
  }

  async function alterarPin(): Promise<void> {
    if (!(await verificarPin(pinAtual))) {
      return setMsgSeg({ tipo: 'erro', texto: 'PIN atual incorreto.' });
    }
    const erro = validarPin(novoPin);
    if (erro) return setMsgSeg({ tipo: 'erro', texto: erro });
    if (novoPin !== confirmaPin) return setMsgSeg({ tipo: 'erro', texto: 'Os PINs nao coincidem.' });
    try {
      await definirPin(novoPin);
      limparCamposPin();
      setMsgSeg({ tipo: 'ok', texto: 'PIN alterado com sucesso.' });
    } catch {
      setMsgSeg({ tipo: 'erro', texto: 'Falha ao gravar o auth.json.' });
    }
  }

  async function excluirPin(): Promise<void> {
    if (!(await verificarPin(pinAtual))) {
      return setMsgSeg({ tipo: 'erro', texto: 'PIN atual incorreto.' });
    }
    try {
      await removerPin();
      setHasPin(false);
      limparCamposPin();
      setMsgSeg({ tipo: 'ok', texto: 'PIN removido. O app abrira sem bloqueio.' });
    } catch {
      setMsgSeg({ tipo: 'erro', texto: 'Falha ao remover o auth.json.' });
    }
  }

  function limparCamposPin(): void {
    setPinAtual('');
    setNovoPin('');
    setConfirmaPin('');
  }

  return (
    <div>
      <div className="page-head">
        <h1>Configurações</h1>
        <span className="muted">Aparencia, IA e comportamento geral do aplicativo</span>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h2>Aparência</h2>
          <div className="field">
            <label htmlFor="theme">Tema</label>
            <select
              id="theme"
              value={settings.theme}
              onChange={(e) => setSettings({ theme: e.target.value as ThemeName })}
            >
              {THEMES.map((t) => (
                <option key={t.id} value={t.id}>{t.label}</option>
              ))}
            </select>
            <span className="hint">Aplicado imediatamente via data-theme no documento.</span>
          </div>
          <div className="field">
            <label htmlFor="precision">Casas decimais</label>
            <input
              id="precision"
              type="number"
              min={0}
              max={8}
              value={settings.precision}
              onChange={(e) => setSettings({ precision: Number(e.target.value) || 2 })}
            />
          </div>
          <div className="switch-row">
            <div>
              <div className="switch-label">Animações</div>
              <div className="switch-desc">Transicoes suaves na interface</div>
            </div>
            <button className={`switch ${settings.animations ? 'on' : ''}`} aria-label="Alternar animacoes" onClick={() => setSettings({ animations: !settings.animations })} />
          </div>
          <div className="switch-row">
            <div>
              <div className="switch-label">Sons</div>
              <div className="switch-desc">Alertas sonoros de trade</div>
            </div>
            <button className={`switch ${settings.soundEnabled ? 'on' : ''}`} aria-label="Alternar sons" onClick={() => setSettings({ soundEnabled: !settings.soundEnabled })} />
          </div>
          <div className="switch-row">
            <div>
              <div className="switch-label">Notificações</div>
              <div className="switch-desc">Notificacoes do sistema operacional</div>
            </div>
            <button className={`switch ${settings.notifications ? 'on' : ''}`} aria-label="Alternar notificacoes" onClick={() => setSettings({ notifications: !settings.notifications })} />
          </div>
        </div>

        <div>
          <div className="card" style={{ marginBottom: 14 }}>
            <h2>IA / Análise</h2>
            <div className="switch-row">
              <div>
                <div className="switch-label">IA ativa</div>
                <div className="switch-desc">Sinais gerados pelo motor de IA do Core</div>
              </div>
              <button className={`switch ${settings.aiEnabled ? 'on' : ''}`} aria-label="Alternar ia" onClick={() => setSettings({ aiEnabled: !settings.aiEnabled })} />
            </div>
            <div className="field">
              <label htmlFor="aimodel">Modelo</label>
              <select id="aimodel" value={settings.aiModel} onChange={(e) => setSettings({ aiModel: e.target.value })}>
                <option value="xau-pro-v2">xau-pro-v2</option>
                <option value="xau-pro-v1">xau-pro-v1</option>
                <option value="experimental">experimental</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="aiinterval">Intervalo de analise (s)</label>
              <input
                id="aiinterval"
                type="number"
                min={10}
                max={3600}
                value={settings.aiInterval}
                onChange={(e) => setSettings({ aiInterval: Number(e.target.value) || 60 })}
              />
            </div>
          </div>

          <div className="card" style={{ marginBottom: 14 }}>
            <h2>Segurança</h2>
            {!hasPin ? (
              <>
                <span className="hint" style={{ display: 'block', marginBottom: 10 }}>
                  Nenhum PIN cadastrado. Defina um PIN para bloquear o app com PBKDF2 (150 mil iteracoes, salt aleatorio).
                </span>
                <div className="field">
                  <label htmlFor="novoPin">Novo PIN (4 a 8 digitos)</label>
                  <input id="novoPin" type="password" inputMode="numeric" maxLength={8} value={novoPin} onChange={(e) => setNovoPin(e.target.value.replace(/\D/g, ''))} />
                </div>
                <div className="field">
                  <label htmlFor="confirmaPin">Confirmar PIN</label>
                  <input id="confirmaPin" type="password" inputMode="numeric" maxLength={8} value={confirmaPin} onChange={(e) => setConfirmaPin(e.target.value.replace(/\D/g, ''))} />
                </div>
                <div className="btn-row">
                  <button className="btn primary" onClick={cadastrarPin}>Cadastrar PIN</button>
                </div>
              </>
            ) : (
              <>
                <span className="hint" style={{ display: 'block', marginBottom: 10 }}>
                  PIN ativo. Informe o PIN atual para alterar ou remover.
                </span>
                <div className="field">
                  <label htmlFor="pinAtual">PIN atual</label>
                  <input id="pinAtual" type="password" inputMode="numeric" maxLength={8} value={pinAtual} onChange={(e) => setPinAtual(e.target.value.replace(/\D/g, ''))} />
                </div>
                <div className="field">
                  <label htmlFor="novoPinAlt">Novo PIN (opcional)</label>
                  <input id="novoPinAlt" type="password" inputMode="numeric" maxLength={8} value={novoPin} onChange={(e) => setNovoPin(e.target.value.replace(/\D/g, ''))} />
                </div>
                <div className="field">
                  <label htmlFor="confirmaPinAlt">Confirmar novo PIN</label>
                  <input id="confirmaPinAlt" type="password" inputMode="numeric" maxLength={8} value={confirmaPin} onChange={(e) => setConfirmaPin(e.target.value.replace(/\D/g, ''))} />
                </div>
                <div className="btn-row">
                  <button className="btn primary" onClick={alterarPin}>Alterar PIN</button>
                  <button className="btn" onClick={() => setPhase('locked')}>Bloquear agora</button>
                  <button className="btn danger" onClick={excluirPin}>Remover PIN</button>
                </div>
              </>
            )}
            {msgSeg && (
              <div className={msgSeg.tipo === 'ok' ? 'auth-ok' : 'auth-erro'} style={{ marginTop: 10 }}>
                {msgSeg.texto}
              </div>
            )}
          </div>

          <div className="card">
            <h2>Manutenção</h2>
            <div className="btn-row">
              <button className="btn danger" onClick={resetSettings}>Restaurar Padrões</button>
            </div>
            <span className="hint" style={{ display: 'block', marginTop: 8 }}>
              As configuracoes ficam persistidas localmente (localStorage, chave xau-ai-pro).
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
