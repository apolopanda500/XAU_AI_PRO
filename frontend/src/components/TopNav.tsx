import React, { useEffect, useState } from 'react';
import { useAppStore } from '../hooks/useAppStore';
import QuantumClock from './QuantumClock';
import { apiBase } from '../lib/api';
import '../theme/latencia-bar.css';

// A navegacao vive em Sidebar.tsx (ITEMS). Este arquivo usava declarar um
// TABS proprio com 4 entradas que nunca eram renderizadas — uma terceira lista
// de abas que divergia da Sidebar conforme as abas eram adicionadas.

type Medicao = {
  broker: string;
  ms: number | null;
  ok: boolean;
  motivo: string;
  server: string;
  melhor_em_ms: number | null;
};

/**
 * Medidor de sinal e servidores com ms, no estilo do rodape do MT5.
 *
 * POR QUE EXISTE
 * --------------
 * O MT5 mostra no rodape o sinal e o servidor com o tempo de resposta. O
 * operador usa isso para uma decisao concreta: quando a latencia sobe, ele
 * sabe que o preco mostrado pode estar velho, e que trocar de servidor ajuda.
 * Sem esse numero, ele so descobre a lentidao quando a ordem sai ruim.
 *
 * A diferenca de MEXC para Binance nesta maquina foi de 405 ms — o suficiente
 * para o operador escolher conscientemente.
 *
 * REGRA QUE IMPORTA
 * -----------------
 * Sem resposta mostra "sem resposta" e NUNCA 0 ms. `0 ms` e mentira: parece
 * medida perfeita e esconde corretora fora do ar. O valor vem do backend,
 * que crono-metra de verdade (ver `backend/latencia.py`).
 */
function MedidorLatencia() {
  const [medicoes, setMedicoes] = useState<Medicao[]>([]);
  const [erro, setErro] = useState(false);

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
    // 15 s: rapido demais vira consumo, lento demais deixa de ajudar a
    // decidir. O MT5 tambem nao fica em sub-segundo.
    const t = setInterval(medir, 15_000);
    return () => {
      vivo = false;
      clearInterval(t);
    };
  }, []);

  if (erro) {
    return (
      <span className="latencia-item latencia-off" title="Gateway sem resposta para medir latência">
        <span aria-hidden="true">📡</span> sem medição
      </span>
    );
  }
  if (!medicoes.length) return null;

  return (
    <div className="latencia-bar" role="status" aria-label="Latência ao vivo por corretora">
      {medicoes.map((m) => {
        // A barra e proporcional a uma latencia de 400 ms. Acima disso ela
        // satura: o operador precisa do numero, nao de uma barra cheia.
        const pct = m.ms === null ? 0 : Math.min(100, Math.round((m.ms / 400) * 100));
        const nivel = m.ms === null ? 'off' : m.ms <= 150 ? 'otima' : m.ms <= 350 ? 'ok' : 'ruim';
        return (
          <span
            key={m.broker}
            className={`latencia-item latencia-${nivel}`}
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
          </span>
        );
      })}
    </div>
  );
}

export default function TopNav() {
  const wsConnected = useAppStore((s) => s.wsConnected);
  const aiStatus = useAppStore((s) => s.aiStatus);
  const robotStatus = useAppStore((s) => s.robotStatus);

  return (
    <header className="topbar">
      <div className="topnav-status">
        <span className="status">
          <i className={`dot ${wsConnected ? 'on' : ''}`} /> WS {wsConnected ? 'Online' : 'Offline'}
        </span>
        <span className="status">🤖 AI: {aiStatus}</span>
        <span className="status">EA: {robotStatus}</span>
        <MedidorLatencia />
        <QuantumClock compact showSeconds={false} showDate={false} />
      </div>
    </header>
  );
}
