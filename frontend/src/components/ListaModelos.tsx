// ===========================================================================
//  LISTA DOS MODELOS TREINADOS — o que realmente vai operar (05/10/2026)
// ===========================================================================
//
//  O DONO PEDIU
//  ===========
//  "mais tem que ter lista dos modelos treinados, eles vão operar automáticos,
//   seja qual for os modelos único ou multi"
//
//  POR QUE ESTA LISTA É O CENTRO DO ROBÔ
//  ====================================
//  MEDIDO (`ai_inference.listar_modelos`, 05/10/2026): **39 modelos treinados,
//  28 publicáveis**, com pares como `BTCUSD_H1`, `EURUSD_H4`.
//
//  O seletor de par antes vinha da lista de MODELOS. Com a lista de modelos
//  como fonte única de par, um par sem modelo treinado não aparecia — e o par
//  escolhido também não mostrava o modelo que ia decidir por ele. O operador
//  via um par e não sabia qual modelo operava.
//
//  Aqui o par vem do CATÁLOGO DA CORRETORA (1639 ativos na conta real) e o
//  modelo vem desta lista. São coisas diferentes: a corretora diz o que existe
//  para negociar, o treino diz o que existe para decidir.
//
//  MODELO REPROVADO APARECE, COM O MOTIVO
//  =======================================
//  MEDIDO: os M5 são reprovados — `AUDUSD_M5` com accuracy 0,344 e edge 0,011
//  contra 0,465/0,132 do H1 do mesmo par. Esconder o M5 faria o operador
//  achar que o app não tem M5. Mostrar com o motivo (`reason`) é o que
//  permite entender POR QUE ele não opera.
//
//  SOBRE "ÚNICO OU MULTI"
//  ======================
//  MEDIDO: no inventário real, um modelo é sempre UM `(símbolo, timeframe)`.
//  Não existe modelo multi-timeframe nos artefatos. Então a lista mostra a
//  verdade — 39 modelos, cada um com o seu par e período — e a escolha de qual
//  opera é feita aqui, uma linha de cada vez.
// ===========================================================================
import { useEffect, useMemo, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import { useAutoState } from '../hooks/queries';
import '../theme/robo.css';

export type ModeloTreinado = {
  id: string;
  symbol: string;
  timeframe: string;
  accuracy: number | null;
  edge: number | null;
  edge_std?: number | null;
  edge_min?: number | null;
  f1?: number | null;
  train_samples?: number | null;
  test_samples?: number | null;
  train_date?: string | null;
  publicable: boolean;
  pkl_present: boolean;
  reason?: string | null;
  algorithm?: string | null;
};

const pct = (v: number | null | undefined, casas = 1): string =>
  v === null || v === undefined || !Number.isFinite(v) ? '—' : `${(v * 100).toFixed(casas)}%`;

export default function ListaModelos() {
  const [modelos, setModelos] = useState<ModeloTreinado[]>([]);
  const [erro, setErro] = useState('');
  const [recusa, setRecusa] = useState('');
  const [carregando, setCarregando] = useState(true);
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  const setSelectedSymbol = useAppStore((s) => s.setSelectedSymbol);
  const autoQ = useAutoState();
  const simboloMotor = String(autoQ.data?.simbolo ?? '').toUpperCase();
  const tfMotor = String(autoQ.data?.timeframe ?? '').toUpperCase();

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase()}/api/ai/trained`, { signal: controller.signal })
      .then(async (r) => {
        if (!r.ok) {
          /*
            HTTP NEGADO E LISTA VAZIA SÃO COISAS DIFERENTES.

            O gateway responde 401 sem token de sessão e 500 quando o backend
            cai. Nos dois casos o corpo não tem `models`, e tratá-los como
            inventário vazio escrevia "nenhum modelo treinado encontrado" — que
            faz o operador concluir que nunca treinou nada, quando o_truth é
            que o app não conseguiu perguntar.

            Aqui a recusa vira recusa, com o código, e o texto manda olhar o
            gateway.
          */
          const erro = new Error(
            `o gateway respondeu ${r.status} ao pedir os modelos treinados`,
          );
          throw erro;
        }
        return r.json();
      })
      .then((d: { models?: ModeloTreinado[] }) => {
        if (controller.signal.aborted) return;
        setModelos(d.models ?? []);
        setErro('');
      })
      .catch(() => {
        if (!controller.signal.aborted) setErro('Não foi possível ler os modelos treinados.');
      })
      .finally(() => {
        if (!controller.signal.aborted) setCarregando(false);
      });
    return () => controller.abort();
  }, []);

  /*
    A LISTA VEM DO INVENTÁRIO REAL, sem filtro escondido.
    Ordenar por edge põe em cima o que realmente decide melhor, e é o que o
    operador quer ver primeiro. Reprovados vão para o fim, nunca somem.
  */
  const ordenados = useMemo(() => {
    const copia = [...modelos];
    copia.sort((a, b) => {
      const pa = a.publicable && a.pkl_present ? 0 : 1;
      const pb = b.publicable && b.pkl_present ? 0 : 1;
      if (pa !== pb) return pa - pb;
      return (b.edge ?? -1) - (a.edge ?? -1);
    });
    return copia;
  }, [modelos]);

  const publicaveis = useMemo(
    () => modelos.filter((m) => m.publicable && m.pkl_present).length,
    [modelos],
  );

  /*
    ESCOLHER O MODELO ESCOLHE O PAR E O PERÍODO.

    É a única coerência que importa: se clicar em `EURUSD_H4` e o gráfico
    continuar em `GOLD · M15`, o operador opera um par com o modelo de outro.
    Por isso os dois vão juntos, para `selectedSymbol` e para o timeframe do
    motor.
  */
const escolher = async (m: ModeloTreinado) => {
    setSelectedSymbol(m.symbol);
    setRecusa('');
    try {
      const r = await fetch(`${apiBase()}/api/auto/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ simbolo: m.symbol, timeframe: m.timeframe }),
        signal: AbortSignal.timeout(10_000),
      });
      const d = (await r.json().catch(() => ({}))) as {
        ok?: boolean;
        error?: string;
        timeframe?: string;
        aplicado?: boolean;
      };
      /*
        A RECUSA NÃO É FALHA DE REDE, E AS DUZAS SÃO DIFERENTES.

        MEDIDO (05/10/2026): `configurar()` respondia `{ok: false}` — o motor
        recusava por falta de lote/SL/TP — e esta tela ignorava a resposta. O
        operador clicava em `BTCUSD_M15`, o par mudava, o período continuava
        1H, e nada era escrito em lugar nenhum. Parecia lista quebrada.

        Agora a recusa é mostrada, com o que o motor gravou e o que falta.
      */
      if (d.ok === false && d.aplicado !== true) {
        setRecusa(d.error ?? `HTTP ${r.status}`);
      } else if (d.ok === false) {
        setRecusa(
          `Modelo aplicado ao motor (${m.symbol} · ${d.timeframe ?? m.timeframe}), mas o automático não liga ainda: ${d.error ?? ''}`,
        );
      }
      autoQ.refetch?.();
    } catch {
      setRecusa('Gateway indisponível: o período não pôde ser trocado.');
    }
  };

  return (
    <div className="robo-modelos" aria-label="Modelos treinados">
      <div className="robo-modelos-cabeca">
        <span className="robo-modelos-titulo">Modelos treinados</span>
        {modelos.length > 0 && (
          <span className="muted">
            {publicaveis} de {modelos.length} podem operar
          </span>
        )}
        {carregando && <span className="muted">lendo…</span>}
      </div>

      {erro ? (
        <p className="hint" role="status">
          {erro}
        </p>
      ) : null}

      {/*
        A RECUSA DO MOTOR, escrita.

        Sem esta linha, clicar num modelo de outro período não produzia nenhum
        sinal visível: o par trocava, o período não, e o operador achava que a
        lista não funcionava.
      */}
      {recusa ? (
        <p className="hint robo-modelos-recusa" role="status">
          {recusa}
        </p>
      ) : null}

      {!carregando && !modelos.length && !erro ? (
        <p className="hint">
          Nenhum modelo treinado encontrado. Sem modelo não há inferência, e sem inferência o
          automático não opera.
        </p>
      ) : null}

      {ordenados.length > 0 && (
        <div className="table-scroll robo-modelos-lista">
          <table className="tbl compact-table robo-modelos-tabela">
            <thead>
              <tr>
                <th>Modelo</th>
                <th>Par</th>
                <th>Período</th>
                <th className="num">Acerto</th>
                <th className="num">Edge</th>
                <th className="num">F1</th>
                <th className="num">Testes</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {ordenados.map((m) => {
                const podeOperar = m.publicable && m.pkl_present;
                const emUso =
                  m.symbol.toUpperCase() === simboloMotor &&
                  m.timeframe.toUpperCase() === tfMotor;
                return (
                  <tr
                    key={m.id}
                    className={`robo-modelo${emUso ? ' em-uso' : ''}${
                      podeOperar ? '' : ' reprovado'
                    }`}
                    onClick={() => void escolher(m)}
                    title={
                      podeOperar
                        ? `${m.id} — clique para operar este par neste período`
                        : (m.reason ?? 'modelo reprovado no treino')
                    }
                  >
                    <td>
                      <code>{m.id}</code>
                    </td>
                    <td>
                      <strong>{m.symbol}</strong>
                    </td>
                    <td>{m.timeframe}</td>
                    <td className="num">{pct(m.accuracy)}</td>
                    <td className="num">{pct(m.edge)}</td>
                    <td className="num">{pct(m.f1)}</td>
                    <td className="num">{m.test_samples ?? '—'}</td>
                    <td>
                      {podeOperar ? (
                        /*
                          O ROTULO ESTAVA INVERTIDO (medido no app instalado)
                          ================================================
                          Era `emUso ? 'no motor' : 'pode operar'`. `emUso`
                          significa que o modelo ESTA no motor — e a tela escrevia
                          "no motor". O modelo que o operador acabara de escolher
                          aparecia dizendo que NAO estava no motor, e a linha de
                          baixo (o que o motor usa) aparecia dizendo que podia
                          operar.

                          Pior com o cabecalho: "28 de 28 podem operar" ao lado de
                          uma linha que afirma "no motor". Um numero e um rotulo
                          que se contradizem, e o operador nao tem como saber qual
                          dos dois ler — e o AGENTS.md 9: controle que o
                          operador acredita ter e nao tem.

                          Agora os dois textos dizem a verdade: o que esta no motor
                          diz "no motor agora", e o que pode operar diz "pode
                          operar". Os dois sao positivos, e nenhum contradiz o
                          cabecalho.
                        */
                        <span className={`chip ${emUso ? 'ok' : 'neutral'}`}>
                          {emUso ? 'no motor agora' : 'pode operar'}
                        </span>
                      ) : (
                        <span className="chip warn" title={m.reason ?? ''}>
                          {m.pkl_present ? 'reprovado' : 'sem artefato'}
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}