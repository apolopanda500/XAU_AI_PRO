import { useAppStore } from '../../hooks/useAppStore';
import { THEMES } from '../../hooks/useTheme';
import type { ThemeName } from '../../hooks/useAppStore';

export default function SettingsTab() {
  const settings = useAppStore((s) => s.settings);
  const setSettings = useAppStore((s) => s.setSettings);
  const resetSettings = useAppStore((s) => s.resetSettings);

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
