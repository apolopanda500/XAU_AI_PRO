import { useCallback, useEffect, useState } from 'react';
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
  const [mt5State, setMt5State] = useState<'Aguardando' | 'Conectado' | 'Indisponível'>('Aguardando');
  const [mt5Checking, setMt5Checking] = useState(false);
  const [profileName, setProfileName] = useState('');
  const [profileLogin, setProfileLogin] = useState('');
  const [profileServer, setProfileServer] = useState('');
  const [profiles, setProfiles] = useState<Array<{ name: string; login: string; server: string }>>(() => {
    try { return JSON.parse(localStorage.getItem('xau-ai-pro-account-profiles') || '[]') as Array<{ name: string; login: string; server: string }>; } catch { return []; }
  });
  const checkMt5 = useCallback(async () => {
    setMt5Checking(true);
    try { const response = await fetch('http://127.0.0.1:9001/api/health', { signal: AbortSignal.timeout(5000) }); setMt5State(response.ok ? 'Conectado' : 'Indisponível'); }
    catch { setMt5State('Indisponível'); }
    finally { setMt5Checking(false); }
  }, []);
  useEffect(() => { void checkMt5(); }, [checkMt5]);
  function addProfile(): void {
    if (!profileName.trim() || !profileLogin.trim() || !profileServer.trim()) return;
    const next = [...profiles, { name: profileName.trim(), login: profileLogin.trim(), server: profileServer.trim() }];
    setProfiles(next); localStorage.setItem('xau-ai-pro-account-profiles', JSON.stringify(next)); setProfileName(''); setProfileLogin(''); setProfileServer('');
  }
  function removeProfile(index: number): void { const next = profiles.filter((_, i) => i !== index); setProfiles(next); localStorage.setItem('xau-ai-pro-account-profiles', JSON.stringify(next)); }

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
                <div className="switch-label">IA para análise</div>
                <div className="switch-desc">Copiloto e análise de mercado; não envia ordens</div>
              </div>
              <button className={`switch ${settings.aiEnabled ? 'on' : ''}`} aria-label="Alternar ia" onClick={() => setSettings({ aiEnabled: !settings.aiEnabled })} />
            </div>
            <div className="field">
              <label htmlFor="aimodel">Modelo</label>
              <select id="aimodel" value={settings.aiModel} onChange={(e) => setSettings({ aiModel: e.target.value })}>
                <option value="openai/gpt-5.6-sol">OpenAI via AI Gateway</option>
                <option value="xau-pro-v2">XAU PRO v2 (se configurado)</option>
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
            <h2>Conexões reais</h2>
            <div className="switch-row"><div><div className="switch-label">Bridge MT5</div><div className="switch-desc">Gateway local somente leitura</div></div><span className={`chip ${mt5State === 'Conectado' ? 'ok' : 'warn'}`}>{mt5State}</span></div>
            <button className="btn sm ghost" type="button" onClick={() => void checkMt5()} disabled={mt5Checking}>{mt5Checking ? 'Testando...' : 'Testar conexão MT5'}</button>
          </div>

          <div className="card" style={{ marginBottom: 14 }}>
            <h2>Perfis de contas MT5</h2><span className="hint" style={{ display: 'block', marginBottom: 10 }}>Salva apenas identificação local. Senhas, tokens e chaves nunca são armazenados pelo app.</span>
            <div className="grid cols-3"><div className="field"><label htmlFor="profile-name">Nome</label><input id="profile-name" value={profileName} onChange={(e) => setProfileName(e.target.value)} placeholder="Minha conta" /></div><div className="field"><label htmlFor="profile-login">Login</label><input id="profile-login" value={profileLogin} onChange={(e) => setProfileLogin(e.target.value)} placeholder="12345678" /></div><div className="field"><label htmlFor="profile-server">Servidor</label><input id="profile-server" value={profileServer} onChange={(e) => setProfileServer(e.target.value)} placeholder="Broker-Server" /></div></div>
            <button className="btn sm primary" type="button" onClick={addProfile}>Adicionar conta</button>
            {profiles.length > 0 && <div className="tbl-wrap" style={{ marginTop: 10 }}><table className="tbl"><tbody>{profiles.map((profile, index) => <tr key={`${profile.login}-${index}`}><td>{profile.name}</td><td className="mono">{profile.login}</td><td>{profile.server}</td><td><button className="btn sm danger" type="button" onClick={() => removeProfile(index)}>Remover</button></td></tr>)}</tbody></table></div>}
          </div>

          <div className="card" style={{ marginBottom: 14 }}>
            <h2>Permissões operacionais</h2>
            <div className="tbl-wrap"><table className="tbl"><tbody><tr><td>Leitura de mercado</td><td><span className="chip ok">Permitida</span></td></tr><tr><td>Ordens automáticas pelo app</td><td><span className="chip warn">Bloqueadas</span></td></tr><tr><td>Saque ou transferência</td><td><span className="chip warn">Bloqueados</span></td></tr><tr><td>Alteração do EA</td><td><span className="chip warn">Bloqueada</span></td></tr></tbody></table></div>
            <span className="hint" style={{ display: 'block', marginTop: 10 }}>A configuração manual do usuário e o terminal MT5 continuam sendo a autoridade operacional.</span>
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
              {hasPin && <button className="btn" type="button" onClick={() => setPhase('locked')}>Sair / bloquear app</button>}
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
