// Risco do robô, em uma tabela só.
//
// O QUE MUDOU
// ===========
// Antes eram tres blocos empilhados: 4 cartões do gateway, 2 cartões de
// "resumo da conta" e 2 de "Performance". Drawdown aparecia em dois lugares
// com nomes diferentes, e PnL aparecia aqui e no Histórico — o mesmo número
// em duas abas, divergindo na первый глаз.
//
// Agora é uma tabela: limite, medido, estado. Uma linha por regra, na mesma
// ordem em que o risk_gate avalia. Os valores vêm do risk_gate (mesma fonte
// que bloqueia a ordem), nunca de um cálculo paralelo aqui.
//
// O PnL saiu: pertence ao Histórico. E o "resumo da conta" saiu porque
// Patrimônio já mostra saldo, margem e posições.
import { useState } from 'react';
import { useRealRisk } from '../../hooks/useRealRisk';
import '../../theme/risk-table.css';

type Linha = {
  regra: string;
  medido: string;
  limite: string;
  pct: number;
  critico: number;
  severidade: 'ok' | 'warn' | 'danger';
};

const num = (v: number | null | undefined, casas = 2) =>
  v === null || v === undefined || !Number.isFinite(v) ? '--' : v.toFixed(casas);

export default function RiskTab() {
  const real = useRealRisk();
  const [mostrarAjuste, setMostrarAjuste] = useState(false);
  const e = real.estado;

  const nivel = (valor: number, critico: number, alto: number): Linha['severidade'] =>
    !Number.isFinite(valor) ? 'ok' : valor >= critico ? 'danger' : valor >= alto ? 'warn' : 'ok';

  const perda = e?.daily_loss_pct ?? null;
  const exposicao = e?.exposure_pct ?? null;
  const drawdown = e?.drawdown_pct ?? null;
  const posicoes = e?.open_positions ?? null;
  const operacoes = e?.daily_trades ?? null;

  const linhas: Linha[] = [
    { regra: 'Perda diaria', medido: `${num(perda)}%`, limite: '2,0%', pct: perda ?? 0, critico: 2, severidade: nivel(perda ?? 0, 2, 1) },
    { regra: 'Exposicao', medido: `${num(exposicao)}%`, limite: '5,0%', pct: exposicao ?? 0, critico: 5, severidade: nivel(exposicao ?? 0, 5, 2.5) },
    { regra: 'Drawdown', medido: `${num(drawdown)}%`, limite: '15,0%', pct: drawdown ?? 0, critico: 15, severidade: nivel(drawdown ?? 0, 15, 8) },
    { regra: 'Posicoes abertas', medido: num(posicoes, 0), limite: '5', pct: (posicoes ?? 0) / 5 * 100, critico: 100, severidade: nivel((posicoes ?? 0) / 5 * 100, 100, 80) },
    { regra: 'Operacoes no dia', medido: num(operacoes, 0), limite: '20', pct: (operacoes ?? 0) / 20 * 100, critico: 100, severidade: nivel((operacoes ?? 0) / 20 * 100, 100, 80) },
  ];

  const killAtivo = real.kill.status === 'ativo';
  const executar = (acao: 'stop' | 'resume') => {
    const pergunta = acao === 'stop'
      ? 'Parar a execucao agora?\n\nO gateway recusara novas ordens ate a retomada.'
      : 'Retomar a execucao?\n\nO gateway exige XAU_ENABLE_EMERGENCY_RESUME=1.';
    if (window.confirm(pergunta)) void (acao === 'stop' ? real.parar() : real.retomar());
  };

  return (
    <section className="card compact-card risk-table-card" aria-labelledby="risk-title">
      <div className="section-head">
        <h2 id="risk-title">Risco</h2>
        <div className="btn-row">
          {killAtivo
            ? <button className="btn xs danger" onClick={() => executar('resume')} disabled={real.kill.busy}>Retomar execucao</button>
            : <button className="btn xs warning" onClick={() => executar('stop')} disabled={real.kill.busy}>Parar execucao</button>}
          <button className="btn xs ghost" onClick={() => void real.refresh()} disabled={real.carregando}>Atualizar</button>
        </div>
      </div>

      {killAtivo && (
        <p className="risk-stopped" role="status">Execucao parada. O gateway recusa novas ordens ate a retomada.</p>
      )}
      {real.erro && <p className="risk-stopped" role="status">Gateway nao devolveu o estado: {real.erro}</p>}
      {real.kill.erro && <p className="risk-stopped" role="status">{real.kill.erro}</p>}

      <div className="table-scroll">
        <table className="tbl compact-table risk-grid">
          <caption className="sr-only">Limites de risco e leitura atual do gateway</caption>
          <thead>
            <tr>
              <th>Regra</th>
              <th className="num">Medido</th>
              <th className="num">Limite</th>
              <th className="risk-th-bar">Uso</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            {linhas.map((l) => (
              <tr key={l.regra}>
                <td>{l.regra}</td>
                <td className="num">{l.medido}</td>
                <td className="num muted">{l.limite}</td>
                <td className="risk-bar-cell">
                  <span className="risk-bar">
                    <span
                      className={`risk-bar-fill ${l.severidade}`}
                      style={{ width: `${Math.min(100, Math.max(0, l.pct))}%` }}
                    />
                  </span>
                </td>
                <td><span className={`chip ${l.severidade}`}>{l.severidade === 'danger' ? 'critico' : l.severidade === 'warn' ? 'atencao' : 'ok'}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="risk-foot">
        <span className="muted">Mesma fonte que o risk_gate usa para liberar ou recusar a ordem.</span>
        <button className="btn xs ghost" type="button" onClick={() => setMostrarAjuste((v) => !v)}>
          {mostrarAjuste ? 'Ocultar' : 'Ajustar pelo app'}
        </button>
      </div>

      {mostrarAjuste && (
        <p className="muted risk-note">
          Estes campos sao apenas uma leitura local e nao alteram o risk_gate. Para mudar os
          limites que valem de verdade, use os campos de <strong>Operacao automatica</strong> acima,
          que vao para o gateway.
        </p>
      )}
    </section>
  );
}
