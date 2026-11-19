// Assistente de primeiro acesso (somente mobile).
//
// Tres passos: Conexao -> Permissoes -> Seguranca. Nao abre nada por conta
// propria: a navegacao para o login acontece ao confirmar o passo 3.
//
// REGRAS DE ESTE COMPONENTE
// =========================
// 1. Nada de hardcode de porta de producao: o default e o tunel USB do
//    ambiente de auditoria (127.0.0.1:9001 -> gateway demo do PC). O campo e
//    editavel e fica salvo em localStorage `xau-api-base`, que e o MESMO que
//    a tela de login/conexao le depois.
// 2. Permissoes: nada e solicitado no mount. Cada tap do operador dispara a
//    API nativa (Tauri plugin-notification / Web Audio / navigator) na hora
//    do clique - nunca antes.
// 3. Sem permissao concedida, o app SEGUE: todas as permissoes sao
//    opcionais e degradam em silencio (a Central mobile ja trata isso).
import React, { useState } from 'react';
import {
  garantirPermissaoNotificacao,
  solicitarExcecaoBateria,
  tocarAlertaSonoro,
  vibrarAlerta,
} from '../lib/mobileAlerts';

const CHAVE_ONBOARDING = 'xau_onboarding_done';
const CHAVE_GATEWAY = 'xau-api-base';

export default function FirstRunWizard({
  onComplete,
  gatewayDefault = 'http://127.0.0.1:9001',
}: {
  onComplete: () => void;
  gatewayDefault?: string;
}) {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [gateway, setGateway] = useState(gatewayDefault);
  const [notif, setNotif] = useState<string>('Pendente');
  const [somOk, setSomOk] = useState(false);
  const [bateriaOk, setBateriaOk] = useState(false);
  const [aceite, setAceite] = useState(false);

  const terminar = () => {
    const url = gateway.trim();
    try {
      if (url) window.localStorage.setItem(CHAVE_GATEWAY, url);
      window.localStorage.setItem(CHAVE_ONBOARDING, '1');
    } catch {
      // localStorage indisponivel: o app segue e o Login pede a base de novo.
    }
    onComplete();
  };

  const pedirNotificacao = async () => {
    const ok = await garantirPermissaoNotificacao();
    setNotif(ok ? 'Concedida' : 'Recusada');
  };

  const testarSom = () => {
    tocarAlertaSonoro('sucesso');
    vibrarAlerta('sucesso');
    setSomOk(true);
  };

  const pedirBateria = async () => {
    const ok = await solicitarExcecaoBateria();
    setBateriaOk(ok);
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--bg, #070b14)',
        color: 'var(--text, #f8fafc)',
        padding: 'max(env(safe-area-inset-top), 36px) 16px 32px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <div
        style={{
          maxWidth: 440,
          width: '100%',
          background: 'var(--panel, #0f172a)',
          border: '1px solid var(--border, #1e293b)',
          borderRadius: 14,
          padding: 20,
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            fontSize: 11,
            color: 'var(--muted, #94a3b8)',
            marginBottom: 14,
          }}
        >
          <span style={{ color: step >= 1 ? 'var(--accent, #f59e0b)' : undefined, fontWeight: 700 }}>
            1. CONEXÃO
          </span>
          <span style={{ color: step >= 2 ? 'var(--accent, #f59e0b)' : undefined, fontWeight: 700 }}>
            2. PERMISSÕES
          </span>
          <span style={{ color: step === 3 ? 'var(--accent, #f59e0b)' : undefined, fontWeight: 700 }}>
            3. SEGURANÇA
          </span>
        </div>

        {step === 1 && (
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 800, margin: '0 0 8px' }}>
              Bem-vindo ao XAU AI PRO
            </h2>
            <p style={{ fontSize: 13, color: 'var(--muted, #94a3b8)', lineHeight: 1.5, marginBottom: 16 }}>
              Plataforma <strong>Local-First & Fail-Closed</strong>. O robô opera no MetaTrader 5;
              você acompanha do PC ou do celular. Nada aqui autoriza movimentações — toda ordem
              exige seu gateway e sua sessão.
            </p>
            <label style={{ fontSize: 12, color: 'var(--text, #f8fafc)', marginBottom: 6, display: 'block' }}>
              Endereço do Gateway (USB/túnel do seu PC, ou remoto configurado):
            </label>
            <input
              type="text"
              value={gateway}
              onChange={(e) => setGateway(e.target.value)}
              autoCapitalize="none"
              autoCorrect="off"
              spellCheck={false}
              style={{
                width: '100%',
                padding: 10,
                borderRadius: 8,
                background: 'var(--bg, #070b14)',
                border: '1px solid var(--border, #1e293b)',
                color: 'var(--accent, #f59e0b)',
                fontSize: 13,
                marginBottom: 6,
                boxSizing: 'border-box',
              }}
            />
            <p style={{ fontSize: 11, color: 'var(--muted, #94a3b8)', margin: '0 0 16px' }}>
              Com o cabo USB e o `adb reverse` ativos, use http://127.0.0.1:9001. Para um gateway
              remoto, informe a URL completa (https://…).
            </p>
            <button
              type="button"
              className="btn primary"
              style={{ width: '100%' }}
              onClick={() => setStep(2)}
            >
              Continuar para Permissões →
            </button>
          </div>
        )}

        {step === 2 && (
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 800, margin: '0 0 6px' }}>
              Permissões do aparelho
            </h2>
            <p style={{ fontSize: 12, color: 'var(--muted, #94a3b8)', marginBottom: 14 }}>
              Opcionais; o app funciona sem elas. Cada pedido dispara só quando você toca.
            </p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 18 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 10, background: 'var(--bg, #070b14)', borderRadius: 8, gap: 8 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700 }}>Notificações</div>
                  <div style={{ fontSize: 11, color: 'var(--muted, #94a3b8)' }}>Status: {notif}</div>
                </div>
                <button type="button" className="btn xs ghost" onClick={() => void pedirNotificacao()}>
                  Autorizar
                </button>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 10, background: 'var(--bg, #070b14)', borderRadius: 8, gap: 8 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700 }}>Som &amp; vibração</div>
                  <div style={{ fontSize: 11, color: 'var(--muted, #94a3b8)' }}>{somOk ? 'Testado' : 'Tocar alerta de exemplo'}</div>
                </div>
                <button type="button" className="btn xs ghost" onClick={testarSom}>
                  Testar som
                </button>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: 10, background: 'var(--bg, #070b14)', borderRadius: 8, gap: 8 }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700 }}>Bateria</div>
                  <div style={{ fontSize: 11, color: 'var(--muted, #94a3b8)' }}>{bateriaOk ? 'Isento de otimização' : 'Evita dormir em segundo plano'}</div>
                </div>
                <button type="button" className="btn xs ghost" onClick={() => void pedirBateria()}>
                  Liberar
                </button>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" className="btn ghost" style={{ flex: 1 }} onClick={() => setStep(1)}>
                ← Voltar
              </button>
              <button type="button" className="btn primary" style={{ flex: 2 }} onClick={() => setStep(3)}>
                Próximo →
              </button>
            </div>
          </div>
        )}

        {step === 3 && (
          <div>
            <h2 style={{ fontSize: 17, fontWeight: 800, margin: '0 0 8px' }}>
              Governança &amp; risco
            </h2>
            <div style={{ padding: 12, background: 'var(--bg, #070b14)', borderRadius: 8, fontSize: 12, color: 'var(--muted, #cbd5e1)', marginBottom: 14, lineHeight: 1.55 }}>
              • Nenhuma tela aqui autoriza saques ou movimentações externas.<br />
              • Toda operação exige token de sessão válido (Fail-Closed).<br />
              • Teste sempre em conta Demo antes de capital real.<br />
              • Seu ponto de contato é o portal oficial: github.com/apolopanda500/XAU_AI_PRO
            </div>
            <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, fontSize: 12, marginBottom: 18, cursor: 'pointer' }}>
              <input type="checkbox" checked={aceite} onChange={(e) => setAceite(e.target.checked)} />
              <span>Li e concordo com os termos de uso e com a gestão de risco do app.</span>
            </label>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="button" className="btn ghost" style={{ flex: 1 }} onClick={() => setStep(2)}>
                ← Voltar
              </button>
              <button type="button" className="btn primary" style={{ flex: 2 }} disabled={!aceite} onClick={terminar}>
                Ir para Login ✔
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
