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

/**
 * POR QUE A BARRA FICAVA VAZIA — e por que era invisível
 * ========================================================
 * MEDIDO no backend (`mt5_gateway.py`, `_autorizado`): **toda** rota GET exige
 * `Authorization: Bearer`, e a MESMA função aplica **rate limit por minuto**.
 *
 * O token é injetado por `installGatewayAuth` (`lib/tauri.ts:41`), que
 * intercepta `window.fetch` — por isso o resto do app responde e esta barra
 * também é chamada com token.
 *
 * Aí está o furo: quando a resposta é **429** (cota do minuto estourada), o
 * corpo vem `{ok: false, error: "rate limit excedido"}` **sem `corretoras`**. O
 * componente fazia:
 *
 *     setMedicoes(Array.isArray(d.corretoras) ? d.corretoras : [])
 *
 * e depois `if (!medicoes.length) return null` — a barra **sumia da tela**.
 *
 * Três falhas de leitura numa linha só: 401, 429 e "nenhuma corretora
 * configurada" produziam exatamente a mesma tela — um espaço vazio no rodapé.
 * O operador concluía "a latência não existe" e não tinha como saber que era
 * cota estourada.
 *
 * O conserto é distinguir os três e DIZER qual deles é.
 */
type EstadoBarra = 'medindo' | 'ok' | 'sem-corretora' | 'token' | 'cota' | 'indisponivel';

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
  const [estado, setEstado] = useState<EstadoBarra>('medindo');
  const [aberto, setAberto] = useState(false);
  const caixa = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let vivo = true;
    const medir = () => {
      fetch(`${apiBase()}/api/latencia`, { signal: AbortSignal.timeout(6000) })
        .then((r) => {
          /*
            O STATUS ANTES DO CORPO. `r.json()` em resposta de erro devolve o
            `{ok:false}` e esconde o que aconteceu; ler o status primeiro é o
            que separa 401 de 429 de 200 com lista vazia.
          */
          const status = r.status;
          return r.json().then(
            (d: { corretoras?: Medicao[] }) => ({ status, d }),
            () => ({ status, d: {} as { corretoras?: Medicao[] } }),
          );
        })
        .then(({ status, d }) => {
          if (!vivo) return;
          if (status === 401) {
            setEstado('token');
            setErro(false);
            return;
          }
          if (status === 429) {
            // Cota do minuto, nao corretora fora do ar. A mensagem tem que dizer
            // isso: "sem medição" levaria o operador a culpar a rede.
            setEstado('cota');
            setErro(false);
            return;
          }
          if (!Array.isArray(d.corretoras)) {
            setEstado('indisponivel');
            setErro(true);
            return;
          }
          if (!d.corretoras.length) {
            setEstado('sem-corretora');
            setErro(false);
            return;
          }
          setMedicoes(d.corretoras);
          setEstado('ok');
          setErro(false);
        })
        .catch(() => {
          if (vivo) {
            setEstado('indisponivel');
            setErro(true);
          }
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
  if (!medicoes.length) {
    /*
      A BARRA NUNCA DESAPARECE, E DIZ POR QUE.

      Antes: `return null` quando não havia medição. Ausência renderizada como
      NADA é indistinguível de ausência real — e foi assim que 401, 429 e
      "nenhuma corretora" viraram o mesmo espaço vazio no rodapé.

      Agora cada estado tem a sua frase. "Sem medição" sem causa é um relatório
      inútil; "cota do minuto" diz o que fazer.
    */
    const FRASES: Record<EstadoBarra, { texto: string; titulo: string }> = {
      medindo: { texto: 'medindo…', titulo: 'Primeira medição de latência em andamento' },
      'sem-corretora': {
        texto: 'sem corretora',
        titulo: 'Nenhuma corretora configurada ainda',
      },
      token: {
        texto: 'sem token',
        titulo: 'O gateway recusou a leitura (401). A sessão do app não foi reconhecida.',
      },
      cota: {
        texto: 'cota do minuto',
        titulo:
          'O gateway devolveu 429: cota de leitura do minuto estourada. Não é corretora fora do ar.',
      },
      indisponivel: {
        texto: 'gateway fora',
        titulo: 'O gateway não respondeu para medir latência',
      },
      ok: { texto: 'sem medição', titulo: 'Sem medição disponível' },
    };
    const f = FRASES[estado];
    return (
      <div className="latencia-rodape">
        <span className="latencia-item latencia-off" title={f.titulo}>
          <span aria-hidden="true">◷</span> {f.texto}
        </span>
      </div>
    );
  }

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
    <div className="latencia-rodape" ref={caixa} data-aberto={aberto}>
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
                {/*
                    `transform: scaleX` em vez de `width`.
                    `width` e propriedade de layout: anima-la reflowa a linha a
                    cada quadro. `transform` move um pixel e o compositor cuida.
                    O desenho e identico; a diferenca aparece em maquina fraca.
                  */}
                <span className="latencia-medidor" aria-hidden="true">
                  <i style={{ transform: `scaleX(${Math.max(0.01, pct / 100)})` }} />
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
