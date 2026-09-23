/**
 * Hook de dados do calendário econômico — XAU AI PRO.
 * Fonte de verdade: GET /api/economic/calendar (agenda real do app/economic_calendar.py).
 * Sem mock: gateway offline = lista vazia + erro explícito.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiBase } from '../lib/api';
import {
  EconomicEvent,
  FiltroCalendario,
  EstadoCarregamento,
} from '../types';
import type { ImpactLevel } from '../types';

const API = `${apiBase()}`;
/** Chave para cache no localStorage */
const CACHE_KEY = 'xau_ai_pro_calendario_cache';
/** Tempo de validade do cache: 5 minutos */
const CACHE_TTL_MS = 5 * 60 * 1000;

type ApiEvent = {
  title?: string; currency?: string; impact?: string;
  note?: string; when_utc?: string; when?: string; gold_relevant?: boolean;
};

const CURRENCY_TO_COUNTRY: Record<string, { code: string; name: string; flag: string }> = {
  USD: { code: 'US', name: 'Estados Unidos', flag: '🇺🇸' },
  EUR: { code: 'EU', name: 'União Europeia', flag: '🇪🇺' },
  GBP: { code: 'GB', name: 'Reino Unido', flag: '🇬🇧' },
  JPY: { code: 'JP', name: 'Japão', flag: '🇯🇵' },
  AUD: { code: 'AU', name: 'Austrália', flag: '🇦🇺' },
  CAD: { code: 'CA', name: 'Canadá', flag: '🇨🇦' },
  BRL: { code: 'BR', name: 'Brasil', flag: '🇧🇷' },
  CNY: { code: 'CN', name: 'China', flag: '🇨🇳' },
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
 */
function processarEventosApi(itens: ApiEvent[]): EconomicEvent[] {
  const agora = new Date();
  return itens.map((item, i) => {
    const utc = item.when_utc ? new Date(`${item.when_utc}Z`) : new Date();
    const horario = Number.isNaN(utc.getTime()) ? new Date() : utc;
    const pais = CURRENCY_TO_COUNTRY[(item.currency ?? '').toUpperCase()] ??
      { code: item.currency ?? '--', name: item.currency ?? 'Desconhecido', flag: '🏳️' };
    return {
      id: `${item.when_utc ?? agora.toISOString()}-${i}`,
      horario,
      codigoPais: pais.code,
      nomePais: pais.name,
      bandeira: pais.flag,
      impacto: impactoDe(item.impact),
      titulo: item.title ?? 'Evento',
      anterior: null,
      consenso: null,
      real: null,
      divulgado: horario.getTime() <= Date.now(),
    };
  });
}

/** Cache local: aceita apenas eventos recentes do gateway. */
function carregarDoCache(): EconomicEvent[] | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const { ts, eventos } = JSON.parse(raw) as { ts: number; eventos: Array<Omit<EconomicEvent, 'horario'> & { horario: string }> };
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
  intervaloRefreshMs: number = CACHE_TTL_MS
) {
  const [estado, setEstado] = useState<EstadoCarregamento<EconomicEvent[]>>({
    dados: null,
    carregando: true,
    erro: null,
    ultimaAtualizacao: null,
  });

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
      const resposta = await fetch(
        `${API}/api/economic/calendar?limit=50&days=14&tz=BRT`,
        { method: 'GET', signal: AbortSignal.timeout(8000) }
      );
      const dadosApi = (await resposta.json()) as { events?: ApiEvent[]; error?: string };

      if (resposta.ok && dadosApi.events?.length) {
        const eventosProcessados = processarEventosApi(dadosApi.events);
        if (montadoRef.current) {
          salvarNoCache(eventosProcessados);
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
  };
}

export default useEconomicData;
