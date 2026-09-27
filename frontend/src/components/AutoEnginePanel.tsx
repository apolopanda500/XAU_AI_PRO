// Operacao automatica.
//
// O QUE ESTE PAINEL FAZ
// =====================
// Liga o motor que avalia o modelo treinado e envia ordens sozinho, com os
// limites que o operador declara. Nao ha numero de fallback aqui: cada campo
// vai para `/api/auto/config` e o proprio gateway valida e recusa.
//
// O QUE NAO ESTA NESTE PAINEL
// ===========================
// Aprovacao de ordem. O motor nao abre posicao sem que os limites passem, e
// o `/api/auto/start` so liga com limites validos. O Copiloto ao lado explica
// o que o motor fez, mas nao aperta botao por ele.
import { useCallback, useEffect, useState } from 'react';
import { apiBase } from '../lib/api';
import { notify } from '../lib/notify';
import '../theme/auto-engine.css';

const API = `${apiBase()}`;

type Limites = {
  banca: number;
  risco_por_trade_pct: number;
  confianca_minima: number;
  edge_minimo: number;
  max_posicoes: number;
  max_operacoes_dia: number;
  perda_diaria_max_pct: number;
  sl_atr: number;
  tp_atr: number;
  intervalo_minutos: number;
};

type Estado = {
  ativo: boolean;
  ciclo: number;
  simbolo: string;
  timeframe: string;
  threads: number;
  limites: Partial<Limites>;
  decisoes: Array<{ ts?: string; simbolo?: string; side?: string; acao?: string; motivo?: string; confianca?: number }>;
  updated_at?: string;
};

const CAMPOS: Array<{ chave: keyof Limites; rotulo: string; dica: string; passo: number }> = [
  { chave: 'banca', rotulo: 'Banca', dica: 'Base de calculo, nao o saldo da conta', passo: 10 },
  { chave: 'risco_por_trade_pct', rotulo: 'Risco por trade %', dica: '0 a 10', passo: 0.1 },
  { chave: 'confianca_minima', rotulo: 'Confianca minima %', dica: 'Probabilidade real do modelo', passo: 1 },
  { chave: 'edge_minimo', rotulo: 'Edge minimo', dica: '0.05 = 5%', passo: 0.01 },
  { chave: 'max_posicoes', rotulo: 'Max posicoes', dica: 'Simultaneas', passo: 1 },
  { chave: 'max_operacoes_dia', rotulo: 'Operacoes/dia', dica: 'Teto diario', passo: 1 },
  { chave: 'perda_diaria_max_pct', rotulo: 'Perda diaria %', dica: 'Ao atingir, o motor para', passo: 0.5 },
  { chave: 'sl_atr', rotulo: 'Stop (x ATR)', dica: 'Multiplicador de ATR', passo: 0.1 },
  { chave: 'tp_atr', rotulo: 'Alvo (x ATR)', dica: 'Multiplicador de ATR', passo: 0.1 },
  { chave: 'intervalo_minutos', rotulo: 'Intervalo (min)', dica: 'Entre avaliacoes', passo: 1 },
];

function num(v: string): number {
  return Number(String(v).replace(',', '.'));
}

export default function AutoEnginePanel() {
  const [limites, setLimites] = useState<Limites>({
    banca: 20, risco_por_trade_pct: 1, confianca_minima: 55, edge_minimo: 0.05,
    max_posicoes: 2, max_operacoes_dia: 20, perda_diaria_max_pct: 2,
    sl_atr: 1.5, tp_atr: 3, intervalo_minutos: 15,
  });
  const [estado, setEstado] = useState<Estado | null>(null);
  const [status, setStatus] = useState('');
  const [ocupado, setOcupado] = useState(false);

  const ler = useCallback(async (signal?: AbortSignal) => {
    const r = await fetch(`${API}/api/auto/state`, { signal: signal ?? AbortSignal.timeout(6000) });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = (await r.json()) as Estado;
    setEstado(d);
    return d;
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void ler(controller.signal).catch(() => setStatus('Gateway indisponivel'));
    const t = window.setInterval(() => { void ler().catch(() => setStatus('Gateway indisponivel')); }, 5_000);
    return () => { controller.abort(); window.clearInterval(t); };
  }, [ler]);

  // Os limites mudam no painel; o estado so e sobrescrito enquanto o operador
  // nao digitou nada, para o polling nao apagar o que esta sendo editado.
  useEffect(() => {
    const l = estado?.limites;
    if (!l) return;
    setLimites((atual) => {
      const seguinte = { ...atual };
      for (const campo of CAMPOS) {
        const v = l[campo.chave];
        if (typeof v === 'number' && !Number.isNaN(v)) seguinte[campo.chave] = v;
      }
      return seguinte;
    });
  }, [estado?.updated_at]);

  const enviar = async (caminho: string, corpo?: Record<string, unknown>, aviso?: string) => {
    if (ocupado) return;
    setOcupado(true);
    setStatus('Enviando...');
    try {
      const r = await fetch(`${API}${caminho}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(corpo ?? {}),
        signal: AbortSignal.timeout(10_000),
      });
      const d = (await r.json().catch(() => ({}))) as { ok?: boolean; error?: string; motivo?: string };
      if (r.ok && d.ok !== false) {
        setStatus(corpo ? 'Limites aplicados.' : 'Motor responds.');
        void notify(caminho.includes('start') ? 'Operacao automatica ligada' : 'Operacao automatica desligada', corpo ? 'Limites de risco atualizados.' : 'O motor parou de evaluar.');
        if (aviso) setStatus(aviso);
      } else {
        setStatus(d.error || d.motivo || `HTTP ${r.status}`);
        void notify('Recusado', d.error || d.motivo || `HTTP ${r.status}`);
      }
      await ler();
    } catch (e) {
      setStatus(`Gateway indisponivel: ${e instanceof Error ? e.message : 'erro'}`);
    } finally {
      setOcupado(false);
    }
  };

  const ativo = estado?.ativo ?? false;

  return (
    <section className="card compact-card auto-engine" aria-labelledby="auto-engine-title">
      <div className="section-head">
        <div>
          <h2 id="auto-engine-title">Operacao automatica</h2>
          <span className="muted">O motor avalia o modelo e envia ordens sozinho, dentro dos limites abaixo</span>
        </div>
        <div className="btn-row">
          <span className={`chip ${ativo ? 'ok' : 'warn'}`}>{ativo ? 'Operando' : 'Parado'}</span>
          <span className="chip">{estado?.simbolo ?? '--'} {estado?.timeframe ?? ''}</span>
          <span className="chip">ciclo {estado?.ciclo ?? 0}</span>
        </div>
      </div>

      <div className="auto-engine-grid">
        {CAMPOS.map((campo) => (
          <label key={campo.chave} className="field" title={campo.dica}>
            <span>{campo.rotulo}</span>
            <input
              type="number"
              step={campo.passo}
              value={String(limites[campo.chave])}
              onChange={(e) => setLimites((l) => ({ ...l, [campo.chave]: num(e.target.value) }))}
            />
          </label>
        ))}
      </div>

      <div className="btn-row" style={{ marginTop: 8 }}>
        <button className="btn sm ghost" type="button" onClick={() => void enviar('/api/auto/config', limites)} disabled={ocupado}>Aplicar limites</button>
        <button className="btn sm primary" type="button" onClick={() => void enviar('/api/auto/start')} disabled={ocupado || ativo}>Ligar</button>
        <button className="btn sm danger" type="button" onClick={() => void enviar('/api/auto/stop')} disabled={ocupado || !ativo}>Desligar</button>
        <button className="btn sm ghost" type="button" onClick={() => void enviar('/api/auto/tick')} disabled={ocupado}>Rodar um ciclo</button>
      </div>

      <div className="hint" role="status" aria-live="polite" style={{ marginTop: 6 }}>{status || `Threads: ${estado?.threads ?? '--'}`}</div>

      {(estado?.decisoes?.length ?? 0) > 0 && (
        <div className="table-scroll auto-engine-decisoes">
          <table className="tbl compact-table">
            <thead><tr><th>Quando</th><th>Ativo</th><th>Decisao</th><th className="num">Confianca</th><th>Motivo</th></tr></thead>
            <tbody>
              {(estado?.decisoes ?? []).slice(0, 8).map((d, i) => (
                <tr key={`${d.ts ?? i}`}>
                  <td className="mono">{d.ts ? new Date(d.ts).toLocaleTimeString('pt-BR') : '--'}</td>
                  <td><strong>{d.simbolo ?? '--'}</strong></td>
                  <td><span className={`chip ${/buy|compra/i.test(String(d.side)) ? 'ok' : /sell|venda/i.test(String(d.side)) ? 'warn' : ''}`}>{d.side ?? d.acao ?? '--'}</span></td>
                  <td className="num">{d.confianca ?? '--'}</td>
                  <td>{d.motivo ?? '--'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
