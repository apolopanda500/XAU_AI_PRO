import React, { useEffect, useRef, useState } from 'react';
import { apiBase } from '../lib/api';
import '../theme/latencia-bar.css';

type Medicao = {
  broker: string;
  ms: number | null;
  ok: boolean;
  motivo: string;
  server: string;
  melhor_em_ms: number | null;
};

/** 400 ms e o alvo: a barra satura aqui e quem decide e o operador. */
const ALVO_MS = 400;

/** Nivel de latencia. A FAIXA e um token no CSS, aqui e o dado. */
function nivel(m: Medicao): 'otima' | 'ok' | 'ruim' | 'off' {
  if (m.ms === null) return 'off';
  if (m.ms <= 150) return 'otima';
  if (m.ms <= 350) return 'ok';
  return 'ruim';
}

/**
 * Latencia ao vivo por corretora — canto inferior esquerdo, selecao com lista.
 *
 * POR QUE MEXC PARA CIMA
 * ---------------------
 * Na MEXC e no MT5 a latencia e um item de RODAPE, nao de cabecalho. No
 * cabecalho ela competia com o relogio e com o status do EA, e a 5 corretoras
 * medindo o cabecalho deixava de caber na largura util.
 *
 * No rodape, o operador le como le uma legenda: o item fica compacto e so abre
 * a lista quando ele pergunta. O que fica sempre visivel e a CORRETORA ATIVA e
 * o seu `ms` — sao os dois dados que ele usa sem clicar.
 *
 * REGRA QUE IMPORTA
 * -----------------
 * Sem resposta mostra "sem resposta" e NUNCA `0 ms`. Zero parece medida
 * perfeita e esconderia corretora fora do ar. O valor vem do backend, que
 * crono-metra de verdade (ver `backend/latencia.py`).
 */
export default function LatenciaBar({ ativa }: { ativa?: string }) {
  const [medicoes, setMedicoes] = useState<Medicao[]>([]);
  const [erro, setErro] = useState(false);
  const [aberto, setAberto] = useState(false);
  const caixa = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let vivo = true;
    const medir = () => {
      fetch(`${apiBase()}/api/latencia`, { signal: AbortSignal.timeout(6000) })
        .then((r) => r.json())
        .then((d: { corretoras?: Medicao[] }) => {
          if (!vivo) return;
          setMedicoes(Array.isArray(d.corretoras) ? d.corretoras : []);
          setErro(false);
        })
        .catch(() => {
          if (vivo) setErro(true);
        });
    };
    medir();
    // 15 s: rapido demais vira consumo, lento demais deixa de ajudar a decidir.
    const t = setInterval(medir, 15_000);
    return () => {
      vivo = false;
      clearInterval(t);
    };
  }, []);

  // Fecha ao clicar fora e no `Escape`. Sem isso a lista ficaria aberta por
  // cima da tela depois que o operador mudou de aba com o mouse.
  useEffect(() => {
    if (!aberto) return;
    const fora = (e: MouseEvent) => {
      if (caixa.current && !caixa.current.contains(e.target as Node)) setAberto(false);
    };
    const esc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setAberto(false);
    };
    document.addEventListener('mousedown', fora);
    document.addEventListener('keydown', esc);
    return () => {
      document.removeEventListener('mousedown', fora);
      document.removeEventListener('keydown', esc);
    };
  }, [aberto]);

  if (erro) {
    return (
      <div className="latencia-rodape">
        <span className="latencia-item latencia-off" title="Gateway sem resposta para medir latência">
          <span aria-hidden="true">📡</span> sem medição
        </span>
      </div>
    );
  }
  if (!medicoes.length) return null;

  // A corretora ativa vem primeiro: e a que o operador opera. Sem `ativa`, a
  // melhor medidamedida escolhe a ordem — que e a mesma logica do backend em
  // `melhor_em_ms`.
  const ordenada = [...medicoes].sort((a, b) => {
    if (a.broker === ativa) return -1;
    if (b.broker === ativa) return 1;
    return (a.ms ?? Infinity) - (b.ms ?? Infinity);
  });
  const principal = ordenada[0];
  const n = nivel(principal);

  return (
    <div className="latencia-rodape" ref={caixa}>
      <button
        type="button"
        className={`latencia-gatilho latencia-${n}`}
        onClick={() => setAberto((v) => !v)}
        aria-expanded={aberto}
        aria-haspopup="true"
        title={`Latência por corretora — ${principal.ms === null ? 'sem resposta' : `${Math.round(principal.ms)} ms`}`}
      >
        <span className="latencia-gatilho-ponto" aria-hidden="true" />
        <span className="latencia-gatilho-ms">
          {principal.ms === null ? '—' : `${Math.round(principal.ms)} ms`}
        </span>
        <span className="latencia-gatilho-seta" aria-hidden="true" />
        <span className="sr-only">Abrir latência por corretora</span>
      </button>

      {aberto && (
        <div className="latencia-lista" role="listbox" aria-label="Latência por corretora">
          {ordenada.map((m) => {
            const pct = m.ms === null ? 0 : Math.min(100, Math.round((m.ms / ALVO_MS) * 100));
            return (
              <div
                key={m.broker}
                role="option"
                aria-selected={m.broker === ativa}
                className={`latencia-item latencia-${nivel(m)}${m.broker === ativa ? ' latencia-ativa' : ''}`}
                title={`${m.server || m.broker} — ${m.motivo}${
                  m.melhor_em_ms ? ` · ${m.melhor_em_ms} ms acima da melhor` : ''
                }`}
              >
                <span className="latencia-nome">{m.broker}</span>
                <span className="latencia-medidor" aria-hidden="true">
                  <i style={{ width: `${pct}%` }} />
                </span>
                <span className="latencia-ms">
                  {m.ms === null ? 'sem resposta' : `${Math.round(m.ms)} ms`}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
