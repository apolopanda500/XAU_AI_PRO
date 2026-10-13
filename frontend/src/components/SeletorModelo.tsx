// ===========================================================================
//  MODELO/PERIODO — qual modelo o motor automático vai usar.
//
//  POR QUE ESTE PAINEL EXISTE (e por que mudou de casa em 05/10/2026)
//  ==================================================================
//  Ele era um bloco separado chamado "Ativo e Período". O dono pediu para
//  remover, e o motivo se sustenta:
//
//  - o PAR não é escolhido aqui. É escolhido na barra inferior, que é onde o
//    MT5 e a XM colocam, e escolher nos dois é o caminho para os dois
//    discordarem — quando discordam, o operador acredita no lugar errado;
//  - o que sobra e a escolha do MODELO, e ela pertence à operação automática:
//    sem modelo não existe "operação automática completa com modelos".
//
//  ENTÃO ESTE PAINEL ENTROU DENTRO DA OPERAÇÃO AUTOMÁTICA, e o que sobrou
//  é só o que o motor precisa: modelo e período.
//
//  O QUE ESTE PAINEL FAZ E SÓ ESCOLHER
//  =====================================
//  Escolher o MODELO/PERIODO não chama o gateway: o backend resolve o modelo
//  por (symbol, timeframe), então o período escolhido é o que vai para o motor
//  quando ele roda.
//
//  Edge e acerto aparecem no rótulo porque o operador escolhe entre modelos com
//  números diferentes. Vem do TREINO (`.meta.json`), e medido: não é previsão.
// ===========================================================================
import { useCallback, useEffect, useMemo, useState } from 'react';
import { apiBase } from '../lib/api';
import { useAppStore } from '../hooks/useAppStore';
import { parseAssetCatalog, type AssetRow } from '../lib/brokerCatalog';
import { useCatalogoAtivos } from '../hooks/useCatalogoAtivos';
import { escopoAtivo } from '../lib/escopoAtivo';
import { useAutoState } from '../hooks/queries';
import type { Broker } from '../lib/connections';

// Base resolvida por chamada (13/10/2026), nunca congelada no topo do modulo.

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

/**
 * O PAR VEM DO CATÁLOGO DA CORRETORA, e nao da lista de modelos.
 *
 * MEDIDO (05/10/2026): a conta 391773676 devolve 1639 ativos em
 * `/api/universal/assets`. Antes, a lista de pares aqui vinha de
 * `modelos.map(m => m.symbol)` — ou seja, SÓ dos pares que têm modelo treinado.
 *
 * Consequência medida: com nenhum modelo carregado, a lista vinha vazia, o
 * campo não tinha uma única opção, e o Robô virava um beco sem saída — o
 * operador não tinha como escolher par, o gráfico não tinha o que desenhar e
 * a operação automática recusava com "escolha o ativo em outra aba".
 *
 * O catálogo é a fonte certa, e é o que a regra do projeto exige: a lista de
 * ativos vem da CORRETORA, não de uma lista fixa no app. Os pares sem modelo
 * aparecem, e o operador escolhe; o seletor de modelo ao lado avisa que
 * aquele par não tem modelo — em vez de esconder o par inteiro.
 */

export default function SeletorModelo() {
  const selectedSymbol = useAppStore((s) => s.selectedSymbol);
  const setSelectedSymbol = useAppStore((s) => s.setSelectedSymbol);
  /*
    O TIMEFRAME DO MOTOR, e por que o modelo precisa dele (06/10/2026)
    ===================================================================
    MEDIDO no app instalado: com `BTCUSD` e `H4` escolhidos na barra inferior,
    o campo "Modelo / periodo" continuava em `H1 · edge 12,2% · acerto 45,6%`, e
    a frase abaixo dizia "O motor vai operar BTCUSD no periodo H1". A lista
    TINHA o `BTCUSD_H4` — marcado "no motor".

    A causa: a escolha de modelo era `visiveis[0]`, o PRIMEIRO da resposta da
    API. A ordem da resposta e do backend, e nao do operador: BTCUSD tem H1 e
    H4, e o H1 vinha primeiro. O timeframe escolhido na barra nunca entrou na
    conta.

    E sao DOIS controles que os dois dizem "escolher o periodo": a barra
    inferior (que escreve o timeframe do MOTOR, via `/api/auto/config`) e este
    campo. Nenhum dos dois escrevia no outro, entao o operador trocava o
    periodo na barra e a tela confirmava o antigo — e o painel dizia o periodo
    errado com toda a certeza. E o AGENTS.md 5: o defeito e do lado que LE o
    nome diferente, e o sintoma (operar no periodo errado) cairia na corretora.

    Aqui o timeframe e do MOTOR, que e quem decide. O modelo segue o periodo,
    e nao a ordem da resposta.
  */
  /*
    O TIMEFRAME DO MOTOR, e por que o modelo precisa dele (06/10/2026)
    ===================================================================
    MEDIDO no app instalado: com `BTCUSD` e `H4` escolhidos na barra inferior,
    o campo "Modelo / periodo" continuava em `H1 · edge 12,2% · acerto 45,6%`, e
    a frase abaixo dizia "O motor vai operar BTCUSD no periodo H1". A lista
    TINHA o `BTCUSD_H4` — marcado "no motor".

    A causa: a escolha de modelo era `visiveis[0]`, o PRIMEIRO da resposta da
    API. A ordem da resposta e do backend, e nao do operador: BTCUSD tem H1 e
    H4, e o H1 vinha primeiro. O timeframe escolhido na barra nunca entrou na
    conta.

    E sao DOIS controles que os dois dizem "escolher o periodo": a barra
    inferior (que escreve o timeframe do MOTOR, via `/api/auto/config`) e este
    campo. Nenhum dos dois escrevia no outro, entao o operador trocava o
    periodo na barra e a tela confirmava o antigo — e o painel dizia o periodo
    errado com toda a certeza. E o AGENTS.md 5: o defeito e do lado que LE o
    nome diferente, e o sintoma (operar no periodo errado) cairia na corretora.

    Aqui o timeframe e do MOTOR, que e quem decide. O modelo segue o periodo,
    e nao a ordem da resposta.
  */
  const autoQ = useAutoState();
  const timeframeDoMotor = String(autoQ.data?.timeframe ?? '').toUpperCase();
  const [modelos, setModelos] = useState<Modelo[]>([]);
  const [modeloId, setModeloId] = useState('');
  const [erroLista, setErroLista] = useState('');

  /*
    O ESCOPO VEM DE `escopoAtivo()`, o MESMO do gráfico e do terminal.
    ===========================================================
    Ler o escopo de outro lugar é o defeito que `escopoAtivo.ts` existe para
    impedir: gráfico, terminal e este painel leriam mercados diferentes do
    mesmo `localStorage`, e o par escolhido aqui apareceria em outro mercado no
    gráfico.
  */
  const { broker: brokerEscopo, market: mercadoEscopo } = escopoAtivo();
  // SEM CORRETORA MEDIDA, SEM CORRETORA AQUI (11/10/2026, decisao do dono:
  // nada de MT5 fixo). Era `|| 'mt5'` — e o seletor listava o catalogo de uma
  // corretora que ninguem escolheu. Com vazio, o catalogo vem vazio (ver
  // `useCatalogoAtivos`) e os campos pedem a escolha em vez de listar MT5.
  const broker = String(brokerEscopo || '') as Broker;

  useEffect(() => {
    const controller = new AbortController();
    void fetch(`${apiBase()}/api/ai/trained`, { signal: controller.signal })
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

  const catalogo = useCatalogoAtivos(broker, mercadoEscopo);

  // Os pares que o operador pode escolher são os do CATÁLOGO, e não os que têm
  // modelo. Filtrar por `temModelo` esconderia o par inteiro da corretora.
  const simbolos = useMemo(() => catalogo.map((a) => a.symbol), [catalogo]);
  const comModelo = useMemo(() => new Set(modelos.map((m) => m.symbol)), [modelos]);
  /*
    SEM CATALOGO, OS MODELOS SAO A LISTA (12/10/2026).
    ==================================================
    MEDIDO no app instalado: sem corretora escolhida, o catalogo vem vazio e
    os dois `<select>` nasciam DESABILITADOS e vazios — "nao tem como clicar
    em nada". A lista de MODELOS (`/api/ai/trained`) nao precisa de corretora,
    e cada modelo tem par: sem catalogo, os pares dos modelos treinados sao
    opcoes reais (tem artefato, tem periodo), marcadas como tal. Nada e
    presumido: continua sem escolha ate o operador clicar.
  */
  const simbolosDosModelos = useMemo(
    () => [...new Set(modelos.map((m) => String(m.symbol || '').toUpperCase()).filter(Boolean))],
    [modelos],
  );
  const paresElegiveis = useMemo(() => {
    const vistos = new Set(simbolos);
    return [...simbolos, ...simbolosDosModelos.filter((s) => !vistos.has(s))];
  }, [simbolos, simbolosDosModelos]);

  /*
    A LISTA DE PARES: SO OS QUE TEM MODELO, E O RESTO A UM CLIQUE (09/10/2026)
    ==========================================================================
    MEDIDO no app instalado, 17:09, com o seletor aberto na conta 391773676:
    a lista comeca em `EUR50CASH (sem modelo)`, `EURAUD (sem modelo)`,
    `EURAZE (sem modelo)`... e segue por centenas de pares do mesmo tipo.

    Sao 1639 ativos na conta e 28 com modelo treinado. Ou seja: **1611 das
    opcoes nao podem ser operadas**, porque `_trava_instrumento()` recusa ciclo
    sem modelo. O operador tinha de rolar uma lista de 1639 itens para achar os
    28 que servem — e cada item nao operavel ainda carregava um sufixo de texto
    que ocupava espaco.

    O que muda:

    - A lista mostra os **28 com modelo**, primeiro. E o que o operador pode
      usar.
    - Um interruptor no rodape do campo mostra **os 1639**, para quem precisa
      ver a corretora inteira. O catalogo NAO e escondido: e so tirado da
      frente.
    - Se o par **ja escolhido** nao tem modelo, ele continua na lista, marcado.
      Sem isso, escolher um par sem modelo e recarregar a tela deixaria o
      operador sem ver o que estava selecionado — e o campo mentindo sobre o
      proprio valor.

    MEDIDO antes e depois da lista: `1639 opcoes` -> `28 opcoes`.
  */
  const [mostrarTodos, setMostrarTodos] = useState(false);
  const simbolosComModelo = useMemo(() => {
    const comModeloOrdenados = paresElegiveis.filter((s) => comModelo.has(s));
    if (mostrarTodos) return paresElegiveis;
    return comModeloOrdenados;
  }, [paresElegiveis, comModelo, mostrarTodos]);
  const totalSemModelo = useMemo(
    () => simbolos.length - simbolos.filter((s) => comModelo.has(s)).length,
    [simbolos, comModelo],
  );

  const simbolo = useMemo(() => {
    const atual = (selectedSymbol || '').toUpperCase();
    // O par já escolhido vence, desde que ainda exista nas opcoes (catalogo
    // ou modelos — ver `paresElegiveis`).
    if (atual && paresElegiveis.includes(atual)) return atual;

    /*
      SEM ESCOLHA, SEM PAR (11/10/2026, decisao do dono: nada de BTCUSD fixo).

      MEDIDO: sem par escolhido, esta linha caia no primeiro modelo publicavel
      da resposta da API — na pratica, BTCUSD — e o efeito abaixo GRAVAVA esse
      par no store. A aba ROBO inteira nascia operando BTCUSD sem ninguem ter
      escolhido: par, grafico, preco e modelo, tudo do primeiro item da lista.

      E o AGENTS.md §3 na forma mais direta: simbolo vazio e RECUSA COM MOTIVO,
      nunca um ativo padrao. Sem escolha o campo mostra o placeholder e o resto
      da tela recusa nomeando este seletor.
    */
    return '';
  }, [selectedSymbol, paresElegiveis]);

  const visiveis = useMemo(
    () => modelos.filter((m) => m.symbol === simbolo),
    [modelos, simbolo],
  );

  /*
    O MODELO ESCOLHIDO SEGUE O PERIODO DO MOTOR.

    MEDIDO (06/10/2026): era `visiveis[0]`, o primeiro da resposta da API. Com
    BTCUSD (que tem H1 e H4) e H4 escolhido na barra, a tela mostrava o modelo
    H1 — e a frase abaixo confirmava "o motor vai operar no periodo H1".

    A ordem da resposta e do BACKEND, e nao do operador. Um campo que depende
    da ordem de um array remoto e um campo que muda sozinho quando o backend
    reordena.

    `candidatoDoPeriodo` procura o modelo do periodo escolhido. Sem ele no
    periodo, `null` — e a frase passa a DIZER que nao ha modelo para o periodo,
    em vez de exibir o de outro periodo com toda a certeza. Um modelo de H1
    apresentado num painel em H4 e o operador operar no periodo errado achando
    que trocou.
  */
  const candidatoDoPeriodo = useMemo(() => {
    const doPeriodo = timeframeDoMotor
      ? visiveis.find((m) => m.timeframe.toUpperCase() === timeframeDoMotor)
      : undefined;
    // SEM MODELO DO PERIODO, NADA (11/10/2026): era `?? visiveis[0]` — o
    // primeiro da resposta da API, que na pratica exibia um modelo de outro
    // periodo com toda a certeza. A frase abaixo passa a dizer que nao ha
    // modelo para o periodo (ver o `<select>`: placeholder em vez de valor).
    return doPeriodo ?? null;
  }, [visiveis, timeframeDoMotor]);

  /*
    SEM CANDIDATO, SEM MODELO (11/10/2026). Era "primeiro publicavel, senao o
    primeiro da lista" — e com o par vindo do primeiro modelo publicavel, a
    combinacao escolhia SOZINHA o par e o modelo da tela inicial (na pratica,
    BTCUSD). O operador escolhia o modelo; a tela mostra o placeholder ate la.
  */
  const modeloReservado = useMemo(() => candidatoDoPeriodo, [candidatoDoPeriodo]);

  useEffect(() => {
    const alvo = modeloReservado?.id ?? '';
    // Só troca quando o alvo MUDA. Sem esta guarda o efeito reescrevia o
    // estado a cada render e o `<select>` perdia a seleção do operador.
    if (alvo && alvo !== modeloId) setModeloId(alvo);
  }, [modeloReservado, modeloId]);

  /*
    Trocar de par ZERA o modelo escolhido.

    Sem isso, o par novo ficava com o período do par anterior, e o operador
    achava que tinha trocado o par quando só tinha trocado o nome — o mesmo
    defeito que a troca de corretora já tinha, corrigido em 05/10/2026.
  */
  const escolherAtivo = useCallback(
    (novo: string) => {
      setSelectedSymbol(novo.toUpperCase());
      setModeloId('');
    },
    [setSelectedSymbol],
  );

  /*
    A GRAVACAO AUTOMATICA SAIU (11/10/2026, decisao do dono: nada de BTCUSD
    fixo). Este efeito gravava no store o par que o `simbolo` derivava — e o
    `simbolo` caia no primeiro modelo publicavel, ou seja, gravava BTCUSD sem
    ninguem escolher. Agora `simbolo` so repete o `selectedSymbol` ja gravado
    (ou `''`), e quem grava e o `onChange` do operador (`escolherAtivo`).
  */

  const escolhido = useMemo(
    () => visiveis.find((m) => m.id === modeloId) ?? null,
    [visiveis, modeloId],
  );

  return (
    <div className="robo-par" aria-labelledby="robo-par-title">
      <div className="robo-par-linha">
        {/*
          O PAR É ESCOLHIDO AQUI, e é o ÚNICO lugar da página onde isso acontece.

          MEDIDO (05/10/2026): sem par escolhido, o Robô é um beco sem saída.
          Sem par, o gráfico não tem o que desenhar; sem par, a operação
          automática recusa; e o painel mandava o operador escolher o ativo em
          OUTRA ABA — enquanto o bloco que fazia essa escolha tinha sido
          removido a pedido dele.

          A lista vem do CATÁLOGO DA CORRETORA (`/api/universal/assets`), e não
          de uma lista fixa no app nem só dos pares com modelo treinado: são
          1639 ativos na conta real, e esconder os que não têm modelo seria
          esconder a corretora.

          Fica dentro da operação automática, e não como bloco separado: o
          dono pediu para remover o bloco "Ativo e Período", e a escolha do par
          pertence ao lugar onde o motor é ligado.
        */}
        <label className="field robo-par-ativo">
          <span>Par para operar</span>
          <select
            aria-label="Par para operar"
            value={simbolo}
            disabled={!simbolosComModelo.length}
            onChange={(e) => escolherAtivo(e.target.value)}
          >
            {/*
              SEM PAR, PLACEHOLDER — nunca o primeiro da lista (11/10/2026).
              Um `<select>` sem opcao para o valor `''` mostra o primeiro item
              como se fosse escolha, e era assim que o BTCUSD nascia "fixo".
            */}
            {!simbolo && <option value="">Escolha o par…</option>}
            {!simbolosComModelo.length && (
              <option value={simbolo}>{simbolo || '—'}</option>
            )}
            {/*
              O par JA ESCOLHIDO sempre aparece, mesmo sem modelo. Sem esta
              linha, quem escolheu um par sem modelo veria o campo vazio ao
              recarregar — e o campo estaria mentindo sobre o proprio valor.
            */}
            {simbolo &&
              !simbolosComModelo.includes(simbolo) && (
                <option value={simbolo}>{simbolo} (sem modelo)</option>
              )}
            {simbolosComModelo.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          {totalSemModelo > 0 && (
            <button
              type="button"
              className="btn xs ghost robo-par-ver-todos"
              aria-pressed={mostrarTodos}
              onClick={() => setMostrarTodos((v) => !v)}
              title={`Mostrar os ${simbolos.length} ativos da corretora, incluindo os ${totalSemModelo} que ainda não têm modelo treinado`}
            >
              {mostrarTodos
                ? `Mostrar só os que podem operar`
                : `Ver os ${totalSemModelo} sem modelo`}
            </button>
          )}
        </label>

        <label className="field robo-par-modelo">
          <span>Modelo / período</span>
          <select
            aria-label="Modelo do robo"
            value={modeloId}
            disabled={!visiveis.length}
            onChange={(e) => setModeloId(e.target.value)}
          >
            {!modeloId && visiveis.length > 0 && (
              <option value="">Escolha o modelo…</option>
            )}
            {!visiveis.length && (
              <option value="">
                {simbolo
                  ? `Nenhum modelo carregável para ${simbolo}`
                  : 'Escolha o par ao lado ou na barra inferior'}
              </option>
            )}
            {visiveis.map((m) => (
              <option key={m.id} value={m.id}>
                {m.timeframe} · edge {pct(m.edge)} · acerto {pct(m.accuracy)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {erroLista ? (
        <p className="hint" role="status">
          {erroLista}
        </p>
      ) : null}
      {escolhido && (
        <p className="robo-par-nota">
          O motor opera neste modelo quando o automático estiver ligado.
        </p>
      )}
    </div>
  );
}
