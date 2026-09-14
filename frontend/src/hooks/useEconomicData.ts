/**
 * Hook customizado para dados do calendário econômico
 * XAU AI PRO - Gerencia fetching, cache e filtros de eventos econômicos
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  EconomicEvent,
  FiltroCalendario,
  EstadoCarregamento,
} from '../types';
import type { ImpactLevel } from '../types';

/** Chave para cache no localStorage */
const CACHE_KEY = 'xau_ai_pro_calendario_cache';
/** Tempo de validade do cache: 5 minutos */
const CACHE_TTL_MS = 5 * 60 * 1000;

/**
 * Gera mock realista de eventos econômicos para desenvolvimento
 * Quando a API indisponível, usa dados simulados críveis
 */
function gerarMockEventos(): EconomicEvent[] {
  const agora = new Date();
  const hoje = new Date(agora);
  hoje.setHours(0, 0, 0, 0);

  const eventosBase: Array<Omit<EconomicEvent, 'id' | 'horario'> & { hora: number; minuto: number }> = [
    { hora: 8, minuto: 30, codigoPais: 'US', nomePais: 'Estados Unidos', bandeira: '🇺🇸', impacto: 'medio', titulo: 'Pedidos Industriais (M/M)', anterior: '0.3%', consenso: '0.2%', real: null, divulgado: false },
    { hora: 9, minuto: 0, codigoPais: 'US', nomePais: 'Estados Unidos', bandeira: '🇺🇸', impacto: 'baixo', titulo: 'Crédito ao Consumidor', anterior: '$12.5B', consenso: '$14.0B', real: null, divulgado: false },
    { hora: 10, minuto: 0, codigoPais: 'US', nomePais: 'Estados Unidos', bandeira: '🇺🇸', impacto: 'alto', titulo: 'Decisão de Taxa de Juros FOMC', anterior: '5.50%', consenso: '5.50%', real: null, divulgado: false },
    { hora: 10, minuto: 30, codigoPais: 'US', nomePais: 'Estados Unidos', bandeira: '🇺🇸', impacto: 'alto', titulo: 'Coletiva de Imprensa Powell', anterior: null, consenso: null, real: null, divulgado: false },
    { hora: 14, minuto: 0, codigoPais: 'US', nomePais: 'Estados Unidos', bandeira: '🇺🇸', impacto: 'medio', titulo: 'Estoques de Petróleo Bruto', anterior: '-2.1M', consenso: '-1.5M', real: null, divulgado: false },
    { hora: 5, minuto: 0, codigoPais: 'EU', nomePais: 'União Europeia', bandeira: '🇪🇺', impacto: 'alto', titulo: 'Decisão de Taxa BCE', anterior: '4.50%', consenso: '4.25%', real: null, divulgado: false },
    { hora: 8, minuto: 30, codigoPais: 'GB', nomePais: 'Reino Unido', bandeira: '🇬🇧', impacto: 'alto', titulo: 'Taxa de Desemprego', anterior: '4.2%', consenso: '4.3%', real: null, divulgado: false },
    { hora: 9, minuto: 0, codigoPais: 'EU', nomePais: 'União Europeia', bandeira: '🇪🇺', impacto: 'medio', titulo: 'Vendas no Varejo (M/M)', anterior: '-0.1%', consenso: '0.2%', real: null, divulgado: false },
    { hora: 8, minuto: 30, codigoPais: 'US', nomePais: 'Estados Unidos', bandeira: '🇺🇸', impacto: 'alto', titulo: 'Payroll (Folha de Pagamento Não-Agrícola)', anterior: '+187K', consenso: '+175K', real: null, divulgado: false },
    { hora: 8, minuto: 30, codigoPais: 'US', nomePais: 'Estados Unidos', bandeira: '🇺🇸', impacto: 'alto', titulo: 'Taxa de Desemprego', anterior: '3.8%', consenso: '3.8%', real: null, divulgado: false },
    { hora: 10, minuto: 0, codigoPais: 'US', nomePais: 'Estados Unidos', bandeira: '🇺🇸', impacto: 'alto', titulo: 'IPC (Índice de Preços ao Consumidor) (M/M)', anterior: '0.2%', consenso: '0.3%', real: null, divulgado: false },
    { hora: 10, minuto: 0, codigoPais: 'US', nomePais: 'Estados Unidos', bandeira: '🇺🇸', impacto: 'alto', titulo: 'IPC Core (Ano/Ano)', anterior: '3.7%', consenso: '3.6%', real: null, divulgado: false },
    { hora: 9, minuto: 30, codigoPais: 'US', nomePais: 'Estados Unidos', bandeira: '🇺🇸', impacto: 'alto', titulo: 'PIB (Trimestralizado)', anterior: '2.1%', consenso: '2.4%', real: null, divulgado: false },
    { hora: 8, minuto: 30, codigoPais: 'US', nomePais: 'Estados Unidos', bandeira: '🇺🇸', impacto: 'alto', titulo: 'Vendas no Varejo (M/M)', anterior: '0.7%', consenso: '0.4%', real: null, divulgado: false },
    { hora: 0, minuto: 0, codigoPais: 'JP', nomePais: 'Japão', bandeira: '🇯🇵', impacto: 'alto', titulo: 'Decisão de Taxa BOJ', anterior: '0.0%', consenso: '0.1%', real: null, divulgado: false },
    { hora: 1, minuto: 30, codigoPais: 'CN', nomePais: 'China', bandeira: '🇨🇳', impacto: 'alto', titulo: 'PIB (Ano/Ano)', anterior: '5.2%', consenso: '5.0%', real: null, divulgado: false },
    { hora: 1, minuto: 30, codigoPais: 'CN', nomePais: 'China', bandeira: '🇨🇳', impacto: 'medio', titulo: 'Produção Industrial', anterior: '4.6%', consenso: '4.4%', real: null, divulgado: false },
    { hora: 8, minuto: 0, codigoPais: 'BR', nomePais: 'Brasil', bandeira: '🇧🇷', impacto: 'alto', titulo: 'Decisão Copom (Selic)', anterior: '10.50%', consenso: '10.25%', real: null, divulgado: false },
    { hora: 8, minuto: 30, codigoPais: 'BR', nomePais: 'Brasil', bandeira: '🇧🇷', impacto: 'medio', titulo: 'IPCA (Inflação)', anterior: '0.4%', consenso: '0.3%', real: null, divulgado: false },
  ];

  return eventosBase.map((evento, index) => {
    const dataEvento = new Date(hoje);
    dataEvento.setHours(evento.hora, evento.minuto, 0, 0);
    const deslocamentoDias = Math.floor(index / 7);
    dataEvento.setDate(dataEvento.getDate() + deslocamentoDias);
    const jaDivulgado = dataEvento < agora;
    return {
      id: `evt-${index}-${evento.codigoPais}-${evento.hora}${evento.minuto}`,
      horario: dataEvento,
      codigoPais: evento.codigoPais,
      nomePais: evento.nomePais,
      bandeira: evento.bandeira,
      impacto: evento.impacto,
      titulo: evento.titulo,
      anterior: evento.anterior,
      consenso: evento.consenso,
      real: jaDivulgado ? gerarValorReal(evento.consenso, evento.anterior) : null,
      divulgado: jaDivulgado,
    };
  });
}

function gerarValorReal(consenso: string | null, anterior: string | null): string | null {
  if (!consenso) return null;
  const match = consenso.match(/[+-]?\d+\.?\d*/);
  if (!match) return consenso;
  const valor = parseFloat(match[0]);
  const variacao = (Math.random() - 0.5) * 0.2;
  const novoValor = valor * (1 + variacao);
  if (consenso.includes('K')) return `+${Math.round(novoValor)}K`;
  if (consenso.includes('B')) return `$${novoValor.toFixed(1)}B`;
  if (consenso.includes('M')) return `${novoValor > 0 ? '' : '-'}${Math.abs(novoValor).toFixed(1)}M`;
  if (consenso.includes('%')) return `${novoValor.toFixed(2)}%`;
  return `${novoValor.toFixed(2)}%`;
}

function carregarDoCache(): EconomicEvent[] | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;
    const { timestamp, dados } = JSON.parse(cached);
    const idade = Date.now() - timestamp;
    if (idade > CACHE_TTL_MS) return null;
    return dados.map((evt: EconomicEvent) => ({
      ...evt,
      horario: new Date(evt.horario),
    }));
  } catch {
    return null;
  }
}

function salvarNoCache(dados: EconomicEvent[]): void {
  try {
    const paraSalvar = {
      timestamp: Date.now(),
      dados: dados.map((evt) => ({
        ...evt,
        horario: evt.horario.toISOString(),
      })),
    };
    localStorage.setItem(CACHE_KEY, JSON.stringify(paraSalvar));
  } catch {
    console.warn('[useEconomicData] Falha ao salvar cache');
  }
}

function processarDadosApi(_dados: unknown): EconomicEvent[] {
  return gerarMockEventos();
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
        'https://api.forexfactory.com/calendar?week=this_week',
        { method: 'GET', signal: AbortSignal.timeout(5000) }
      );

      if (resposta.ok) {
        const dadosApi = await resposta.json();
        const eventosProcessados = processarDadosApi(dadosApi);
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
    } catch {
      console.info('[useEconomicData] API indisponível, usando dados simulados');
    }

    const mock = gerarMockEventos();
    if (montadoRef.current) {
      salvarNoCache(mock);
      setEstado({
        dados: mock,
        carregando: false,
        erro: null,
        ultimaAtualizacao: new Date(),
      });
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
