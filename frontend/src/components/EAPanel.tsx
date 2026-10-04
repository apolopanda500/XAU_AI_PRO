// Painel do Expert Advisor.
//
// O QUE ESTE PAINEL MOSTRA
// ========================
// Duas verdades separadas, que a tela anterior misturava:
//
//   1. O que existe em disco no terminal MT5 (inventario: nome, hash, se tem
//      codigo-fonte). Isto e leitura de pasta, nao execucao.
//   2. O que o terminal esta reportando agora (heartbeat do EA, journal,
//      auto-trading). Isto e o sinal que destrava comando.
//
// Um EA instalado nao e um EA rodando. O app nao anexa EA a grafico nem
// compila: anexar e fechar grafico no MetaTrader 5 e compilar e trabalho do
// MetaEditor. Aqui so se ve o estado e se manda comando pelo canal de
// arquivo (FILE_COMMON), que e o mesmo canal do heartbeat.
//
// POR QUE O BOTAO FICA DESLIGADO
// ==============================
// O gateway recusa qualquer comando de EA sem heartbeat vivo. Em vez de um
// botao morto sem explicacao, o painel diz o motivo devolvido pelo gateway
// ("EA sem heartbeat vivo", "arquivo nao atualizado", "estado nao RUNNING").
//
// EDICAO DO EA
// ============
// O `.mq5` e editavel no repositorio. Mudou o codigo, recompile no
// MetaEditor64 e reanexe ao grafico — o build do app nao compila MQL5.
import { useState, type ReactNode } from 'react';
import { apiBase } from '../lib/api';
import { notify } from '../lib/notify';
import { useEaRuntime, useEaStatusDetail, type EaDetailed } from '../hooks/queries';

type CmdResult = {
  ok?: boolean;
  error?: string;
  status?: string;
  command?: string;
  detail?: string;
  [key: string]: unknown;
};

const TIMEFRAMES = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1'];
const MODOS: Array<[string, string]> = [
  ['auto', 'Automático'],
  ['manual', 'Manual'],
];

const ESTADO_TOM: Record<string, 'ok' | 'warn' | 'neutral' | 'danger'> = {
  vivo: 'ok',
  visto_no_journal: 'warn',
  heartbeat_sem_identificar: 'neutral',
  sem_sinal: 'danger',
};

const ROTULO_ESTADO: Record<string, string> = {
  vivo: 'vivo',
  visto_no_journal: 'visto no journal',
  heartbeat_sem_identificar: 'heartbeat sem identificar',
  sem_sinal: 'sem sinal',
};

const CONTROLES: Array<{ id: string; rotulo: string; tom?: string }> = [
  { id: 'start', rotulo: 'Iniciar' },
  { id: 'pause', rotulo: 'Pausar' },
  { id: 'resume', rotulo: 'Retomar' },
  { id: 'stop', rotulo: 'Parar' },
  { id: 'close-all', rotulo: 'Fechar tudo', tom: 'danger' },
];

function Chip({ tom, children }: { tom: string; children: ReactNode }) {
  return <span className={`chip ${tom}`}>{children}</span>;
}

export default function EAPanel() {
  const runtime = useEaRuntime();
  const detalhe = useEaStatusDetail();

  const [simbolo, setSimbolo] = useState('');
  const [timeframe, setTimeframe] = useState('M15');
  const [modo, setModo] = useState('auto');
  const [ocupado, setOcupado] = useState<string | null>(null);
  const [resultado, setResultado] = useState<(CmdResult & { command?: string }) | null>(null);

  const ea = runtime.data;
  const hb = ea?.ea_heartbeat ?? {};
  const vivo = ea?.live === true;
  const motivo = String(hb.reason ?? '') || (vivo ? '' : 'heartbeat ausente');
  const linha = detalhe.data;
  const lista: EaDetailed[] = linha?.detalhado?.length
    ? linha.detalhado
    : ((linha?.experts ?? []) as EaDetailed[]);

  const enviar = async (command: string, extra: Record<string, unknown> = {}) => {
    if (ocupado) return;
    setOcupado(command);
    try {
      const r = await fetch(`${apiBase()}/api/ea/${command}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirm: true, ...extra }),
        signal: AbortSignal.timeout(12_000),
      });
      const d = (await r.json()) as CmdResult;
      setResultado({ ...d, command });
      void notify(
        d.ok === true ? 'Comando aceito' : 'Comando recusado',
        d.ok === true
          ? `${command} enviado ao EA pelo canal FILE_COMMON.`
          : String(d.error ?? d.detail ?? 'Veja o resultado no painel.'),
      );
      await runtime.refetch();
      await detalhe.refetch();
    } catch (erro) {
      const d: CmdResult = {
        ok: false,
        error: `Gateway indisponível: ${erro instanceof Error ? erro.message : 'erro'}`,
        command,
      };
      setResultado(d);
      void notify('Comando não enviado', String(d.error));
    } finally {
      setOcupado(null);
    }
  };

  const bloqueado = !vivo || ocupado !== null;

  return (
    <div className="card" style={{ marginTop: 14 }}>
      <div className="xau-head" style={{ marginTop: 0 }}>
        <div className="xau-title-row">
          <span className="xau-badge">EA</span>
          <div>
            <h2 style={{ margin: 0 }}>Expert Advisors</h2>
            <span className="muted">
              inventário do terminal · heartbeat do EA · comando pelo arquivo FILE_COMMON
            </span>
          </div>
        </div>
        <div className="btn-row" style={{ justifyContent: 'flex-end', flexWrap: 'wrap' }}>
          <Chip tom={ea?.terminal_connected ? 'ok' : 'danger'}>
            {ea?.terminal_connected ? 'terminal conectado' : 'terminal desconectado'}
          </Chip>
          <Chip tom={ea?.autotrading ? 'ok' : 'warn'}>
            auto-trading {ea?.autotrading ? 'ligado' : 'desligado'}
          </Chip>
          <Chip tom={vivo ? 'ok' : 'danger'}>
            {vivo ? `EA vivo · ${hb.age_sec ?? 0}s` : 'EA sem heartbeat'}
          </Chip>
        </div>
      </div>

      {!vivo && (
        <div className="xau-guard" role="status">
          <span>
            Comandos de EA desativados: {motivo}. O gateway só encaminha comando com heartbeat vivo
            — abra o gráfico no MetaTrader 5 com o EA anexado e<code> ExpertEnable</code> ligado.
          </span>
        </div>
      )}

      {/* ---------------------------------------------------------- comandos */}
      <div className="xau-section">Controle do EA</div>
      <div className="btn-row" style={{ marginTop: 8, flexWrap: 'wrap' }}>
        {CONTROLES.map((c) => (
          <button
            key={c.id}
            type="button"
            className={`btn ghost${c.tom === 'danger' ? ' danger' : ''}`}
            disabled={bloqueado}
            onClick={() => void enviar(c.id)}
            title={vivo ? `POST /api/ea/${c.id}` : motivo}
          >
            {ocupado === c.id ? 'Enviando…' : c.rotulo}
          </button>
        ))}
      </div>

      <div className="grid cols-3" style={{ marginTop: 12 }}>
        <div className="field">
          <label htmlFor="ea-simbolo">Símbolo</label>
          <input
            id="ea-simbolo"
            type="text"
            placeholder="XAUUSD"
            value={simbolo}
            onChange={(e) => setSimbolo(e.target.value.toUpperCase())}
          />
        </div>
        <div className="field">
          <label htmlFor="ea-timeframe">Timeframe</label>
          <select
            id="ea-timeframe"
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
          >
            {TIMEFRAMES.map((tf) => (
              <option key={tf} value={tf}>
                {tf}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="ea-modo">Modo</label>
          <select id="ea-modo" value={modo} onChange={(e) => setModo(e.target.value)}>
            {MODOS.map(([valor, rotulo]) => (
              <option key={valor} value={valor}>
                {rotulo}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="btn-row" style={{ marginTop: 10, flexWrap: 'wrap' }}>
        <button
          type="button"
          className="btn primary"
          disabled={bloqueado || !simbolo}
          onClick={() => void enviar('set-symbol', { symbol: simbolo, value: simbolo })}
        >
          Aplicar símbolo
        </button>
        <button
          type="button"
          className="btn"
          disabled={bloqueado}
          onClick={() => void enviar('set-timeframe', { value: timeframe })}
        >
          Aplicar timeframe
        </button>
        <button
          type="button"
          className="btn"
          disabled={bloqueado}
          onClick={() => void enviar('set-mode', { value: modo })}
        >
          Aplicar modo
        </button>
        <button
          type="button"
          className="btn"
          disabled={bloqueado}
          onClick={() => void enviar('set-autotrading', { value: ea?.autotrading ? '0' : '1' })}
        >
          {ea?.autotrading ? 'Desligar auto-trading' : 'Ligar auto-trading'}
        </button>
        <button
          type="button"
          className="btn ghost danger"
          disabled={bloqueado}
          onClick={() => void enviar('close', { symbol: simbolo })}
          title="Fecha a posição do símbolo informado"
        >
          Fechar símbolo
        </button>
      </div>

      {resultado && (
        <div className={`xau-result ${resultado.ok ? 'is-ok' : 'is-neg'}`} role="status">
          <span>
            {resultado.ok
              ? `${resultado.command} aceito · ${resultado.status ?? 'queued'}`
              : `${resultado.command} recusado · ${resultado.error ?? resultado.detail ?? 'sem detalhe'}`}
          </span>
        </div>
      )}

      {/* --------------------------------------------------------- inventário */}
      <div className="xau-section">Instalados no terminal</div>

      {detalhe.isFetching && !linha && (
        <div className="hint">Lendo a pasta de experts do terminal…</div>
      )}
      {linha?.error && (
        <div className="hint warn" role="alert">
          {String(linha.error)}
        </div>
      )}

      {!linha?.error && lista.length === 0 && !detalhe.isFetching && (
        <div className="placeholder" role="status">
          <p className="hint">Nenhum EA encontrado em {linha?.experts_dir ?? 'MQL5/Experts'}.</p>
        </div>
      )}

      {lista.length > 0 && (
        <>
          <div className="table-scroll">
            <table className="tbl compact-table dense-grid">
              <thead>
                <tr>
                  <th>EA</th>
                  <th>Arquivo</th>
                  <th>Estado</th>
                  <th className="num">Journal</th>
                  <th>Código-fonte</th>
                  <th className="num">Hash</th>
                  <th className="num">Modificado</th>
                </tr>
              </thead>
              <tbody>
                {lista.map((item) => {
                  const estado = String(item.estado ?? (item.executavel ? 'sem_sinal' : 'fonte'));
                  const tom = ESTADO_TOM[estado] ?? 'neutral';
                  const rotulo = ROTULO_ESTADO[estado] ?? estado;
                  return (
                    <tr key={item.arquivo ?? item.nome}>
                      <td>{item.nome ?? '—'}</td>
                      <td className="muted">{item.arquivo ?? '—'}</td>
                      <td>
                        <Chip tom={tom}>{rotulo}</Chip>
                      </td>
                      <td className="num">
                        {item.no_journal ? `${item.ocorrencias_journal ?? 0}×` : '—'}
                      </td>
                      <td>{item.tem_codigo_fonte ? '.mq5' : '—'}</td>
                      <td className="num muted">{item.hash_sha256_16 ?? '—'}</td>
                      <td className="num muted">
                        {item.modificado_em ? String(item.modificado_em).slice(0, 10) : '—'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="hint" style={{ marginTop: 6 }}>
            {linha?.count ?? lista.length} arquivo(s) · {linha?.executaveis ?? 0} executável(is) ·{' '}
            {linha?.apenas_fonte ?? 0} só código-fonte. {linha?.nota ?? ''}
          </div>
        </>
      )}

      <div className="hint" style={{ marginTop: 10 }}>
        O <code>.mq5</code> é editável no repositório. Mudou o código: recompile no MetaEditor64 (
        <code>C:\Program Files\MetaTrader 5\MetaEditor64.exe</code>) e reanexe ao gráfico — o build
        deste app não compila MQL5.
      </div>
    </div>
  );
}
