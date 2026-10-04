/**
 * Estado de risco e parada de emergencia, com fonte de verdade no gateway.
 *
 * Antes desta mudanca a aba Risco recalculava tudo no cliente a partir de
 * balance/equity, e o toggle "Auto-Parar" era um `useState` do React: nao
 * enviava nada, nao parava o guardian e nao bloqueava ordem alguma. O
 * endpoint `/api/risk/state` existia e nao tinha consumidor, sendo justamente
 * a evidencia de que o risk_gate recebe dado real.
 *
 * Aqui as tres coisas passam a ter efeito real:
 *   1. as metricas vem de GET /api/risk/state (deals do dia + posicoes + pico);
 *   2. a parada de emergencia chama POST /api/universal/emergency-stop;
 *   3. a retomada chama emergency-resume, que o gateway so aceita com
 *      XAU_ENABLE_EMERGENCY_RESUME=1.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { apiBase } from '../lib/api';
import { notify } from '../lib/notify';

export interface RiskStateReal {
  ok: boolean;
  daily_loss_pct: number | null;
  exposure_pct: number | null;
  open_positions: number | null;
  daily_trades: number | null;
  drawdown_pct: number | null;
  limits?: Record<string, unknown>;
  source?: string;
  error?: string;
}

export interface KillSwitchState {
  /** Indeterminado enquanto o gateway nao responde: nao afirmar que esta livre. */
  status: 'desconhecido' | 'livre' | 'ativo';
  busy: boolean;
  erro: string | null;
}

function numero(valor: unknown): number | null {
  const n = Number(valor);
  return Number.isFinite(n) ? n : null;
}

export function useRealRisk() {
  const [estado, setEstado] = useState<RiskStateReal | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [kill, setKill] = useState<KillSwitchState>({
    status: 'desconhecido',
    busy: false,
    erro: null,
  });
  const vivo = useRef(true);

  const lerEstado = useCallback(async () => {
    try {
      const r = await fetch(`${apiBase()}/api/risk/state`, { signal: AbortSignal.timeout(8000) });
      const body = await r.json().catch(() => ({}));
      if (!vivo.current) return;
      if (!r.ok) {
        setErro((body as { error?: string })?.error || `HTTP ${r.status}`);
        return;
      }
      setErro(null);
      setEstado({
        ok: true,
        daily_loss_pct: numero((body as Record<string, unknown>).daily_loss_pct),
        exposure_pct: numero((body as Record<string, unknown>).exposure_pct),
        open_positions: numero((body as Record<string, unknown>).open_positions),
        daily_trades: numero((body as Record<string, unknown>).daily_trades),
        drawdown_pct: numero((body as Record<string, unknown>).drawdown_pct),
        limits: (body as { limits?: Record<string, unknown> }).limits,
        source: (body as { source?: string }).source,
      });
    } catch (e) {
      if (vivo.current) setErro(String(e));
    } finally {
      if (vivo.current) setCarregando(false);
    }
  }, []);

  useEffect(() => {
    vivo.current = true;
    void lerEstado();
    const timer = window.setInterval(() => void lerEstado(), 15000);
    return () => {
      vivo.current = false;
      window.clearInterval(timer);
    };
  }, [lerEstado]);

  const acionar = useCallback(async (acao: 'stop' | 'resume') => {
    setKill((k) => ({ ...k, busy: true, erro: null }));
    const endpoint = acao === 'stop' ? 'emergency-stop' : 'emergency-resume';
    try {
      const r = await fetch(`${apiBase()}/api/universal/${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: true }),
        signal: AbortSignal.timeout(8000),
      });
      const body = (await r.json().catch(() => ({}))) as {
        error?: string;
        emergency_stop?: boolean;
      };
      if (!r.ok) {
        const mensagem = body?.error || `HTTP ${r.status}`;
        setKill((k) => ({ ...k, busy: false, erro: mensagem }));
        void notify('Parada de emergencia recusada', mensagem);
        return;
      }
      setKill((k) => ({
        ...k,
        busy: false,
        erro: null,
        status: acao === 'stop' ? 'ativo' : 'livre',
      }));
      void notify(
        acao === 'stop' ? 'Execução parada' : 'Execução retomada',
        acao === 'stop'
          ? 'O gateway recusará novas ordens até a retomada.'
          : 'O gateway voltou a aceitar comandos.',
      );
    } catch (e) {
      setKill((k) => ({ ...k, busy: false, erro: String(e) }));
    }
  }, []);

  return {
    estado,
    carregando,
    erro,
    refresh: lerEstado,
    parar: () => acionar('stop'),
    retomar: () => acionar('resume'),
    kill,
  };
}
