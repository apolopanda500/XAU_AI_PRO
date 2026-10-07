/**
 * Hook de dados do calendário econômico — XAU AI PRO.
 * Fonte de verdade: GET /api/economic/calendar (agenda real do app/economic_calendar.py).
 * Sem mock: gateway offline = lista vazia + erro explícito.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiBase } from '../lib/api';
import { EconomicEvent, FiltroCalendario, EstadoCarregamento } from '../types';
import type { ImpactLevel } from '../types';
import { categoriaEvento, eventoTraduzido, traduzirEvento } from '../components/tabs/traduzirEvento';
import { zonaAtual } from './useFuso';

const API = `${apiBase()}`;
/** Chave para cache no localStorage */
const CACHE_KEY = 'xau_ai_pro_calendario_cache';
/** Tempo de validade do cache: 5 minutos */
const CACHE_TTL_MS = 5 * 60 * 1000;

type ApiEvent = {
  title?: string;
  currency?: string;
  impact?: string;
  note?: string;
  when_utc?: string;
  when?: string;
  gold_relevant?: boolean;
  /**
   * Campo novo (05/10/2026). Antes estas três colunas da tela eram sempre
   * `--`, porque a fonte era a tabela local — que sabe QUANDO o evento
   * acontece e nada mais. Agora a semana corrente vem do feed público.
   */
  previous?: string | null;
  forecast?: string | null;
  actual?: string | null;
  /** true quando o horário é estimativa de padrão de calendário. */
  estimado?: boolean;
  bandeira?: string;
};

type ApiFontes = {
  reais?: number;
  estimados?: number;
  feed_disponivel?: boolean;
  erro?: string;
};

/*
  MOEDA -> PAÍS
  ============
  MEDIDO no feed público em 05/10/2026 (`ff_calendar_thisweek.json`, 82
  eventos): as moedas que aparecem são ALL, AUD, CNY, JPY, EUR, NZD, GBP, CAD,
  USD, CHF.

  A versão anterior tinha 8 entradas e NÃO tinha NZD nem ALL. Consequência
  medida: os eventos da Nova Zelândia caíam no fallback — bandeira branca 🏳 e
  nome "NZD" no lugar do país. O dono pediu "bandeiras dos paises em cada
  pais", e meia dúzia de eventos ficava sem bandeira nenhuma.

  Por que a lista existe e mesmo assim não é " presumir país": é o
  DECODIFICAR de um código que o feed manda. O conjunto vem do que o feed
  traz; para moeda fora daqui o código vira o próprio nome, marcado como
  desconhecido em vez de adivinhado.
*/
const CURRENCY_TO_COUNTRY: Record<string, { code: string; name: string; flag: string }> = {
  USD: { code: 'US', name: 'Estados Unidos', flag: '🇺🇸' },
  EUR: { code: 'EU', name: 'Zona do Euro', flag: '🇪🇺' },
  GBP: { code: 'GB', name: 'Reino Unido', flag: '🇬🇧' },
  JPY: { code: 'JP', name: 'Japão', flag: '🇯🇵' },
  AUD: { code: 'AU', name: 'Austrália', flag: '🇦🇺' },
  CAD: { code: 'CA', name: 'Canadá', flag: '🇨🇦' },
  BRL: { code: 'BR', name: 'Brasil', flag: '🇧🇷' },
  CNY: { code: 'CN', name: 'China', flag: '🇨🇳' },
  NZD: { code: 'NZ', name: 'Nova Zelândia', flag: '🇳🇿' },
  CHF: { code: 'CH', name: 'Suíça', flag: '🇨🇭' },
  MXN: { code: 'MX', name: 'México', flag: '🇲🇽' },
  ZAR: { code: 'ZA', name: 'África do Sul', flag: '🇿🇦' },
  INR: { code: 'IN', name: 'Índia', flag: '🇮🇳' },
  KRW: { code: 'KR', name: 'Coreia do Sul', flag: '🇰🇷' },
  SGD: { code: 'SG', name: 'Singapura', flag: '🇸🇬' },
  HKD: { code: 'HK', name: 'Hong Kong', flag: '🇭🇰' },
  TRY: { code: 'TR', name: 'Turquia', flag: '🇹🇷' },
  // O feed usa "ALL" para evento que vale para todos os mercados (OPEC, por
  // exemplo). Não é um país: o nome diz isso, em vez de fingir que é um.
  ALL: { code: 'ALL', name: 'Todos os mercados', flag: '🌐' },
};

function impactoDe(valor?: string): ImpactLevel {
  const v = (valor ?? '').toLowerCase();
  if (v === 'alto' || v === 'high') return 'alto';
  if (v === 'baixo' || v === 'low') return 'baixo';
  return 'medio';
}

/**
 * Converte o payload real do gateway em EconomicEvent[].
 * `when_utc` é hora UTC real; `date` local é derivada dela.
 *
 * Os campos `previous`/`forecast`/`actual` vêm como `null` quando o evento não
 * os traz — evento de estimativa não tem valor nenhum. Passar `""` adiante
 * colocaria célula vazia ao lado de célula com número, e o operador não saberia
 * qual das duas é ausência de verdade.
 */
function processarEventosApi(itens: ApiEvent[]): EconomicEvent[] {
  const agora = new Date();
  return itens.map((item, i) => {
/*
    `when_utc` CHEGA EM DOIS FORMATOS, e o código antigo assumia UM. (05/10/2026)

    MEDIDO nos dois producer, na mesma máquina:
      - agenda estimada (`planos/economic_calendar`): `'2026-10-06T12:00'`
        —— horário local, SEM fuso;
      - feed público (`economic_calendar_publica`): `'2026-10-04T09:15+00:00'`
        —— UTC, COM deslocamento.

    O código fazia `new Date(`${when_utc}Z`)` para "converter para UTC". Com o
    feed público isso vira `'2026-10-04T09:15+00:00Z'` — data **inválida** — e
    caía no `|| new Date()`.

    O resultado na tela foi o pior possível e completamente silencioso: **os 50
    eventos do dia com o mesmo horário**, 19:13, que é a hora em que a tela foi
    aberta. Nenhum erro, nenhuma exceção, nenhuma linha vazia: só a hora do
    "agora" repetida.

    Agora a decisão é por FORMATO, não por suposição:
      - com deslocamento (`+hh:mm`, `-hh:mm`) ou com `Z` → parseia direto, que
        é o que o produtor quis dizer;
      - sem nada disso → é local, e o `Z` é acrescentado como antes.

    Um campo que chega em dois formatos é um defeito de contrato entre os dois
    lados. Aqui ele é tratado dos dois lados, e o teste trava os dois.
  */
  const quandoUtc = (bruto: string): Date => {
    const texto = bruto.trim();
    const temFuso = /(?:[+-]\d{2}:?\d{2}|Z)$/i.test(texto);
    const d = new Date(temFuso ? texto : `${texto}Z`);
    if (!Number.isNaN(d.getTime())) return d;
    // Data ilegível NAO vira "agora": vira evento sem horário, marcado como
    // tal. Trocar por `new Date()` é inventar dado — foi o que produziu o
    // 19:13 em toda a tabela.
    return new Date(Number.NaN);
  };
  const utc = item.when_utc ? quandoUtc(item.when_utc) : new Date(Number.NaN);
  const horario = utc;
    const moeda = (item.currency ?? '').toUpperCase();
    const pais = CURRENCY_TO_COUNTRY[moeda] ?? {
      code: moeda || '--',
      name: moeda || 'Desconhecido',
      flag: '\u{1F3F3}',
    };
    const texto = (v: string | null | undefined): string | null => {
      const t = (v ?? '').trim();
      return t ? t : null;
    };
    const tituloCru = (item.title ?? '').trim() || 'Evento';
    return {
      id: `${item.when_utc ?? agora.toISOString()}-${i}`,
      horario,
      codigoPais: pais.code,
      nomePais: pais.name,
      bandeira: item.bandeira ?? pais.flag,
      impacto: impactoDe(item.impact),
      // Traduzido AQUI, e não no gateway: o app já tem o nome do país em
      // português nesta mesma tabela, e uma tradução por consumidor garante
      // que a tela fale uma língua só. O título original fica guardado, porque
      // evento não reconhecido precisa continuar legível.
      titulo: traduzirEvento(tituloCru),
      tituloOriginal: tituloCru,
      traduzido: eventoTraduzido(tituloCru),
      categoria: categoriaEvento(tituloCru),
      // `note` é a descrição do evento no feed público. É texto editorial de
      // terceiro: entra como TEXTO, nunca como HTML.
      nota: (item.note ?? '').trim() || null,
      anterior: texto(item.previous),
      consenso: texto(item.forecast),
      real: texto(item.actual),
      divulgado: horario.getTime() <= Date.now(),
      // Rótulo de procedência. `true` = horário estimado, sem valor publicado.
      estimado: item.estimado === true,
    };
  });
}

/** Cache local: aceita apenas eventos recentes do gateway. */
function carregarDoCache(): EconomicEvent[] | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const { ts, eventos } = JSON.parse(raw) as {
      ts: number;
      eventos: Array<Omit<EconomicEvent, 'horario'> & { horario: string }>;
    };
    if (Date.now() - ts > CACHE_TTL_MS) return null;
    return eventos.map((e) => ({ ...e, horario: new Date(e.horario) }));
  } catch {
    return null;
  }
}

function salvarNoCache(eventos: EconomicEvent[]): void {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ ts: Date.now(), eventos }));
  } catch {
    // Cache é opcional; falha em silêncio.
  }
}

export function useEconomicData(
  filtro: FiltroCalendario,
  intervaloRefreshMs: number = CACHE_TTL_MS,
) {
  const [estado, setEstado] = useState<EstadoCarregamento<EconomicEvent[]>>({
    dados: null,
    carregando: true,
    erro: null,
    ultimaAtualizacao: null,
  });
  /**
   * De onde veio cada evento, e se o feed público respondeu.
   *
   * A tela usa isto para avisar que a semana corrente é estimativa — não é
   * detalhe: sem o aviso, o operador trata horário estimado como número
   * publicado, que é a mesma coisa que usar backfill como dado real.
   */
  const [fontes, setFontes] = useState<ApiFontes | null>(null);

  const montadoRef = useRef(true);
  const intervaloRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const buscarDados = useCallback(async (): Promise<void> => {
    const doCache = carregarDoCache();
    if (doCache && montadoRef.current) {
      setEstado((prev) => ({
        ...prev,
        dados: doCache,
        carregando: false,
        ultimaAtualizacao: new Date(),
      }));
    }

    try {
      /*
        `tz` era `BRT` FIXO, e o servidor aceitava qualquer coisa: fuso
        desconhecido caia em UTC sem erro (`_TZ_OFFSETS.get(tz, 0)`), devolvendo
        agenda 3 horas errada e nenhuma pista. MEDIDO 05/10/2026: o servidor
        agora resolve zona IANA e tem `tz_desconhecida()` para recusar com
        motivo. O cliente manda a zona que o dono escolheu na tela.
      */
      // `limit` MEDIDO, e nao chutado (05/10/2026).
      //
      // A rota devolve `combinado["events"][:limit]`, e a COMBINAÇAO tem 111
      // eventos em 14 dias: 82 do feed publico + 29 ESTIMADOS. Os estimados
      // (semana seguinte) entram no FIM da lista combinada, porque sao
      // acrescentados depois dos reais.
      //
      // Com `limit=50` a tela recebia so os 50 primeiros: os dias da semana
      // corrente, e a semana seguinte INTEIRA ficava fora. Era por isso que as
      // abas de semana vinham vazias — e nao era "faltando evento no dia",
      // era o CORTE, do lado do cliente.
      //
      // 200 e o teto que a propria rota aplica (`min(limit, 200)`), e cabe a
      // janela de 14 dias com folga. Um numero pequeno aqui nao economiza nada:
      // esconde dados que a rota ja pagou para buscar.
      const resposta = await fetch(`${API}/api/economic/calendar?limit=200&days=14&tz=${zonaAtual()}`, {
        method: 'GET',
        signal: AbortSignal.timeout(8000),
      });
      const dadosApi = (await resposta.json()) as {
        events?: ApiEvent[];
        error?: string;
        fontes?: ApiFontes;
      };

      if (resposta.ok && dadosApi.events?.length) {
        const eventosProcessados = processarEventosApi(dadosApi.events);
        if (montadoRef.current) {
          salvarNoCache(eventosProcessados);
          setFontes(dadosApi.fontes ?? null);
          setEstado({
            dados: eventosProcessados,
            carregando: false,
            erro: null,
            ultimaAtualizacao: new Date(),
          });
        }
        return;
      }
      throw new Error(dadosApi.error ?? 'Gateway sem eventos');
    } catch (e) {
      if (montadoRef.current) {
        setEstado({
          dados: doCache ?? [],
          carregando: false,
          erro: `Calendário indisponível: ${e instanceof Error ? e.message : 'gateway offline'}`,
          ultimaAtualizacao: new Date(),
        });
      }
    }
  }, []);

  const eventosFiltrados = estado.dados?.filter((evento) => {
    if (filtro.paises.length > 0 && !filtro.paises.includes(evento.codigoPais)) {
      return false;
    }
    if (filtro.impactos.length > 0 && !filtro.impactos.includes(evento.impacto)) {
      return false;
    }
    if (filtro.dataInicio && evento.horario < filtro.dataInicio) {
      return false;
    }
    if (filtro.dataFim) {
      const fimDoDia = new Date(filtro.dataFim);
      fimDoDia.setHours(23, 59, 59, 999);
      if (evento.horario > fimDoDia) {
        return false;
      }
    }
    return true;
  });

  const proximoEventoAlto = estado.dados
    ?.filter((e) => e.impacto === 'alto' && e.horario > new Date() && !e.divulgado)
    .sort((a, b) => a.horario.getTime() - b.horario.getTime())[0];

  useEffect(() => {
    montadoRef.current = true;
    buscarDados();
    intervaloRef.current = setInterval(buscarDados, intervaloRefreshMs);
    return () => {
      montadoRef.current = false;
      if (intervaloRef.current) {
        clearInterval(intervaloRef.current);
      }
    };
  }, [buscarDados, intervaloRefreshMs]);

  const refreshManual = useCallback(() => {
    setEstado((prev) => ({ ...prev, carregando: true }));
    buscarDados();
  }, [buscarDados]);

  return {
    eventos: eventosFiltrados ?? [],
    carregando: estado.carregando,
    erro: estado.erro,
    ultimaAtualizacao: estado.ultimaAtualizacao,
    proximoEventoAlto,
    refreshManual,
    totalEventos: estado.dados?.length ?? 0,
    /** Procedência dos eventos, para a tela rotular estimativa. */
    fontes: fontes
      ? {
          reais: fontes.reais ?? 0,
          estimados: fontes.estimados ?? 0,
          feedDisponivel: fontes.feed_disponivel === true,
          erro: fontes.erro ?? '',
        }
      : null,
  };
}

export default useEconomicData;
