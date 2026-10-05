// ===========================================================================
//  ATIVO e MODELO/PERIODO — escolha do par que o motor opera.
//
//  POR QUE ISTO EXISTE SEPARADO DO GRAFICO
//  =========================================
//  O grafico (`AcompanharModelos`) le o par do MOTOR (`/api/auto/state`) e
//  mostra o que o motor esta usando. Sem um lugar para ESCOLHER, trocar de par
//  obrigava a sair da aba — e "qual ativo e modelo?" e a primeira pergunta de
//  quem opera.
//
//  POR QUE NAO TEM PREVISAO
//  ========================
//  Este painel antes mostrava sinal, confianca e probabilidades, com um botao
//  "Prever". O dono mandou tirar: "nada de prever tabela de previsao — isso nao
//  ajuda em nada, o que importa e operar".
//
//  Alem do pedido, o numero ja aparecia em outro lugar: o grafico do meio
//  desenha o sinal do modelo como marcador no candle. Um painel que mostra o
//  mesmo dado duas vezes faz o operador desconfiar dos dois.
//
//  O QUE ESTE PAINEL FAZ E SO ESCOLHER
//  =====================================
//  Escolher o ATIVO escreve em `useAppStore.selectedSymbol`, o mesmo estado que
//  o grafico e o mercado leem. Escolher o MODELO/PERIODO nao chama o gateway: o
//  backend resolve o modelo por (symbol, timeframe), entao o periodo escolhido
//  e o que vai para o motor quando ele roda.
//
//  Edge e acerto aparecem no rotulo porque o operador escolhe entre modelos com
//  numeros diferentes. Vem do TREINO (`.meta.json`), e medido: nao e previsao.
// ===========================================================================
import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';

const API = `${apiBase()}`;

type Modelo = {
  id: string;
  symbol: string;
  timeframe: string;
  accuracy: number | null;
  edge: number | null;
  pkl_present: boolean;
  publicable: boolean;
};

function pct(v: number | null | undefined, casas = 1): string {
  return v === null || v === undefined || !Number.isFinite(v)
    ? '--'
    : `${(v * 100).toFixed(casas)}%`;
}

export default function SeletorModelo() {
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  const setSelectedSymbol = useAppStore((s) => s.setSelectedSymbol);
  const [modelos, setModelos] = useState<Modelo[]>([]);
  const [modeloId, setModeloId] = useState('');
  const [erroLista, setErroLista] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    void fetch(`${API}/api/ai/trained`, { signal: controller.signal })
      .then((r) => r.json())
      .then((d: { models?: Modelo[] }) => {
        if (controller.signal.aborted) return;
        // `pkl_present` e o filtro: um modelo listado sem artefato no disco
        // falha ao carregar, e o operador escolheria um par quebrado.
        const lista = (d.models ?? []).filter((m) => m.pkl_present);
        setModelos(lista);
        setErroLista('');
      })
      .catch(() => {
        if (!controller.signal.aborted) setErroLista('Nao foi possivel ler os modelos.');
      });
    return () => controller.abort();
  }, []);

  const simbolos = useMemo(() => {
    const unicos = [...new Set(modelos.map((m) => m.symbol))];
    unicos.sort((a, b) => a.localeCompare(b));
    return unicos;
  }, [modelos]);

  const simbolo = useMemo(() => {
    const atual = (selectedSymbol || '').toUpperCase();
    if (atual && (simbolos.length === 0 || simbolos.includes(atual))) return atual;
    return simbolos[0] ?? '';
  }, [selectedSymbol, simbolos]);

  const visiveis = useMemo(
    () => modelos.filter((m) => m.symbol === simbolo),
    [modelos, simbolo],
  );

  // Trocar de ativo nao pode deixar o modelo escolhido de um ativo que nao
  // existe mais na lista: o periodo viria de um modelo que nao e mais o
  // exibido, e o operador acharia que trocou o par quando so trocou o nome.
  useEffect(() => {
    if (!visiveis.length) return;
    if (!visiveis.some((m) => m.id === modeloId)) setModeloId(visiveis[0].id);
  }, [visiveis, modeloId]);

  const escolherAtivo = useCallback(
    (novo: string) => {
      setSelectedSymbol(novo.toUpperCase());
      setModeloId('');
    },
    [setSelectedSymbol],
  );

  const escolhido = useMemo(
    () => visiveis.find((m) => m.id === modeloId) ?? null,
    [visiveis, modeloId],
  );

  return (
    <section className="card robo-par" aria-labelledby="robo-par-title">
      <div className="section-head">
        <div>
          <h2 id="robo-par-title">Ativo e período</h2>
          <span className="muted">
            {escolhido
              ? `O motor opera ${escolhido.symbol} ${escolhido.timeframe}.`
              : 'Escolha o par que o motor vai operar.'}
          </span>
        </div>
      </div>

      {erroLista ? (
        <p className="hint" role="status">
          {erroLista}
        </p>
      ) : (
        <div className="robo-par-linha">
          <label className="field robo-par-ativo">
            <span>Ativo</span>
            <select
              aria-label="Ativo do robo"
              value={simbolo}
              disabled={!simbolos.length}
              onChange={(e) => escolherAtivo(e.target.value)}
            >
              {!simbolos.length && <option value={simbolo}>{simbolo || '—'}</option>}
              {simbolos.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>

<label className="field robo-par-modelo">
            <span>Modelo / período</span>
            <select
              aria-label="Modelo do robo"
              value={modeloId}
              disabled={!visiveis.length}
              onChange={(e) => setModeloId(e.target.value)}
            >
              {!visiveis.length && (
                <option value="">Nenhum modelo carregável para {simbolo}</option>
              )}
              {visiveis.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.timeframe} · edge {pct(m.edge)} · acerto {pct(m.accuracy)}
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
    </section>
  );
}
