import React, { useMemo, useState } from 'react';
import { isMobileRuntime } from '../lib/api';
import { exportarJson } from '../lib/mobileExport';
import { garantirPermissaoNotificacao, solicitarExcecaoBateria, testarAlertaMobile } from '../lib/mobileAlerts';

export const MobilePermissionsHub: React.FC = () => {
  const mobile = isMobileRuntime();
  const [status, setStatus] = useState<string>('');
  const [notif, setNotif] = useState<string>(
    typeof Notification !== 'undefined' ? Notification.permission : 'indisponível',
  );

  const online = typeof navigator !== 'undefined' ? navigator.onLine : false;
  const info = useMemo(
    () => ({
      mobile,
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
      online,
      notification: notif,
      horario: new Date().toISOString(),
    }),
    [mobile, online, notif],
  );

  if (!mobile) {
    return (
      <div className="card compact-card" style={{ marginTop: 12 }}>
        <h3 style={{ marginTop: 0 }}>Central móvel</h3>
        <p className="muted" style={{ marginBottom: 0 }}>
          Recursos nativos móveis (notificações, áudio/vibração, exportação e bateria) ficam disponíveis no app Android.
        </p>
      </div>
    );
  }

  return (
    <div className="card compact-card" style={{ marginTop: 12 }}>
      <div className="section-head" style={{ marginBottom: 8 }}>
        <div>
          <h3 style={{ margin: 0 }}>Permissões & Recursos Móveis</h3>
          <span className="muted">Notificações, som/vibração, bateria e exportação</span>
        </div>
        <span className="chip ok">Android</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8 }}>
        <button
          type="button"
          className="btn sm"
          onClick={async () => {
            const ok = await garantirPermissaoNotificacao();
            setNotif(typeof Notification !== 'undefined' ? Notification.permission : ok ? 'granted' : 'denied');
            setStatus(ok ? 'Permissão de notificação concedida/disponível.' : 'Notificação não concedida neste ambiente.');
          }}
        >
          Solicitar notificações
        </button>

        <button
          type="button"
          className="btn sm"
          onClick={async () => {
            await testarAlertaMobile();
            setStatus('Teste de alerta sonoro, vibração e notificação disparado.');
          }}
        >
          Testar alerta (som/push)
        </button>

        <button
          type="button"
          className="btn sm"
          onClick={async () => {
            const ok = await solicitarExcecaoBateria();
            setStatus(
              ok
                ? 'Solicitação de otimização de bateria enviada (quando suportada pelo sistema).'
                : 'Ajuste de bateria não suportado automaticamente neste build; configure manualmente nas opções do app.',
            );
          }}
        >
          Bateria sem restrição
        </button>

        <button
          type="button"
          className="btn sm"
          onClick={async () => {
            await exportarJson(`xau-ai-pro-mobile-status-${Date.now()}`, info);
            setStatus('Relatório de status móvel exportado/compartilhado.');
          }}
        >
          Exportar status (JSON)
        </button>
      </div>

      <div style={{ marginTop: 10, fontSize: 12, color: 'var(--muted, #94a3b8)' }}>
        <div>Notificação: <strong>{notif}</strong></div>
        <div>Conexão: <strong>{online ? 'online' : 'offline'}</strong></div>
        {status ? <div style={{ marginTop: 6 }}>{status}</div> : null}
      </div>
    </div>
  );
};

export default MobilePermissionsHub;
