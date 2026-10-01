// Seletor de modelo do robo.
//
// POR QUE MOSTRAR A METRICA AO LADO DO NOME
// ==========================================
// Um seletor que so mostra "H1" nao diz nada. O mesmo timeframe pode ter um
// modelo reprovado no quality gate e outro aprovado, e trocar entre eles sem
// ver a metrica e trocar no escuro. Aqui cada opcao mostra a accuracy e o edge
// que vieram do arquivo do modelo — nunca um numero inventado na interface.
import { useEffect, useState } from 'react';
import { buscarModelosTreinados, type ModeloTreinado } from '../hooks/useAICommunication';
import ModelCover from './ModelCover';
import '../theme/robot-model.css';

function pct(value: number | null): string {
  return value === null || value === undefined || !Number.isFinite(value)
    ? '--'
    : `${(value * 100).toFixed(1)}%`;
}

export default function RobotModelSelector() {
  const [modelos, setModelos] = useState<ModeloTreinado[]>([]);
  const [modeloId, setModeloId] = useState('');
  const [erro, setErro] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    void buscarModelosTreinados(controller.signal).then(({ modelos: lista, erro: msg }) => {
      if (controller.signal.aborted) return;
      setModelos(lista);
      setErro(msg);
      // Preseleciona o primeiro modelo realmente carregavel. `publicable` nao
      // basta: o quality gate pode aprovar um timeframe cujo .pkl foi removido
      // na limpeza, e a inferencia falharia ao carregar.
      const primeiro = lista.find((m) => m.pklPresent) ?? null;
      if (primeiro) setModeloId(primeiro.id);
    });
    return () => controller.abort();
  }, []);

  const escolhida = modelos.find((m) => m.id === modeloId) ?? null;
  // Só entra na lista o que tem artefato em disco. Mostrar H4 como opcao
  // quando o .pkl nao existe faria o operador escolher e o robo falhar ao
  // carregar o modelo.
  const selecionavel = modelos.filter((m) => m.pklPresent);

  return (
    <section className="card compact-card robot-model-selector" aria-labelledby="robot-model-title">
      <div className="section-head">
        <div>
          <h2 id="robot-model-title">Modelo</h2>
          <span className="muted">Modelo que o robô avalia antes de operar</span>
        </div>
        <span className="chip">{selecionavel.length} disponíve{selecionavel.length === 1 ? 'l' : 'is'}</span>
      </div>
      {erro && <p className="hint" role="status">{erro}</p>}
      {/* POR QUE CANDOS DE CAPA E NAO UM <select>
          A lista tem 25 modelos carregaveis. Num select eles viram 25 linhas
          de texto com tres numeros, e comparar "qual tem edge maior" vira
          trabalho. A capa mostra simbolo, timeframe, accuracy e edge juntos,
          com cor pela classe do ativo — a escolha vira visual.
          O <select> continua existindo para o leitor de tela e para o
          teclado: as capas sao botoes com aria-pressed, e a metrica fica
          no aria-label. */}
      <div className="model-cover-grid" role="group" aria-label="Modelos disponiveis">
        {selecionavel.map((m) => (
          <ModelCover
            key={m.id}
            modelo={{
              id: m.id,
              symbol: m.symbol,
              timeframe: m.timeframe,
              accuracy: m.accuracy,
              edge: m.edge,
              f1: m.f1,
              publicable: m.publicable,
              pklPresent: m.pklPresent,
            }}
            selecionado={m.id === modeloId}
            onSelect={(id) => { setModeloId(id); }}
          />
        ))}
      </div>
      <div className="robot-model-row">
        <label className="field">
          <span>Selecionar (lista)</span>
          <select
            aria-label="Selecionar modelo do robo"
            value={modeloId}
            onChange={(event) => setModeloId(event.target.value)}
            disabled={!selecionavel.length}
          >
            {!selecionavel.length && <option value="">Nenhum modelo disponivel</option>}
            {selecionavel.map((m) => (
              <option key={m.id} value={m.id}>
                {m.symbol} {m.timeframe} · acc {pct(m.accuracy)} · edge {pct(m.edge)}
              </option>
            ))}
          </select>
        </label>
        {escolhida && (
          <dl className="robot-model-metrics">
            <div><dt>Acurácia</dt><dd className="num">{pct(escolhida.accuracy)}</dd></div>
            <div><dt>Edge</dt><dd className="num">{pct(escolhida.edge)}</dd></div>
            <div><dt>F1</dt><dd className="num">{pct(escolhida.f1)}</dd></div>
          </dl>
        )}
      </div>
      {!selecionavel.length && !erro && (
        <p className="hint">Nenhum modelo tem artefato carregavel. Treine em <code>Python/ai/train_v2.py</code>.</p>
      )}
    </section>
  );
}
