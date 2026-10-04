import { useEffect, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import { useAuthStore } from '../auth/authStore';
import { definirPin, removerPin, validarPin, verificarPin } from '../auth/auth';
import { THEMES } from '../hooks/useTheme';
import ConnectionSettings from './ConnectionSettings';
import ConnectedDevicesPanel from './ConnectedDevicesPanel';
import DeclaracoesConfianca from './DeclaracoesConfianca';
import '../theme/settings.css';

type Section = 'general' | 'connections' | 'security' | 'confianca';
const tabs: [Section, string][] = [
  ['general', 'Geral / Interface'],
  // "Notificações & Alertas" saiu: a seção existia no menu sem renderizar
  // nada, e a aba Alertas também foi removida. Um item que abre uma tela vazia
  // é pior que não existir.
  ['connections', 'Conexões & Corretoras'],
  ['security', 'Segurança'],
  // Declarações de confiança: o que o app faz, o que nunca faz, e quem
  // developeu. Cada afirmação da tela tem um teste ou auditoria por trás.
  ['confianca', 'Confiança & Responsável'],
];
const fmt = (v: unknown) => {
  const n = Number(v);
  return Number.isFinite(n)
    ? n.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : '--';
};
export default function SettingsCore() {
  const settings = useAppStore((state) => state.settings);
  const setSettings = useAppStore((state) => state.setSettings);
  // O auth.json no disco e a fonte da verdade do PIN; o espelho no store serve
  // apenas para desenhar a interface.
  const hasPin = useAuthStore((state) => state.hasPin);
  const setHasPin = useAuthStore((state) => state.setHasPin);
  const [section, setSection] = useState<Section>('general');
  const [status, setStatus] = useState('');
  const [pin1, setPin1] = useState('');
  const [pin2, setPin2] = useState('');
  const [pinAtual, setPinAtual] = useState('');
  const [connected, setConnected] = useState(false);
  const [account, setAccount] = useState<Record<string, unknown> | null>(null);
  const [connectivity, setConnectivity] = useState<Record<string, string>>({});
  const refreshAccount = () => {
    fetch(`${apiBase()}/api/status`, { signal: AbortSignal.timeout(5000) })
      .then((r) => r.json())
      .then((d: any) => setConnected(Boolean(d?.terminal_connected)))
      .catch(() => setConnected(false));
    fetch(`${apiBase()}/api/account`, { signal: AbortSignal.timeout(5000) })
      .then((r) => r.json())
      .then((data: any) => {
        const a = data && typeof data === 'object' ? (data.account ?? data) : null;
        setAccount(a && typeof a === 'object' ? a : null);
      })
      .catch(() => setAccount(null));
  };
  useEffect(() => {
    refreshAccount();
    const timer = window.setInterval(refreshAccount, 15000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    if (section !== 'connections') return;
    let active = true;
    const check = async () => {
      const items: Record<string, string> = {};
      for (const [name, path] of [
        ['Gateway local', '/api/health'],
        ['MT5', '/api/status'],
        ['MEXC API', '/api/universal/account?broker=mexc&market=crypto-spot'],
        ['Binance API', '/api/universal/account?broker=binance&market=crypto-spot'],
      ] as const) {
        const started = performance.now();
        try {
          const response = await fetch(`${apiBase()}${path}`, {
            signal: AbortSignal.timeout(5000),
          });
          items[name] = response.ok
            ? `Online · ${Math.round(performance.now() - started)} ms`
            : 'Indisponível';
        } catch {
          items[name] = 'Indisponível';
        }
      }
      if (active) setConnectivity(items);
    };
    void check();
    const timer = window.setInterval(check, 15000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [section]);
  const createPin = async () => {
    if (!pin1 || pin1 !== pin2) {
      setStatus('Os PINs digitados não conferem.');
      return;
    }
    const error = validarPin(pin1);
    if (error) {
      setStatus(error);
      return;
    }
    if (hasPin) {
      // Troca de PIN exige prova de posse do PIN atual.
      const erroAtual = validarPin(pinAtual);
      if (erroAtual) {
        setStatus(erroAtual);
        return;
      }
      const confere = await verificarPin(pinAtual).catch(() => false);
      if (!confere) {
        setStatus('PIN atual incorreto. O PIN não foi alterado.');
        setPinAtual('');
        return;
      }
    }
    const gravado = await definirPin(pin1)
      .then(() => true)
      .catch(() => false);
    if (!gravado) {
      setStatus('Falha ao gravar o PIN. Verifique as permissões da pasta de dados.');
      return;
    }
    setHasPin(true);
    setSettings({ pinEnabled: true, pinCode: '' });
    setPin1('');
    setPin2('');
    setPinAtual('');
    setStatus(hasPin ? 'PIN alterado com sucesso.' : 'PIN ativado e salvo neste dispositivo.');
  };
  const togglePin = async () => {
    if (hasPin) {
      const pin = window.prompt('Digite o PIN atual para desativar:') || '';
      const error = validarPin(pin);
      if (error) {
        setStatus(error);
        return;
      }
      const confere = await verificarPin(pin).catch(() => false);
      if (!confere) {
        setStatus('PIN atual incorreto. O PIN continua ativo.');
        return;
      }
      const removido = await removerPin()
        .then(() => true)
        .catch(() => false);
      if (!removido) {
        setStatus('Falha ao remover o PIN. O PIN continua ativo.');
        return;
      }
      setHasPin(false);
      setSettings({ pinEnabled: false, pinCode: '' });
      setStatus('PIN desativado.');
      return;
    }
    setSection('security');
  };

  return (
    <div className="card settings-card">
      <div className="section-head">
        <div>
          <h2>Configurações</h2>
          <span className="muted">Interface, alertas, conexões e segurança</span>
        </div>
        <span className={`chip ${connected ? 'ok' : 'warn'}`}>
          {connected ? 'MT5 conectado' : 'MT5 desconectado'}
        </span>
      </div>
      <div className="settings-layout">
        <nav className="settings-nav" aria-label="Seções de configuração">
          {tabs.map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={`settings-nav-item ${section === id ? 'active' : ''}`}
              onClick={() => setSection(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        {section === 'general' && (
          <div className="settings-panel">
            <h3>🎨 Tema da interface</h3>
            <div className="theme-grid">
              {THEMES.map((theme) => (
                <button
                  key={theme.id}
                  type="button"
                  className={`theme-swatch theme-swatch-${theme.id} ${settings.theme === theme.id ? 'selected' : ''}`}
                  onClick={() => setSettings({ theme: theme.id })}
                >
                  <span className="theme-preview" aria-hidden="true">
                    <i />
                    <i />
                    <i />
                  </span>
                  <span className="theme-name">{theme.label}</span>
                  {settings.theme === theme.id && <span className="chip ok">ativo</span>}
                </button>
              ))}
            </div>
            {/*
              PREFERENCIAS — só o que tem consumidor de verdade.

              Removidos nesta limpeza, com medição de uso no codigo:
                - Animações da interface .... 0 leituras
                - Sons de alerta ............ 0 leituras, e estava DUPLICADO
                                            aqui e em Notificações
                - Notificações do sistema .. 0 leituras, e duplicado
                - Auto-scroll terminais .... 0 leituras
              Um interruptor que nada faz e pior que a ausencia dele: o
              usuario acredita que esta protegido. Ficou só a precisão
              decimal, que o formatador realmente usa.
            */}
            <h3>Preferências</h3>
            <div className="settings-rows">
              <label className="switch-row">
                <span>Casas decimais: {settings.precision}</span>
                <input
                  type="range"
                  min={0}
                  max={5}
                  value={settings.precision}
                  onChange={(e) => setSettings({ precision: Number(e.target.value) })}
                />
              </label>
            </div>
          </div>
        )}
        {/*
          A SECAO DE NOTIFICACOES FOI REMOVIDA.

          Os 10 campos de Slack / Telegram / Discord nao tinham consumidor: o
          `lib/notify.ts` so emite notificacao nativa do sistema operacional, via
          Tauri. Nenhum fetch era feito para webhook nenhum. Alem disso, "Sons
          de alerta" e "Notificações do sistema" apareciam aqui E em Preferências,
          ligados ao mesmo campo do store — dois interruptores, um efeito.

          O que realmente notifica hoje:
            - abas de Alertas e de Inteligência Artificial (notificação nativa)
            - abas de Mercado, Patrimônio e Sistema (plUGIN de notificação)
          Quando houver canal externo de verdade, ele nasce aqui — com código
          que o consuma, não campos que fingem configurar.
        */}
        {section === 'connections' && (
          <div className="settings-panel">
            {/*
              CONEXOES — só configuração. Nada de leitura de conta aqui.

              Removido nesta limpeza, por duplicação:
                - "Saúde das conexões"  -> aba Sistema (mostra core, watchdog,
                  filas e telemetria; é o lugar de diagnóstico)
                - "Conta ativa" com Login/Servidor/Moeda/Saldo/Patrimônio
                  -> aba Patrimônio (que já mostra saldo, disponível e
                  posições por corretora). Três telas com o mesmo saldo
                  é o tipo de coisa que faz o usuário duvidar do número.
                - "Conectar automaticamente" — 0 leituras e sempre `disabled`.

              O que fica aqui: o caminho do terminal. É configuração de verdade,
              e só ela pertence a esta seção.
            */}
            <h3>MetaTrader 5</h3>
            <div className="settings-rows">
              <label className="switch-row">
                <span>Caminho do terminal</span>
                <input
                  className="input"
                  value={settings.mt5Path}
                  onChange={(e) => setSettings({ mt5Path: e.target.value })}
                  placeholder="terminal64.exe"
                />
              </label>
            </div>
            <ConnectionSettings />
            <ConnectedDevicesPanel />
            <p className="hint">
              Por segurança o app nunca inicia o MT5 sozinho — a conexão é uma ação sua, na aba do
              Robô.
            </p>
          </div>
        )}
        {section === 'security' && (
          <div className="settings-panel">
            {/*
              A SECAO "Risco & IA" FOI REMOVIDA daqui.

              - Risco (limites, stop de emergencia, estado do risk_gate) pertence
                a aba Risco, que mostra os valores REAIS vindos do gateway. Aqui
                os limites eram só estado local do navegador, com o próprio
                código avisando "somente aviso nesta tela".
              - IA (ligar motor, escolher modelo, intervalo) pertence a aba
                Inteligência Artificial, que mostra a inferência real, a
                confiança real e o edge do modelo. O campo `aiModel` era texto
                livre e não casava com nenhum modelo do catálogo.

              Esta seção guarda só o PIN, porque é a única coisa que é
              configuração de segurança de verdade — e o lugar de verdade é a
              tela de bloqueio, logo na abertura do app. A credencial é criada e
              destruída aqui; nunca no meio de uma tela de trading.
            */}
            <h3>PIN de acesso</h3>
            <p className="hint">
              O PIN protege a abertura do app e é pedido na tela de bloqueio. Validado com
              PBKDF2-SHA256 (150k iterações) e salvo apenas neste dispositivo.
            </p>
            <div className="settings-rows">
              <label className="switch-row">
                <span>Exigir PIN ao abrir o app</span>
                <input type="checkbox" checked={hasPin} onChange={() => void togglePin()} />
              </label>
            </div>
            <div className="pin-form">
              {hasPin && (
                <input
                  className="input"
                  type="password"
                  inputMode="numeric"
                  maxLength={8}
                  placeholder="PIN atual (para trocar)"
                  value={pinAtual}
                  onChange={(e) => setPinAtual(e.target.value.replace(/\D/g, ''))}
                />
              )}
              <input
                className="input"
                type="password"
                inputMode="numeric"
                maxLength={8}
                placeholder="Novo PIN (4-8 dígitos)"
                value={pin1}
                onChange={(e) => setPin1(e.target.value.replace(/\D/g, ''))}
              />
              <input
                className="input"
                type="password"
                inputMode="numeric"
                maxLength={8}
                placeholder="Confirmar PIN"
                value={pin2}
                onChange={(e) => setPin2(e.target.value.replace(/\D/g, ''))}
              />
              <button type="button" className="btn primary sm" onClick={() => void createPin()}>
                {hasPin ? 'Alterar PIN' : 'Salvar PIN'}
              </button>
            </div>
            {hasPin && (
              <p className="hint">
                Para desativar o PIN é necessário informar o PIN atual. O app nunca remove a
                credencial sozinho.
              </p>
            )}
            {status && (
              <div className="hint" role="status">
                {status}
              </div>
            )}
          </div>
        )}

        {section === 'confianca' && (
          <div className="settings-panel">
            <DeclaracoesConfianca />
          </div>
        )}
      </div>
    </div>
  );
}
