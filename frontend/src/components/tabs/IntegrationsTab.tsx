import { useAppStore } from '../../hooks/useAppStore';

export default function IntegrationsTab() {
  const settings = useAppStore((s) => s.settings);
  const setSettings = useAppStore((s) => s.setSettings);

  const toggle = (key: 'slackActive' | 'telegramActive' | 'discordActive') =>
    setSettings({ [key]: !settings[key] });

  return (
    <div>
      <div className="page-head">
        <h1>Integrações</h1>
        <span className="muted">Notificacoes externas (Slack, Telegram, Discord)</span>
      </div>

      <div className="grid cols-2">
        {/* Slack */}
        <div className="card">
          <h2>Slack</h2>
          <div className="switch-row">
            <div>
              <div className="switch-label">Slack ativo</div>
              <div className="switch-desc">Envia alertas de trade para o canal configurado</div>
            </div>
            <button className={`switch ${settings.slackActive ? 'on' : ''}`} aria-label="Alternar slack" onClick={() => toggle('slackActive')} />
          </div>
          <div className="field">
            <label htmlFor="slack-webhook">Webhook URL</label>
            <input
              id="slack-webhook"
              type="password"
              placeholder="https://hooks.slack.com/services/..."
              value={settings.slackWebhook}
              onChange={(e) => setSettings({ slackWebhook: e.target.value })}
            />
            <span className="hint">Armazenado localmente (settings persistidos do app).</span>
          </div>
        </div>

        {/* Telegram */}
        <div className="card">
          <h2>Telegram</h2>
          <div className="switch-row">
            <div>
              <div className="switch-label">Telegram ativo</div>
              <div className="switch-desc">Alertas via bot do Telegram</div>
            </div>
            <button className={`switch ${settings.telegramActive ? 'on' : ''}`} aria-label="Alternar telegram" onClick={() => toggle('telegramActive')} />
          </div>
          <div className="field">
            <label htmlFor="tg-token">Bot Token</label>
            <input
              id="tg-token"
              type="password"
              placeholder="123456:ABC-DEF..."
              value={settings.telegramToken}
              onChange={(e) => setSettings({ telegramToken: e.target.value })}
            />
          </div>
          <div className="field">
            <label htmlFor="tg-chat">Chat ID</label>
            <input
              id="tg-chat"
              type="text"
              placeholder="-1001234567890"
              value={settings.telegramChatId}
              onChange={(e) => setSettings({ telegramChatId: e.target.value })}
            />
          </div>
        </div>

        {/* Discord */}
        <div className="card">
          <h2>Discord</h2>
          <div className="switch-row">
            <div>
              <div className="switch-label">Discord ativo</div>
              <div className="switch-desc">Alertas via webhook do Discord</div>
            </div>
            <button className={`switch ${settings.discordActive ? 'on' : ''}`} aria-label="Alternar discord" onClick={() => toggle('discordActive')} />
          </div>
          <div className="field">
            <label htmlFor="dc-webhook">Webhook URL</label>
            <input
              id="dc-webhook"
              type="password"
              placeholder="https://discord.com/api/webhooks/..."
              value={settings.discordWebhook}
              onChange={(e) => setSettings({ discordWebhook: e.target.value })}
            />
          </div>
        </div>

        <div className="card">
          <h2>Segurança</h2>
          <p className="muted" style={{ fontSize: 13 }}>
            Credenciais ficam apenas neste dispositivo (localStorage). Nao sao enviadas a nenhum servidor
            do projeto. A integracao real de env sera ativada na Fase 4 (Core notificador).
          </p>
          <div className="btn-row" style={{ marginTop: 10 }}>
            <span className={`chip ${settings.slackActive ? 'ok' : ''}`}>Slack {settings.slackActive ? 'ON' : 'OFF'}</span>
            <span className={`chip ${settings.telegramActive ? 'ok' : ''}`}>Telegram {settings.telegramActive ? 'ON' : 'OFF'}</span>
            <span className={`chip ${settings.discordActive ? 'ok' : ''}`}>Discord {settings.discordActive ? 'ON' : 'OFF'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
