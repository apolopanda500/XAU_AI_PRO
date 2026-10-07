/**
 * Calendário Econômico — padrão MetaTrader 5 (05/10/2026).
 *
 * O DONO PEDIU
 * ============
 * "aba calendarios reconstruir nao gostei, pesquisar mt5 calenadario copiar"
 *
 * O QUE A TELA ANTIGA FAIA DE ERRADO
 * ===================================
 * Uma lista ÚNICA de 30 eventos, de 14 dias, empilhada e rolável. Três
 * problemas, todos medidos:
 *
 * 1. TREIS COLUNAS MORTAS. Anterior / Previsão / Real apareciam no cabeçalho e
 *    ficavam permanentemente em `--`. A fonte era a tabela local de
 *    `planos/economic_calendar.py`, que sabe QUANDO o evento acontece e nada
 *    mais. Coluna que nunca pode ter dado faz o operador desconfiar do resto.
 *    → Agora a semana corrente vem do feed público, que traz os três valores.
 *
 * 2. SEM DIA SELECIONADO. Com 14 dias empilhados, o operador rolava procurando
 *    "o que sai hoje" e não achava o marcador. O MT5 mostra UM dia por vez,
 *    com uma aba por dia.
 *
 * 3. SEM NAVEGAÇÃO. Não havia como pular para a próxima semana.
 *
 * O QUE O MT5 FAZ, E O QUE AQUI ESTÁ
 * ===================================
 * Documentação do MT5 (Charts/Fundamental): abas por dia na parte de cima,
 * navegação por semana, colunas Data/Hora · Moeda · Importância · Real ·
 * Previsão · Anterior,Importance em três estrelas, filtro por país e por
 * importance, e janela de detalhe ao abrir o evento.
 *
 * Tudo isso está aqui. A diferença de fuse:
 *
 * - aImportance é o que decide a operação, então o filtro de importance fica
 *   ACIMA da tabela e as estrelas repetem em cada linha;
 * - a fonte de cada linha é declarada. Evento do feed público é dado publicado;
 *   evento de estimativa local é horário estimado, sem valor. A tela escreve
 *   qual é — misturar os dois sem aviso seria o defeito que a coluna morta já
 *   era.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useEconomicData } from '../../hooks/useEconomicData';
import { apiBase } from '../../lib/api';
import '../../theme/calendar.css';
import {
  EconomicEvent,
  FiltroCalendario,
  ImpactLevel,
} from './types';

const LABELS_IMPACTO: Record<ImpactLevel, string> = {
  baixo: 'Baixo',
  medio: 'Médio',
  alto: 'Alto',
};

/** Estrelas de importância, como no MT5: 3 = alto, 2 = médio, 1 = baixo. */
const ESTRELAS: Record<ImpactLevel, number> = { alto: 3, medio: 2, baixo: 1 };

export type DiaCalendario = {
  /** yyyy-mm-dd — serve de key e garante ordem estável. */
  chave: string;
  /** "Hoje"/"Amanhã"/"Ontem" quando cabe, senão vazio. */
  relato: string;
  /** Data por extenso, em minúsculas (o CSS deixa a inicial maiúscula). */
  data: string;
  eventos: EconomicEvent[];
};

const chaveDoDia = (d: Date): string =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

function relatoDia(d: Date, agora: Date): string {
  const meioNoite = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const dias = Math.round((meioNoite(d) - meioNoite(agora)) / 86_400_000);
  if (dias === 0) return 'Hoje';
  if (dias === 1) return 'Amanhã';
  if (dias === -1) return 'Ontem';
  return '';
}

/**
 * Agrupa por dia e ordena DO BAIXO PARA O ALTO.
 *
 * Antes o agrupamento usava a ordem de chegada da API, que vem agrupada por
 * país: o dia 29 aparecia antes do 28 e o rótulo de dia subia fora de ordem.
 * Aqui os eventos são ordenados por horário primeiro — daí a ordem dos dias e
 * a ordem deles dentro do dia caem sozinhas.
 */
export function agruparPorDia(eventos: EconomicEvent[], agora: Date = new Date()): DiaCalendario[] {
  const ordenados = [...eventos].sort((a, b) => a.horario.getTime() - b.horario.getTime());
  const grupos = new Map<string, DiaCalendario>();

  for (const evento of ordenados) {
    const d = evento.horario;
    const chave = chaveDoDia(d);
    let dia = grupos.get(chave);
    if (!dia) {
      dia = {
        chave,
        relato: relatoDia(d, agora),
        data: d.toLocaleDateString('pt-BR', {
          weekday: 'long',
          day: '2-digit',
          month: '2-digit',
          year: 'numeric',
        }),
        eventos: [],
      };
      grupos.set(chave, dia);
    }
    dia.eventos.push(evento);
  }

  return [...grupos.values()];
}

/**
 * Os SETE DIAS da semana visível, com ou sem evento.
 *
 * MEDIDO no feed público em 05/10/2026: os 82 eventos vão de 04/10 até 11/10.
 * Hoje é segunda-feira, então `inicioDaSemana` dá 05/10 — e os eventos de
 * ONTEM (04/10) ficam na semana ANTERIOR. O dono viu isso como "as páginas
 * seguintes e anteriores estão vazias".
 *
 * Antes a tira mostrava só os dias COM evento. Consequência: numa semana sem
 * evento nenhum aparecia o texto "Sem eventos nesta semana" e NENHUMA aba para
 * onde ir — a navegação começava a terminar ali. Sem as sete abas não há como
 * distinguir "o dia está vazio" de "a semana está fora da janela do feed".
 *
 * Agora as sete sempre aparecem, e o dia vazio mostra "sem eventos" ao ser
 * clicado. A diferença entre "não tem" e "não carregou" fica visível.
 */
export function diasCompletosDaSemana(
  semana: Date,
  porChave: Map<string, DiaCalendario>,
  agora: Date = new Date(),
): DiaCalendario[] {
  const inicio = inicioDaSemana(semana);
  return Array.from({ length: 7 }, (_, i) => {
    const d = new Date(inicio.getFullYear(), inicio.getMonth(), inicio.getDate() + i);
    const chave = chaveDoDia(d);
    const existente = porChave.get(chave);
    if (existente) return existente;
    return {
      chave,
      relato: relatoDia(d, agora),
      data: d.toLocaleDateString('pt-BR', {
        weekday: 'long',
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      }),
      eventos: [],
    };
  });
}

/** Início da semana no fuso (segunda a domingo), para navegar por semana. */
function inicioDaSemana(base: Date): Date {
  // `getDay()`: 0 = domingo. A semana do calendário econômico começa na
  // segunda, então domingo é o último dia, não o primeiro.
  const meioNoite = new Date(base.getFullYear(), base.getMonth(), base.getDate());
  const deslocamento = (meioNoite.getDay() + 6) % 7;
  meioNoite.setDate(meioNoite.getDate() - deslocamento);
  return meioNoite;
}

function Estrelas({ impacto }: { impacto: ImpactLevel }) {
  const total = ESTRELAS[impacto];
  return (
    <span
      className={`cal-stars cal-stars-${impacto}`}
      role="img"
      aria-label={`Importância ${LABELS_IMPACTO[impacto]}`}
      title={`Importância ${LABELS_IMPACTO[impacto]}`}
    >
      {[0, 1, 2].map((i) => (
        <span key={i} aria-hidden="true" className={i < total ? 'on' : 'off'}>
          ★
        </span>
      ))}
    </span>
  );
}

/**
 * Uma célula de valor: Anterior, Previsão ou Real.
 *
 * O `--` ERA A DECISÃO ERRADA, e o comentário antigo defendia o oposto (05/10/2026).
 *
 * O argumento era: "célula vazia ao lado de célula com número deixa o operador sem
 * saber qual das duas é ausência". O problema é que `--` não diz *qual* ausência:
 *
 *   - evento **estimado** (semana seguinte): o produtor não publica valor, e
 *     isso é uma coisa;
 *   - evento do **feed público** sem aquele campo: ausência é outra coisa;
 *   - evento **ainda não divulgado** na coluna Real: o valor não existe porque
 *     ainda vai existir.
 *
 * Três ausências diferentes, o mesmo `--`. E o dono leu isso como ruído — o
 * `--` aparecia nas duas primeiras linhas de cada bloco da captura, ao lado de
 * números reais, e poluía a tabela sem explicar nada.
 *
 * Agora a célula fica VAZIA e o motivo vai no `title` do espaço. Vazio é o
 * desenho correto para "não há número": é o que o MT5 e a XM fazem, e nenhum dos
 * dois escreve um trace numa célula numérica. Quem precisa saber o motivo passa
 * o mouse e lê — e a razão está escrita, não adivinhada.
 */
/**
 * POR QUE a coluna está vazia — as três ausências que `--` colapsava.
 *
 * MEDIDO (05/10/2026): 111 eventos no total — 82 do feed público e 29
 * estimados. Os estimados são horário previsto e **não têm valor publicado por
 * definição**; os do feed público têm anterior/previsão, e só a coluna Real
 * fica vazia enquanto o evento não foi divulgado.
 */
function motivoAusente(evento: EconomicEvent, coluna: string): string {
  if (evento.estimado) {
    return `${coluna}: horário estimado pela agenda — o produtor não publica valor previsto`;
  }
  return `${coluna}: o produtor não informou este valor`;
}

function motivoReal(evento: EconomicEvent): string {
  if (evento.estimado) {
    return 'Real: horário estimado pela agenda — não existe valor publicado';
  }
  if (!evento.divulgado) {
    return 'Real: o evento ainda não foi divulgado';
  }
  return 'Real: o produtor não informou o valor';
}

function Valor({
  valor,
  forte,
  ausente,
}: {
  valor: string | null;
  forte?: boolean;
  /** Por que a célula está vazia. Vai no `title`; não ocupa a coluna. */
  ausente?: string;
}) {
  if (valor === null || valor === undefined || !String(valor).trim()) {
    return <span className="cal-sem-valor" title={ausente ?? 'O produtor não informou este valor'} />;
  }
  return <span className={`num${forte ? ' cal-real' : ''}`}>{valor}</span>;
}

export function EconomicCalendarTab() {
  const [filtro, setFiltro] = useState<FiltroCalendario>({
    paises: [],
    impactos: [],
    dataInicio: null,
    dataFim: null,
  });
  /** Semana visível, como âncora do domingo. Navegar move 7 dias. */
  const [semana, setSemana] = useState(() => inicioDaSemana(new Date()));
  /** Dia selecionado — o MT5 mostra UM dia por vez. */
  const [diaSelecionado, setDiaSelecionado] = useState<string | null>(null);
  const [aberto, setAberto] = useState<EconomicEvent | null>(null);

  const {
    eventos,
    carregando,
    erro,
    ultimaAtualizacao,
    refreshManual,
    totalEventos,
    fontes,
  } = useEconomicData(filtro);

  // Agenda completa (sem filtro de data) para as abas mostrarem o que existe em
  // cada dia, mesmo com um filtro que esconde o dia inteiro.
  const { eventos: todosEventos } = useEconomicData({ ...filtro, dataInicio: null, dataFim: null });

  const dias = useMemo(() => agruparPorDia(todosEventos), [todosEventos]);
  /*
    OS SETE DIAS, SEMPRE — inclusive os vazios (05/10/2026).

    `dias` só tem os dias que têm evento. Filtrar por semana sobre ele dava
    abas só nos dias com evento, e uma semana sem nenhum virava um texto solto
    sem botão nenhum para navegar. Aqui as sete abas existem sempre, e o dia
    vazio é clicável.
  */
  const diasDaSemana = useMemo(() => {
    const porChave = new Map(dias.map((d) => [d.chave, d]));
    return diasCompletosDaSemana(semana, porChave);
  }, [dias, semana]);

  // Dia selecionado padrão: hoje, se houver na semana visível; senão o primeiro
  // dia da semana visível.
  //
  // A busca é por `diasDaSemana`, NÃO pela lista completa. Validar contra a
  // lista completa mantinha o dia da semana anterior selecionado depois de
  // navegar: ele continuava "existente", nenhuma aba ficava ativa, e a tabela
  // mostrava o dia errado. A aba visível é a única que pode estar ativa.
  useEffect(() => {
    if (diaSelecionado && diasDaSemana.some((dia) => dia.chave === diaSelecionado)) return;
    const hoje = chaveDoDia(new Date());
    /*
      A REGRA DE ESCOLHA (corrigida em 05/10/2026)
      ===========================================
      Antes as abas eram só os dias COM evento, e o primeiro com evento virava
      o selecionado. Ao mostrar os sete dias sempre, a regra precisa mudar: se
      "hoje" fosse escolhido só por ser hoje, uma segunda-feira sem evento
      nenhum mostraria tabela vazia enquanto amanhã tem a agenda inteira.

      Ordem: hoje COM evento → primeiro dia com evento → hoje.
      "Hoje" continua sendo o padrão, que é o que o operador espera; e o dia sem
      evento só entra quando não há nada melhor para mostrar.
    */
    const hojeTemEvento = diasDaSemana.some((dia) => dia.chave === hoje && dia.eventos.length > 0);
    const primeiroComEvento = diasDaSemana.find((dia) => dia.eventos.length > 0);
    const alvo = hojeTemEvento ? diasDaSemana.find((d) => d.chave === hoje) : primeiroComEvento;
    setDiaSelecionado((alvo?.chave ?? diasDaSemana[0]?.chave ?? null));
  }, [diasDaSemana, diaSelecionado]);

  /*
    A SEMANA QUE O DADO REALMENTE COBRE.
    =======================================
    O feed público entrega só a semana corrente (`ff_calendar_thisweek.json`) e o
    backend completa as semanas seguintes com horários ESTIMADOS. Antes ele não
    existia: uma semana vazia mostrava só "Sem eventos nesta semana", e o
    operador não sabia se era falta de evento ou semana fora do dado.

    Agora, quando a semana visível não tem nada, a tela diz até onde o dado
    chega — que é a diferença entre "não tem evento" e "não foi carregado".
  */
  const diasComDado = useMemo(() => dias.map((d) => d.chave).sort(), [dias]);
  const janela = useMemo(() => {
    if (!diasComDado.length) return null;
    return { de: diasComDado[0], ate: diasComDado[diasComDado.length - 1] };
  }, [diasComDado]);
  const semanaVazia = useMemo(
    () => (!!janela && !diasDaSemana.some((dia) => dia.eventos.length > 0) ? janela : null),
    [diasDaSemana, janela],
  );

  /*
    ONTEM, QUANDO O DADO TEM.
    ===========================
    Só entra no botão se existe evento naquele dia. Botão de navegação que não
    tem para onde levar é botão morto, e um "Ontem" que abre semana vazia é
    pior do que não existir.
  */
  const ontemComDado = useMemo(() => {
    const ontem = new Date();
    ontem.setDate(ontem.getDate() - 1);
    const chave = chaveDoDia(ontem);
    return diasComDado.includes(chave) ? chave : null;
  }, [diasComDado]);

  /** Troca a semana E seleciona o dia, que é o que o operador quer de fato. */
  const irParaDia = useCallback(
    (chave: string) => {
      const [ano, mes, dia] = chave.split('-').map(Number);
      if (!ano || !mes || !dia) return;
      setSemana(inicioDaSemana(new Date(ano, mes - 1, dia)));
      setDiaSelecionado(chave);
    },
    [setSemana, setDiaSelecionado],
  );

  // Só um dia da SEMANA VISÍVEL pode estar na tabela. Buscar na lista completa
// reintroduzia o dia antigo depois de navegar de semana.
  const diaAtual = diasDaSemana.find((dia) => dia.chave === diaSelecionado) ?? null;

  /*
    PAÍSES DA SEMANA VISÍVEL, com a contagem de cada um.
    ======================================================
    Gerado do que EXISTE, e nao de `PAISES_SUPORTADOS`. O feed traz moedas
    que a lista fixa nao conhece, e um pais que a lista fixa nao tem fica sem
    como ser filtrado.

    A contagem vem dos eventos do dia APOS o filtro de impacto e PAIS, mas
    ANTES do filtro de pais: se o proprio filtro zerasse a contagem, o chip
    marcado mostraria 0 e pareceria estar vazio.
  */
  const paisesDaSemana = useMemo(() => {
    const mapa = new Map<
      string,
      { codigo: string; nome: string; bandeira: string; eventos: number }
    >();
    for (const dia of diasDaSemana) {
      for (const evento of dia.eventos) {
        if (filtro.impactos.length > 0 && !filtro.impactos.includes(evento.impacto)) continue;
        const atual = mapa.get(evento.codigoPais);
        if (atual) {
          atual.eventos += 1;
        } else {
          mapa.set(evento.codigoPais, {
            codigo: evento.codigoPais,
            nome: evento.nomePais,
            bandeira: evento.bandeira,
            eventos: 1,
          });
        }
      }
    }
    // Selecionados primeiro: quem acabou de clicar em dois paises quer os dois
    // no topo, nao em ordem alfabetica longe.
    return [...mapa.values()].sort((a, b) => {
      const selA = filtro.paises.includes(a.codigo) ? 0 : 1;
      const selB = filtro.paises.includes(b.codigo) ? 0 : 1;
      if (selA !== selB) return selA - selB;
      return b.eventos - a.eventos;
    });
  }, [diasDaSemana, filtro.impactos, filtro.paises]);

  // Só o dia selecionado entra na tabela, já filtrado por país/impacto.
  const linhas = useMemo(() => {
    const doDia = diaAtual?.eventos ?? [];
    return doDia.filter((evento) => {
      if (filtro.paises.length > 0 && !filtro.paises.includes(evento.codigoPais)) return false;
      if (filtro.impactos.length > 0 && !filtro.impactos.includes(evento.impacto)) return false;
      return true;
    });
  }, [diaAtual, filtro.paises, filtro.impactos]);

  const contagensDoDia = useMemo(() => {
    const mapa = new Map<string, { total: number; altos: number; estimados: number }>();
    for (const dia of dias) {
      mapa.set(dia.chave, {
        total: dia.eventos.length,
        altos: dia.eventos.filter((e) => e.impacto === 'alto').length,
        estimados: dia.eventos.filter((e) => e.estimado).length,
      });
    }
    return mapa;
  }, [dias]);

  const moverSemana = (delta: number) => {
    const proxima = new Date(semana);
    proxima.setDate(proxima.getDate() + delta * 7);
    setSemana(proxima);
    // O dia selecionado tem que ser descartado AO VIVER, não ser revalidado
    // depois. Ele continua válido na lista completa de dias (que é de todo o
    // periodo), então o efeito que escolhe o dia via `dias` — não via
    // `diasDaSemana` — o mantém, e a tabela continua mostrando o dia da semana
    // ANTERIOR enquanto as abas mostram a nova.
    //
    // Medido em 05/10/2026: navegar para a próxima semana trocava as sete abas
    // e deixava a tabela no dia antigo, sem nenhuma aba marcada como ativa.
    setDiaSelecionado(null);
  };

  const togglePais = (codigo: string) => {
    setFiltro((prev) => ({
      ...prev,
      paises: prev.paises.includes(codigo)
        ? prev.paises.filter((p) => p !== codigo)
        : [...prev.paises, codigo],
    }));
  };

  const toggleImpacto = (impacto: ImpactLevel) => {
    setFiltro((prev) => ({
      ...prev,
      impactos: prev.impactos.includes(impacto)
        ? prev.impactos.filter((i) => i !== impacto)
        : [...prev.impactos, impacto],
    }));
  };

  const limparFiltros = () => {
    setFiltro({ paises: [], impactos: [], dataInicio: null, dataFim: null });
  };

  if (erro) {
    return (
      <div className="card compact-card cal-copilot" role="alert">
        <h3>Erro ao carregar o calendário</h3>
        <p className="hint">{erro}</p>
        <button className="btn sm ghost" type="button" onClick={refreshManual}>
          Tentar novamente
        </button>
      </div>
    );
  }

  const rotuloSemana = `${semana.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })} — ${new Date(
    semana.getTime() + 6 * 86_400_000,
  ).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: 'numeric' })}`;

  return (
    <div className="calendar-tab">
      <div className="cal-head">
        <div>
          <h2>Calendário Econômico</h2>
          <span className="cal-head-count">{totalEventos} eventos</span>
        </div>
        <div className="cal-head-actions">
          {ultimaAtualizacao && (
            <span className="muted">
              Atualizado {ultimaAtualizacao.toLocaleTimeString('pt-BR')}
            </span>
          )}
          <button
            className="btn xs ghost"
            type="button"
            onClick={refreshManual}
            disabled={carregando}
          >
            {carregando ? 'Atualizando…' : 'Atualizar'}
          </button>
        </div>
      </div>

      {/*
        FONTE DE CADA LINHA, DECLARADA
        ==============================
        A semana corrente vem do feed público e traz anterior, previsão e real.
        As semanas seguintes são horários ESTIMADOS, sem valor — porque a fonte
        (`planos/economic_calendar.py`) só sabe quando o evento acontece.

        Sem este aviso, as duas se misturam na mesma coluna e o operador trata
        estimativa como número publicado. É a mesma regra dos dados de mercado:
        backfill e estimativa têm que ser rotulados.
      */}
      {fontes && !fontes.feedDisponivel && (
        <p className="cal-fonte cal-fonte-estimada" role="status">
          Agenda da semana corrente indisponível{fontes.erro ? ` (${fontes.erro})` : ''}: abaixo só
          há horários estimados, sem valor anterior, previsão ou real.
        </p>
      )}

      {/* NAVEGAÇÃO DE SEMANA E ABAS DE DIA — o padrão do MT5 */}
      <div className="cal-semana">
        {/*
          ATALHOS DE DIA, e nao só de semana (05/10/2026).

          O dono pediu: "os dias seguintes e anteriores nao estao carregando".
          Causa medida: os 82 eventos do feed vao de **04/10 a 11/10**, e 05/10
          é uma SEGUNDA — entao a semana inicial é 05/10..11/10 e **ontem (04/10)
          fica na semana ANTERIOR**. Navegar por semana obrigava dois cliques
          para ver o dia que tinha acabado de acontecer.

          Estes dois botões vão direto ao dia, e só aparecem quando existe dado:
          botão que não tem para onde levar é botão morto.
        */}
        {ontemComDado && (
          <button
            type="button"
            className="btn xs ghost"
            onClick={() => irParaDia(ontemComDado)}
            title={`Ver os eventos de ${formatarChaveDia(ontemComDado)}`}
          >
            Ontem
          </button>
        )}
        <button
          type="button"
          className="btn xs ghost"
          onClick={() => moverSemana(-1)}
          aria-label="Semana anterior"
          title="Semana anterior"
        >
          ‹
        </button>
        <span className="cal-semana-rotulo">{rotuloSemana}</span>
        <button
          type="button"
          className="btn xs ghost"
          onClick={() => moverSemana(1)}
          aria-label="Próxima semana"
          title="Próxima semana"
        >
          ›
        </button>
        <button
          type="button"
          className="btn xs ghost"
          onClick={() => {
            setSemana(inicioDaSemana(new Date()));
            setDiaSelecionado(null);
          }}
          title="Voltar para a semana atual"
        >
          Hoje
        </button>
      </div>

      <div className="cal-dias" role="tablist" aria-label="Dias da semana">
        {/*
          As sete abas aparecem SEMPRE, mesmo sem evento. Antes só vinha o dia
          que tinha evento, e uma semana sem nenhum virava um texto sem botão
          para onde ir — era o que o dono viu como "páginas vazias".
        */}
        {diasDaSemana.map((dia) => {
          const contagem = contagensDoDia.get(dia.chave);
          const ativo = dia.chave === diaSelecionado;
          return (
            <button
              key={dia.chave}
              type="button"
              role="tab"
              aria-selected={ativo}
              className={`cal-dia${ativo ? ' is-ativo' : ''}${
                // A COR DO DIA (05/10/2026): o dono pediu "colorir". Dia com
                // evento de alto impacto ganha fundo quente — é o primeiro que o
                // olho acha na tira, sem abrir as sete abas.
                contagem && contagem.altos > 0 ? ' tem-alto' : ''
              }${dia.chave === chaveDoDia(new Date()) ? ' is-hoje' : ''}`}
              onClick={() => setDiaSelecionado(dia.chave)}
              title={`${dia.data} — ${contagem?.total ?? 0} evento(s)`}
            >
              <span className="cal-dia-relato">{dia.relato || dia.data.split(',')[0]}</span>
              <span className="cal-dia-nome">
                {dia.data.split(' de ')[1] ?? dia.data}
              </span>
              <span className="cal-dia-cont">{contagem?.total ?? 0}</span>
              {/* O ponto vermelho é o que faz o operador achar o dia do FOMC
                  sem abrir as sete abas. Sem ele, ele abre todas. */}
              {contagem && contagem.altos > 0 && (
                <span
                  className="cal-dia-alto"
                  aria-label={`${contagem.altos} evento(s) de alto impacto`}
                  title={`${contagem.altos} de alto impacto`}
                />
              )}
            </button>
          );
        })}
      </div>

      {/*
        FAIXA DE PAÍSES COM BANDEIRA (05/10/2026)
        ==========================================
        O dono pediu: "se possivel adicionar bandeiras dos paises ao lado de
        cada informacao relevante ou no topo de cada pais".

        Aqui a faixa e GERADA A PARTIR DO QUE EXISTE na semana visível, e nao de
        uma lista fixa de países. Motivo: a lista fixa (`PAISES_SUPORTADOS`)
        tem 6 entradas e o feed traz 12+ moedas — Countries que a tela nunca
        mostrou. Com lista fixa, metade dos eventos ficaria sem como ser filtrado.

        Cada botão mostra a bandeira, a moeda e quantos eventos há NAQUEL PAÍS
        NA SEMANA. O número é o que diz se vale clicar: um chip de uma bandeira
        sem evento é ruído.

        A faixa também FILTRA: clicar marca o país, clicar de novo desmarca. E
        os países marcados por último aparecem primeiro — quem filtra por dois
        países quer os dois, não uma lista alfabética.
      */}
      {paisesDaSemana.length > 0 && (
        <div className="cal-paises" role="group" aria-label="Filtrar por país">
          {paisesDaSemana.map((pais) => {
            const marcado = filtro.paises.includes(pais.codigo);
            return (
              <button
                key={pais.codigo}
                type="button"
                onClick={() => togglePais(pais.codigo)}
                className={`cal-chip cal-pais-chip${marcado ? ' on' : ''}`}
                aria-pressed={marcado}
                title={`${pais.nome} — ${pais.eventos} evento(s) nesta semana`}
              >
                <span className="cal-bandeira">{pais.codigo}</span>
                <span className="cal-pais-nome">{pais.nome}</span>
                <span className="cal-pais-sigla">{pais.codigo}</span>
                <span className="cal-pais-num">{pais.eventos}</span>
              </button>
            );
          })}
        </div>
      )}

      {/* FILTROS: importance primeiro, porque e o que decide a operacao. */}
      <div className="cal-filters">
        <div className="cal-filter-row">
          <span className="cal-filter-label">Importância</span>
          {(['alto', 'medio', 'baixo'] as ImpactLevel[]).map((impacto) => (
            <button
              key={impacto}
              type="button"
              onClick={() => toggleImpacto(impacto)}
              className={`cal-chip ${filtro.impactos.includes(impacto) ? 'on' : ''}`}
            >
              <Estrelas impacto={impacto} />
              {LABELS_IMPACTO[impacto]}
            </button>
          ))}
          {(filtro.paises.length > 0 || filtro.impactos.length > 0) && (
            <button className="cal-chip cal-chip-clear" type="button" onClick={limparFiltros}>
              Limpar
            </button>
          )}
        </div>
      </div>

      {/* TABELA DO DIA — colunas do MT5, na ordem do MT5 */}
      <div className="cal-columns">
        <span className="num">Hora</span>
        <span>Moeda</span>
        <span>Evento</span>
        <span className="cal-col-import">Importância</span>
        <span className="num">Anterior</span>
        <span className="num">Previsão</span>
        <span className="num">Real</span>
      </div>

      <div className="cal-body">
        {carregando && todosEventos.length === 0 ? (
          <div className="cal-state">Carregando eventos…</div>
        ) : linhas.length === 0 ? (
          <div className="cal-state">
            {semanaVazia ? (
              <>
                Nenhum evento nesta semana. O dado carregado vai de{' '}
                {formatarChaveDia(semanaVazia.de)} até {formatarChaveDia(semanaVazia.ate)}.
              </>
            ) : (
              (diaAtual
                ? 'Nenhum evento neste dia com os filtros atuais.'
                : 'Nenhum evento encontrado.')
            )}
          </div>
        ) : (
          linhas.map((evento) => (
<button
          key={evento.id}
          type="button"
className={`cal-row${evento.horario.getTime() < Date.now() ? ' passado' : ''}${
                evento.impacto === 'alto' ? ' alto' : evento.impacto === 'medio' ? ' medio' : ''
              }${aberto?.id === evento.id ? ' is-aberto' : ''}`}
          onClick={() => setAberto(aberto?.id === evento.id ? null : evento)}
          title={
            evento.traduzido
              ? `${evento.titulo} — ${evento.nomePais}. Clique para o detalhe.`
              : `${evento.titulo} (${evento.tituloOriginal}) — ${evento.nomePais}. Sem tradução no dicionário. Clique para o detalhe.`
          }
        >
              <span className="num cal-row-time">
                {/*
                  Data inválida NÃO vira "Invalid Date" na tela, e NEM a hora
                  atual.

                  A hora atual já foi o defeito: 50 linhas com 19:13, que era a
                  hora em que a tela abriu. Trocar por `new Date()` aqui
                  devolveria o mesmo defeito, agora escondido atrás de um
                  travessão.

                  Sem horário, a linha mostra travessão e o `title` diz que o
                  produtor não mandou a hora. Dado ausente é ausente.
                */}
                {semHora(evento) ? (
                  <span title="O produtor do evento não informou o horário">
                    —
                  </span>
                ) : (
                  evento.horario.toLocaleTimeString('pt-BR', {
                    hour: '2-digit',
                    minute: '2-digit',
                  })
                )}
              </span>
              <span className="cal-row-pais" title={evento.nomePais}>
                <span className="cal-bandeira">{evento.codigoPais}</span>
                <span className="cal-pais-nome">{evento.nomePais}</span>
                <span className="cal-pais-sigla">{evento.codigoPais}</span>
              </span>
              <span className="cal-row-title">
                <span className="cal-bandeira cal-row-bandeira" aria-hidden="true">
                  {evento.bandeira}
                </span>
                {/*
                  TÍTULO TRADUZIDO, com duas marcações que o operador precisa:

                  - `en`: o dicionário não cobriu este evento e a linha continua
                    em inglês. Sem esta marca o operador leria "Housing Starts"
                    como se fosse português e não saberia que pode estar
                    perdendo nuance — a tradução é por palavra, e palavra
                    traduzida errada é pior que inglês.
                  - `cat`: a categoria (Juros, Inflação, Emprego, Atividade,
                    Energia). Serve de busca visual: quem opera ouro olha
                    "Juros" e "Inflação" antes de ler o nome do evento.
                */}
                {evento.categoria && <span className="cal-cat">{evento.categoria}</span>}
                <strong>{evento.titulo}</strong>
                {!evento.traduzido && (
                  <span
                    className="cal-row-tag cal-row-en"
                    title={`O feed publica este evento em inglês: "${evento.tituloOriginal}". A tradução é por palavra, então o título acima é aproximado.`}
                  >
                    en
                  </span>
                )}
                {evento.estimado && (
                  <span className="cal-row-tag" title="Horário estimado por padrão de calendário; sem valor publicado">
                    estimado
                  </span>
                )}
              </span>
              <span className="cal-col-import">
                <Estrelas impacto={evento.impacto} />
              </span>
              <Valor
                valor={evento.anterior}
                ausente={motivoAusente(evento, 'Anterior')}
              />
              <Valor
                valor={evento.consenso}
                ausente={motivoAusente(evento, 'Previsão')}
              />
              <Valor valor={evento.real} forte ausente={motivoReal(evento)} />
            </button>
          ))
        )}
      </div>

      {/* DETALHE — o MT5 abre uma janela com o evento. Aqui abre abaixo da
          linha: mesma informação, sem cobrir a tabela que o operador compara. */}
      {aberto && (
        <div className="cal-detalhe" role="region" aria-label={`Detalhe: ${aberto.titulo}`}>
          <div className="cal-detalhe-topo">
            <span className="cal-detalhe-bandeira">{aberto.codigoPais}</span>
            <div className="cal-detalhe-ident">
              <strong>{aberto.titulo}</strong>
              {/*
                O título em inglês fica visível quando a tradução foi por
                palavra. O operador que precisa do nome exato — para comparar
                com o calendário da XM ou do MT5 — precisa conseguir ler o
                original, e ele não pode estar escondido atrás de um tooltip.
              */}
              {!aberto.traduzido ? (
                <small className="cal-detalhe-en">
                  Sem tradução no dicionário. No feed: “{aberto.tituloOriginal}”.
                </small>
              ) : (
                aberto.tituloOriginal !== aberto.titulo && (
                  <small className="cal-detalhe-en">No feed: “{aberto.tituloOriginal}”</small>
                )
              )}
            </div>
            <button
              type="button"
              className="btn xs ghost cal-detalhe-fechar"
              onClick={() => setAberto(null)}
              aria-label="Fechar detalhe"
            >
              ×
            </button>
          </div>

          {/*
            A GRADE é `grid-template-columns`, com as MESMAS duas colunas em
            cada linha. Antes o rótulo e o valor viviam em `<em>` e `<span>`
            dentro de um bloco comum: cada célula tinha a largura do próprio
            conteúdo, e o "Anterior" de uma linha não caía em cima do "Anterior"
            da linha de baixo. Duas colunas fixas resolvem: o valor começa
            sempre na mesma coordenada, e o operador compara números em coluna.
          */}
          <dl className="cal-detalhe-grade">
            <div>
              <dt>País</dt>
              <dd>
                {aberto.nomePais} · {aberto.codigoPais}
              </dd>
            </div>
            <div>
              <dt>Horário</dt>
              <dd>{aberto.horario.toLocaleString('pt-BR')}</dd>
            </div>
            <div>
              <dt>Importância</dt>
              <dd>
                <Estrelas impacto={aberto.impacto} /> {LABELS_IMPACTO[aberto.impacto]}
              </dd>
            </div>
            <div>
              <dt>Anterior</dt>
              <dd>
                <Valor valor={aberto.anterior} ausente={motivoAusente(aberto, 'Anterior')} />
              </dd>
            </div>
            <div>
              <dt>Previsão</dt>
              <dd>
                <Valor valor={aberto.consenso} />
              </dd>
            </div>
            <div>
              <dt>Real</dt>
              <dd>
                <Valor valor={aberto.real} forte />
              </dd>
            </div>
            <div>
              <dt>Fonte</dt>
              <dd>{aberto.estimado ? 'horário estimado' : 'dado publicado'}</dd>
            </div>
          </dl>

          {/*
            `nota` é a descrição do evento no feed público: texto editorial de
            terceiro, e por isso renderizado como TEXTO — nunca como HTML.
            Este bloco estava no comentário mas não existia no JSX: o campo era
            mapeado no hook e descartado, então a descrição nunca aparecia.
          */}
          {aberto.nota && <p className="cal-detalhe-nota">{aberto.nota}</p>}
        </div>
      )}
    </div>
  );
}

/**
 * O evento tem horário usável?
 *
 * Um `Date` com `NaN` — data que o produtor mandou em formato ilegível — é
 * ausência de dado. `toLocaleTimeString` nesse caso escreve "Invalid Date" na
 * tela, e o operador lê aquilo como horário.
 */
function semHora(evento: EconomicEvent): boolean {
  return !Number.isFinite(evento.horario?.getTime?.());
}

/** `yyyy-mm-dd` → `dd/mm/aaaa`, para o texto que diz até onde vai o dado. */
function formatarChaveDia(chave: string): string {
  const p = chave.split('-');
  return p.length === 3 ? `${p[2]}/${p[1]}/${p[0]}` : chave;
}

/** A chave do dia cai dentro da semana visível? */
function estaNaSemana(chave: string, semana: Date): boolean {
  const [ano, mes, dia] = chave.split('-').map(Number);
  const alvo = new Date(ano, mes - 1, dia).getTime();
  const inicio = inicioDaSemana(semana).getTime();
  return alvo >= inicio && alvo < inicio + 7 * 86_400_000;
}

export default EconomicCalendarTab;