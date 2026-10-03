/**
 * Copiloto do XAU AI PRO — painel de conversa dentro da aba de IA.
 *
 * Nao substitui o painel de inferencia: os dois convivem. O painel de
 * inferencia e a LEITURA (probabilidade real do modelo, edge por fold,
 * inventario de modelos). O copiloto e a PERGUNTA (sobre o codigo do EA,
 * os controles de risco, o fluxo). Sao leituras diferentes do mesmo assunto.
 *
 * O que o copiloto promete e o que ele recusa estao na resposta dele; esta UI
 * nao faz propaganda. Quando o backend devolve `available: false` ou um
 * motivo, isso aparece — nao escondemos falha de backend com texto generico.
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { apiBase } from '../lib/api';
// As duas folhas do copiloto ficavam sem importar: `copilot.css` so era
// puxado pelo AIControlTab (que a interface nunca monta) e
// `theme/copilot-table.css` nao tinha import em nenhum lugar. Sem elas a
// tabela de achados caia sem largura, sem sticky e com numeros sobre os
// textos. A ordem importa: a folha da tabela sobrescreve o respiro do painel.
import './copilot.css';
import '../theme/copilot-table.css';

const API = `${apiBase()}`;

interface Mensagem {
  id: string;
  de: 'user' | 'copilot';
  texto: string;
  intent?: string;
}

interface Contexto {
  ok: boolean;
  achados_total: number;
  controles: { total: number; ativos: number; parciais: number; inoperantes: number; stubs: number };
  intents: string[];
  escreve_codigo: boolean;
  previsao_mercado: boolean;
  nota: string;
  mapa?: {
    total_arquivos?: number;
    total_linhas?: number;
    arquivo_principal?: { linhas?: number };
  };
}

interface Achado {
  id: number;
  gravidade: string;
  arquivo: string;
  linha: string;
  titulo: string;
  por_que_importa: string;
}

const SUGESTOES = [
  'Qual o pior problema do meu EA',
  'Me mostra os controles de risco',
  'O que acontece sem sinal de IA',
  'Como funciona o OnTick',
  'O que o EA grava nos dados',
  'Quem é você',
];

/**
 * Markdown mínimo. O copiloto devolve **, `código` e listas.
 * Evitar uma dependencia de markdown completa por causa disso.
 */
function renderizar(texto: string) {
  const blocos = texto.split("\n");
  return blocos.map((linha, i) => {
    if (linha.trim() === '' ) return <div key={i} style={{ height: 8 }} />;
    if (linha.startsWith('### ')) {
      return <h4 key={i} className="copilot-h4">{linha.slice(4)}</h4>;
    }
    if (linha.startsWith('## ')) {
      return <h3 key={i} className="copilot-h3">{linha.slice(3)}</h3>;
    }
    if (linha.startsWith('# ')) {
      return <h3 key={i} className="copilot-h3">{linha.slice(2)}</h3>;
    }
    if (linha.startsWith('- ') || linha.startsWith('* ')) {
      return (
        <div key={i} className="copilot-li">
          <span className="copilot-bullet">•</span>
          <span>{inline(linha.replace(/^[-*]\s*/, ''))}</span>
        </div>
      );
    }
    if (/^\d+\.\s/.test(linha)) {
      const m = linha.match(/^(\d+)\.\s(.*)$/);
      return (
        <div key={i} className="copilot-li">
          <span className="copilot-num">{m?.[1]}.</span>
          <span>{inline(m?.[2] ?? linha)}</span>
        </div>
      );
    }
    if (linha.startsWith('---')) {
      return <hr key={i} className="copilot-hr" />;
    }
    return <p key={i} className="copilot-p">{inline(linha)}</p>;
  });
}

/** **negrito** e `código` dentro da linha. */
function inline(texto: string) {
  const partes = texto.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).filter(Boolean);
  return partes.map((p, i) => {
    if (p.startsWith('**') && p.endsWith('**')) {
      return <strong key={i}>{p.slice(2, -2)}</strong>;
    }
    if (p.startsWith('`') && p.endsWith('`')) {
      return <code key={i} className="copilot-code">{p.slice(1, -1)}</code>;
    }
    return <span key={i}>{p}</span>;
  });
}

export default function CopilotPanel() {
  const [mensagens, setMensagens] = useState<Mensagem[]>([]);
  const [pergunta, setPergunta] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [contexto, setContexto] = useState<Contexto | null>(null);
  const [erroCtx, setErroCtx] = useState('');
  const [aba, setAba] = useState<'conversa' | 'achados'>('conversa');
  const [achados, setAchados] = useState<Achado[]>([]);
  const [filtro, setFiltro] = useState<string>('');
  const fimRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    void (async () => {
      try {
        const r = await fetch(`${API}/api/copilot/contexto`, { signal: ctrl.signal });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        setContexto((await r.json()) as Contexto);
      } catch (e) {
        if (!ctrl.signal.aborted) {
          setErroCtx(e instanceof Error ? e.message : 'contexto indisponível');
        }
      }
    })();
    return () => ctrl.abort();
  }, []);

  useEffect(() => {
    if (aba !== 'achados') return;
    const ctrl = new AbortController();
    void (async () => {
      try {
        const q = filtro ? `?gravidade=${encodeURIComponent(filtro)}` : '';
        const r = await fetch(`${API}/api/ea/achados${q}`, { signal: ctrl.signal });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const d = (await r.json()) as { achados: Achado[] };
        setAchados(d.achados);
      } catch {
        if (!ctrl.signal.aborted) setAchados([]);
      }
    })();
    return () => ctrl.abort();
  }, [aba, filtro]);

  useEffect(() => {
    fimRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [mensagens, enviando]);

  const enviar = useCallback(async (texto: string) => {
    const limpa = texto.trim();
    if (!limpa || enviando) return;
    setPergunta('');
    setEnviando(true);
    setMensagens((m) => [
      ...m,
      { id: `u${Date.now()}`, de: 'user', texto: limpa },
    ]);
    try {
      const r = await fetch(`${API}/api/copilot/perguntar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pergunta: limpa }),
        signal: AbortSignal.timeout(30000),
      });
      const d = (await r.json()) as {
        ok?: boolean;
        resposta?: string;
        intent?: string;
        error?: string;
      };
      setMensagens((m) => [
        ...m,
        {
          id: `c${Date.now()}`,
          de: 'copilot',
          // A mensagem de erro do backend aparece como esta. Nao substituimos
          // falha por texto generico para o usuario nao achar que respondeu.
          texto: d.resposta ?? d.error ?? 'Sem resposta do copiloto.',
          intent: d.intent,
        },
      ]);
    } catch (e) {
      setMensagens((m) => [
        ...m,
        {
          id: `c${Date.now()}`,
          de: 'copilot',
          texto: `Copiloto inacessível: ${e instanceof Error ? e.message : 'erro'}. O gateway precisa estar rodando.`,
        },
      ]);
    } finally {
      setEnviando(false);
    }
  }, [enviando]);

  return (
    <div className="copilot-panel">
      <div className="copilot-head">
        <div className="copilot-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={aba === 'conversa'}
            className={`copilot-tab ${aba === 'conversa' ? 'on' : ''}`}
            onClick={() => setAba('conversa')}
          >
            Conversa
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={aba === 'achados'}
            className={`copilot-tab ${aba === 'achados' ? 'on' : ''}`}
            onClick={() => setAba('achados')}
          >
            Achados{contexto ? ` (${contexto.achados_total})` : ''}
          </button>
        </div>
        {contexto && (
          <span className="muted">
            {contexto.mapa?.total_arquivos ?? '—'} arquivos ·{' '}
            {(contexto.mapa?.total_linhas ?? 0).toLocaleString('pt-BR')} linhas ·{' '}
            {contexto.controles.inoperantes} controles inoperantes
          </span>
        )}
      </div>

      {erroCtx && (
        <div className="placeholder">
          Mapa do EA indisponível: {erroCtx}
        </div>
      )}

      {aba === 'conversa' && (
        <>
          <div className="copilot-chat" role="log" aria-live="polite">
            {mensagens.length === 0 && (
              <div className="copilot-vazio">
                <p>
                  Pergunte sobre o <strong>código do seu EA</strong>. As respostas
                  citam arquivo e linha, e ele diz quando não sabe.
                </p>
                {contexto && (
                  <ul className="copilot-fatos">
                    <li>{contexto.achados_total} achados verificados no código</li>
                    <li>
                      {contexto.controles.ativos} controles de risco ativos,{' '}
                      {contexto.controles.inoperantes} inoperantes,{' '}
                      {contexto.controles.stubs} stub
                    </li>
                    <li>
                      Não escreve MQL5{' '}
                      <span className="chip warn">leitura apenas</span>
                    </li>
                    <li>
                      Não prevê preço{' '}
                      <span className="chip warn">edge real é +0,11</span>
                    </li>
                  </ul>
                )}
                <div className="copilot-sugestoes">
                  {SUGESTOES.map((s) => (
                    <button
                      key={s}
                      type="button"
                      className="btn xs ghost"
                      onClick={() => void enviar(s)}
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {mensagens.map((m) => (
              <div
                key={m.id}
                className={`copilot-msg ${m.de === 'user' ? 'from-user' : 'from-bot'}`}
              >
                {m.de === 'copilot' && m.intent && (
                  <span className="copilot-intent">{m.intent}</span>
                )}
                <div className="copilot-bubble">{renderizar(m.texto)}</div>
              </div>
            ))}
            {enviando && (
              <div className="copilot-msg from-bot">
                <div className="copilot-bubble muted">Lendo o código…</div>
              </div>
            )}
            <div ref={fimRef} />
          </div>

          <div className="copilot-input">
            <textarea
              value={pergunta}
              onChange={(e) => setPergunta(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  void enviar(pergunta);
                }
              }}
              placeholder="Pergunte sobre o EA, o risco ou o código. Enter envia."
              rows={2}
              maxLength={2000}
              aria-label="Pergunta ao copiloto"
            />
            <button
              type="button"
              className="btn primary"
              onClick={() => void enviar(pergunta)}
              disabled={enviando || !pergunta.trim()}
            >
              {enviando ? 'Enviando…' : 'Enviar'}
            </button>
          </div>

          {contexto && (
            <p className="hint">
              {contexto.nota}
            </p>
          )}
        </>
      )}

      {aba === 'achados' && (
        <div className="copilot-achados">
          <div className="copilot-filtros">
            {['CRITICO', 'ALTO', 'MEDIO', 'BAIXO', ''].map((g) => (
              <button
                key={g || 'todos'}
                type="button"
                className={`btn xs ${filtro === g ? 'primary' : 'ghost'}`}
                onClick={() => setFiltro(g)}
              >
                {g || 'Todos'}
              </button>
            ))}
          </div>
          {/* Os 42 achados eram um cartao empilhado por item, com titulo,
              arquivo:linha e paragrafo. Tres linhas por achado = 126 linhas
              de rolagem para ler uma lista. Virou tabela: uma linha por
              achado, com gravidade, arquivo:linha e o "por que importa"
              condensado. */}
          <div className="table-scroll copilot-achados-scroll">
            <table className="tbl compact-table copilot-achados-table">
              <caption className="sr-only">Achados da auditoria do EA</caption>
              <thead>
                <tr>
                  <th className="num">#</th>
                  <th>Gravidade</th>
                  <th>Achado</th>
                  <th>Arquivo</th>
                  <th>Por que importa</th>
                </tr>
              </thead>
              <tbody>
                {achados.map((a) => (
                  <tr key={a.id} className={`g-${a.gravidade.toLowerCase()}`}>
                    <td className="num">{a.id}</td>
                    <td>
                      <span className={`chip ${a.gravidade === 'CRITICO' ? 'danger' : a.gravidade === 'ALTO' ? 'warn' : 'neutral'}`}>
                        {a.gravidade}
                      </span>
                    </td>
                    <td><strong>{a.titulo}</strong></td>
                    <td className="mono muted">{a.arquivo}:{a.linha}</td>
                    <td className="muted">{a.por_que_importa}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {achados.length === 0 && <div className="placeholder">Nenhum achado neste filtro.</div>}
          </div>
        </div>
      )}
    </div>
  );
}
