// Alertas móveis: som (Web Audio), vibração e notificação nativa/web.
// Uso defensivo: em ambientes sem permissão/suporte, falha em silêncio com retorno informativo.

import { isPermissionGranted, requestPermission, sendNotification } from '@tauri-apps/plugin-notification';
import { isMobileRuntime } from './api';

export type TipoAlertaMobile = 'info' | 'sucesso' | 'aviso' | 'critico';

export async function garantirPermissaoNotificacao(): Promise<boolean> {
  try {
    let granted = await isPermissionGranted();
    if (!granted) {
      const perm = await requestPermission();
      granted = perm === 'granted';
    }
    return granted;
  } catch {
    if (typeof Notification !== 'undefined') {
      if (Notification.permission === 'granted') return true;
      if (Notification.permission !== 'denied') {
        try {
          return (await Notification.requestPermission()) === 'granted';
        } catch {
          return false;
        }
      }
    }
    return false;
  }
}

function freqPorTipo(tipo: TipoAlertaMobile): number {
  switch (tipo) {
    case 'sucesso':
      return 880;
    case 'aviso':
      return 520;
    case 'critico':
      return 220;
    default:
      return 660;
  }
}

export function tocarAlertaSonoro(tipo: TipoAlertaMobile = 'info'): void {
  try {
    const Ctx = window.AudioContext || (window as any).webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = tipo === 'critico' ? 'sawtooth' : 'sine';
    osc.frequency.value = freqPorTipo(tipo);
    gain.gain.value = 0.0001;
    osc.connect(gain);
    gain.connect(ctx.destination);
    const now = ctx.currentTime;
    gain.gain.exponentialRampToValueAtTime(0.12, now + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.0001, now + (tipo === 'critico' ? 0.45 : 0.22));
    osc.start(now);
    osc.stop(now + (tipo === 'critico' ? 0.5 : 0.25));
    osc.onended = () => {
      void ctx.close().catch(() => undefined);
    };
  } catch {
    // sem áudio disponível
  }
}

export function vibrarAlerta(tipo: TipoAlertaMobile = 'info'): void {
  try {
    if (!('vibrate' in navigator)) return;
    const padrao =
      tipo === 'critico' ? [120, 60, 120, 60, 220] : tipo === 'aviso' ? [80, 40, 120] : [60];
    navigator.vibrate(padrao);
  } catch {
    // sem vibração
  }
}

export async function notificarAlerta(titulo: string, corpo: string): Promise<void> {
  try {
    if (await garantirPermissaoNotificacao()) {
      try {
        await sendNotification({ title: titulo, body: corpo });
        return;
      } catch {
        // fallback web abaixo
      }
    }
    if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      new Notification(titulo, { body: corpo });
    }
  } catch {
    // sem notificação
  }
}

export async function dispararAlertaMobile(
  titulo: string,
  corpo: string,
  tipo: TipoAlertaMobile = 'info',
): Promise<void> {
  if (!isMobileRuntime()) return;
  tocarAlertaSonoro(tipo);
  vibrarAlerta(tipo);
  await notificarAlerta(titulo, corpo);
}

export async function testarAlertaMobile(): Promise<void> {
  tocarAlertaSonoro('sucesso');
  vibrarAlerta('sucesso');
  await notificarAlerta('XAU AI PRO', 'Teste de alerta sonoro, vibração e notificação concluído.');
}

export async function solicitarExcecaoBateria(): Promise<boolean> {
  // Implementação nativa completa depende de plugin/plataforma; aqui abrimos
  // intenção informativa quando disponível e retornamos false se não suportado.
  try {
    const w = window as any;
    if (w.__TAURI__?.core?.invoke) {
      await w.__TAURI__.core.invoke('abrir_configuracao_bateria').catch(() => undefined);
      return true;
    }
  } catch {
    // fallback
  }
  return false;
}
