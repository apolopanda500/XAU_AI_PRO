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
import { apiBase, isMobileRuntime } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import { ehClasseDeModelo } from '../lib/parNaTela';
import { useAutoState } from '../hooks/queries';
import ModelCover from './ModelCover';
import '../theme/robo.css';

export type ModeloTreinado = {
  id: string;
  /**
   * O nome do modelo como o operador le: `MODELO MULTI_METALS 5M`.
   *
   * MEDIDO (09/10/2026): o `id` e o `symbol` mostravam o MESMO texto nos
   * artefatos de classe — o dono viu `MULTI_METALS | MULTI_METALS | METALS`
   * na captura, duas colunas dizendo a mesma coisa. O `label` vem do
   * `rotulo_modelo` do backend, que e descreve com o periodo.
   */
  label?: string;
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

/*
  A CLASSE NAO E UM ATIVO, E A COLUNA PAR PRECISA DIZER ISSO (11/10/2026)
  ========================================================================
  MEDIDO na captura do dono (12:26): a linha `MODELO MULTI_METALS 5M` mostrava
  `METALS` na coluna PAR. `METALS` e uma CLASSE de ativo (o `class` do meta),
  nao um simbolo que se pode operar — e a propria cabeca da tabela dizia
  "37 de 37 periodos podem operar". Duas afirmacoes que se contradizem no
  mesmo painel (AGENTS.md §5): o operador nao sabe se pode escolher `METALS`
  como par, e nao pode — ele nao existe no catalogo da corretora.

  O rotulo e "classe X" porque a coluna PAR e onde se le o ativo. Um `METALS`
  cru parece um ativo; "classe METALS" e a verdade, e e o que separa "isto e
  uma classe" de "isto e um ativo que voce vai operar".
*/
export function rotuloClasseMulti(id: string): string {
  return `classe ${id.slice('MULTI_'.length)}`;
}

/**
 * A data do treino, legivel. O gateway manda ISO com microsegundos e fuso
 * (ex. `...03T03:08:41.377819+00:00`), e a captura do dono (13/10/2026)
 * mostrava o cru estourando o card — 30 caracteres para dizer o dia. O dia
 * basta; a hora do treino nao opera nada. Fora do formato, travessao.
 */
export function diaDoTreino(iso: string | null | undefined): string {
  if (!iso) return '—';
  const dia = String(iso).slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(dia) ? dia : '—';
}

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

  /**
   * Quantos ARTEFATOS existem, tirando os repetidos.
   *
   * MEDIDO (09/10/2026): os tres modelos de classe cobrem varios periodos e
   * cada periodo e uma linha. Contar linhas diria 48 modelos quando existem 39
   * arquivos `.pkl`. O contador pela coluna "Modelo" repetia o mesmo nome
   * quatro vezes para o mesmo artefato, que e exatamente o que o dono apontou
   * na captura de 20:28.
   */
  const artefatos = useMemo(
    () => new Set(modelos.map((m) => m.id)).size,
    [modelos],
  );

  /*
    ESCOLHER O MODELO ESCOLHE O PAR E O PERÍODO.

    É a única coerência que importa: se clicar em `EURUSD_H4` e o gráfico
    continuar em `GOLD · M15`, o operador opera um par com o modelo de outro.
    Por isso os dois vão juntos, para `selectedSymbol` e para o timeframe do
    motor.
  */
  /*
    O CARD DE CLASSE NAO ESCOLHE PAR (12/11/2026)
    ==============================================
    MEDIDO no app instalado 1.2.182 (12/11 23:50): clicar no card
    `MODELO MULTI_METALS 5M` gravava `MULTI_METALS` em `selectedSymbol` e mandava
    o MESMO texto como `simbolo` para `/api/auto/config`. A aba ROBO passava a
    pedir candles de `MULTI_METALS` — que nao existe em corretora nenhuma — e a
    tela dizia:

        Gráfico indisponível: nenhuma fonte publica respondeu para MULTI_METALS
        M5 (binance: ...; yahoo: ...; frankfurter: ...)

    O grafico vazio nao era do grafico: era o NOME DO MODELO no lugar do par.

    O backend ja sabia disso e a tela nao perguntava. Medido no Python do repo:

        simbolo_valido('MULTI_METALS')    -> False
        classe_de('MULTI_METALS')         -> OUTROS
        _tentativas_multi('MULTI_METALS') -> []
        _tentativas_multi('XAUUSD','M5')  -> [('MULTI_METALS','MULTI_METALS_M5'), ...]

    A ultima linha e a regra que resolve o caso SEM adivinhar ativo (§3): o
    modelo de classe entra SOZINHO para o ativo real que o operador escolheu
    (`_classe_multi_de` le a classe do simbolo). Entao o card de classe nao
    precisa — e nao pode — escolher par nenhum:

      - com par ja escolhido, ele troca SO o periodo desse par (o modelo da
        classe e o que vai decidir por ele, de qualquer forma);
      - sem par escolhido, ele RECUSA com motivo, nomeando a classe, em vez de
        inventar um ativo ou gravar o nome do modelo.
  */
  const escolher = async (m: ModeloTreinado) => {
    setRecusa('');
    const deClasse = m.id.startsWith('MULTI_');
    const classe = deClasse ? m.id.slice('MULTI_'.length) : '';
    /*
      `parNaTela` e a MESMA regra que a barra, o painel e o grafico leem. Um
      `selectedSymbol` que ja esteja com o nome do modelo (persistido no
      localStorage de quem clicou antes desta correcao) nao conta como par.
    */
    const escolhidoNaTela = ehClasseDeModelo(selectedSymbol)
      ? ''
      : String(selectedSymbol ?? '').trim().toUpperCase();
    const par = deClasse ? escolhidoNaTela : String(m.symbol ?? '').trim().toUpperCase();
    if (!par) {
      setRecusa(
        deClasse
          ? `${m.id} é um modelo de CLASSE — cobre os ativos da classe ${classe}, não um par. Escolha o par em «Par para operar»: o modelo da classe entra sozinho para o ativo que você escolher.`
          : `${m.label ?? m.id} veio sem par: sem símbolo não há gráfico nem inferência.`,
      );
      return;
    }
    setSelectedSymbol(par);
    try {
      const r = await fetch(`${apiBase()}/api/auto/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ simbolo: par, timeframe: m.timeframe }),
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
          `Modelo aplicado ao motor (${par} · ${d.timeframe ?? m.timeframe}), mas o automático não liga ainda: ${d.error ?? ''}`,
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
            {/*
              O CONTADOR CONTA LINHAS, E LINHAS NAO SAO ARTEFATOS (09/10/2026)
              =================================================================
              MEDIDO: um modelo de CLASSE (`MULTI_METALS`) cobre QUATRO periodos
              e virou quatro linhas aqui. O contador somava as linhas, entao
              depois da correcao que trouxe os tres multi de volta ele passou a
              dizer "37 de 48" — e sao 39 artefatos, tres deles com quatro
              linhas cada. 48 e a quantidade de OPORTUNIDADES de operacao, nao
              de modelos, e o operador lia como quantidade de modelos.

              Agora o numero certo aparece por linha: quantos ARTEFATOS
              diferentes existem (pelos `id` unicos) e quantos deles podem
              operar.
            */}
            {artefatos} artefatos · {publicaveis} de {modelos.length} períodos podem operar
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
          {isMobileRuntime()
            ? 'Nenhum modelo ativo retornado pelo gateway remoto. Verifique a conexão com o servidor/gateway.'
            : 'Nenhum modelo treinado encontrado. Sem modelo não há inferência, e sem inferência o automático não opera.'}
        </p>
      ) : null}

      {ordenados.length > 0 && (
        <div className="robo-modelos-grade">
          {/*
            UM CARD POR MODELO (12/10/2026, decisao do dono).
            ==================================================
            A tabela virou grade de cartoes: cada modelo tem cara (capa com
            classe, periodo e metricas), mini informacoes (par, algoritmo,
            testes, treino, motivo) e estado. Clicar opera o par no periodo,
            como a linha fazia — o gesto nao mudou, so a leitura.

            A classe da capa vem do `id` MULTI_* (o nome do treino, estruturado)
            ou fica vazia (cinza honesto) — nunca adivinhada do simbolo.
          */}
          {ordenados.map((m) => {
            const podeOperar = m.publicable && m.pkl_present;
            const emUso =
              m.symbol.toUpperCase() === simboloMotor &&
              m.timeframe.toUpperCase() === tfMotor;
            const classe = m.id.startsWith('MULTI_')
              ? m.id.slice('MULTI_'.length).toLowerCase()
              : undefined;
            return (
              <article
                key={`${m.id}|${m.timeframe}`}
                className={`robo-modelo robo-modelo-card${emUso ? ' em-uso' : ''}${
                  podeOperar ? '' : ' reprovado'
                }`}
                title={
                  podeOperar
                    ? `${m.symbol} em ${m.timeframe} — clique para operar este par neste período`
                    : (m.reason ?? 'modelo reprovado no treino')
                }
                role="button"
                tabIndex={0}
                aria-label={`${m.label ?? m.id} — ${podeOperar ? (emUso ? 'no motor agora' : 'pode operar') : 'reprovado'}`}
                onClick={() => void escolher(m)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    void escolher(m);
                  }
                }}
              >
                <ModelCover
                  modelo={{
                    id: m.id,
                    label: m.label,
                    symbol: m.id.startsWith('MULTI_') ? rotuloClasseMulti(m.id) : m.symbol,
                    timeframe: m.timeframe,
                    accuracy: m.accuracy,
                    edge: m.edge,
                    f1: m.f1,
                    publicable: m.publicable,
                    pklPresent: m.pkl_present,
                    assetClass: classe ?? null,
                  }}
                  selecionado={emUso}
                />
                <dl className="robo-modelo-mini">
                  <div>
                    {/* CORRIGIDO 23/11/2026 ("leitura horrivel" no celular): o
                        rotulo fixo "Par" repetido em 17 linhas era enganoso nos
                        modelos de classe — "classe METALS" nao e um par que se
                        possa escolher. Agora a coluna diz "Classe" quando o
                        valor e uma classe, e "Par" quando e um ativo real. */}
                    <dt>{m.id.startsWith('MULTI_') ? 'Classe' : 'Par'}</dt>
                    <dd>
                      <strong>
                        {m.id.startsWith('MULTI_') ? rotuloClasseMulti(m.id) : m.symbol}
                      </strong>
                    </dd>
                  </div>
                  <div>
                    <dt>Período</dt>
                    <dd>{m.timeframe}</dd>
                  </div>
                  <div>
                    <dt>Testes</dt>
                    <dd className="num">{m.test_samples ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>F1</dt>
                    <dd className="num">{pct(m.f1)}</dd>
                  </div>
                  <div>
                    <dt>Algoritmo</dt>
                    <dd>{m.algorithm ?? '—'}</dd>
                  </div>
                  <div>
                    <dt>Treino em</dt>
                    <dd>{diaDoTreino(m.train_date)}</dd>
                  </div>
                  <div>
                    <dt>Estado</dt>
                    <dd>
                      {podeOperar ? (
                        <span className={`chip ${emUso ? 'ok' : 'neutral'}`}>
                          {emUso ? 'no motor agora' : isMobileRuntime() ? 'ativo no gateway' : 'pode operar'}
                        </span>
                      ) : (
                        <span className="chip warn" title={m.reason ?? ''}>
                          {m.pkl_present ? 'reprovado' : isMobileRuntime() ? 'indisponível no gateway' : 'sem artefato'}
                        </span>
                      )}
                    </dd>
                  </div>
                  {!podeOperar && m.reason ? (
                    <div className="robo-modelo-motivo">
                      <dt>Motivo</dt>
                      <dd>{m.reason}</dd>
                    </div>
                  ) : null}
                </dl>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}