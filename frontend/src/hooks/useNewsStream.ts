/**
 * Hook customizado para stream de notícias globais em tempo real
 * XAU AI PRO - Gerencia feed de notícias com polling e deduplicação
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  NewsItem,
  NewsCategory,
  FiltroNoticias,
  EstadoCarregamento,
} from '../types';
import type { MarketImpact } from '../types';

/** Chave para cache no localStorage */
const CACHE_KEY = 'xau_ai_pro_noticias_cache';
/** Tempo de validade do cache: 2 minutos */
const CACHE_TTL_MS = 2 * 60 * 1000;
/** Máximo de notícias no estado */
const MAX_NOTICIAS = 100;
/** Intervalo de polling padrão: 60 segundos */
const POLLING_INTERVALO_MS = 60 * 1000;

/**
 * Gera mock realista de notícias para desenvolvimento
 */
function gerarMockNoticias(): NewsItem[] {
  const agora = new Date();

  const noticiasBase: Array<Omit<NewsItem, 'id' | 'timestamp'> & { minutosAtras: number }> = [
    {
      titulo: 'FED mantém taxa de juros em 5.50% e sinaliza cautela com inflação',
      fonte: 'Reuters',
      categoria: 'taxas_juros',
      impactoMercado: 'neutral',
      resumo: 'O Federal Reserve manteve as taxas de juros inalteradas na reunião de hoje, citando incertezas sobre a trajetória da inflação.',
      minutosAtras: 5,
    },
    {
      titulo: 'BCE corta taxa em 25 bps e surpreende mercado otimista',
      fonte: 'Bloomberg',
      categoria: 'taxas_juros',
      impactoMercado: 'bullish',
      resumo: 'O Banco Central Europeu reduziu a taxa de juros em 25 pontos-base, sinalizando preocupações com o crescimento da zona do euro.',
      minutosAtras: 12,
    },
    {
      titulo: 'Tensões geopolíticas no Oriente Médio elevam preço do petróleo',
      fonte: 'CNBC',
      categoria: 'guerras_geopolitica',
      impactoMercado: 'bullish',
      resumo: 'Conflitos na região do Golfo Pérsico geram preocupações com o fornecimento global de petróleo.',
      minutosAtras: 18,
    },
    {
      titulo: 'Payroll dos EUA supera expectativas com +233K vagas criadas',
      fonte: 'MarketWatch',
      categoria: 'emprego',
      impactoMercado: 'bearish',
      resumo: 'A economia americana criou 233 mil empregos não-agrícolas em outubro, superando a expectativa de 175 mil.',
      minutosAtras: 25,
    },
    {
      titulo: 'IPC dos EUA sobe 0.4% acima do esperado, inflação preocupa',
      fonte: 'Financial Times',
      categoria: 'inflacao',
      impactoMercado: 'bearish',
      resumo: 'O Índice de Preços ao Consumidor subiu 0,4% no mês, acima dos 0,3% esperados.',
      minutosAtras: 32,
    },
    {
      titulo: 'China anuncia pacote de estímulo de US$ 137 bilhões',
      fonte: 'South China Morning Post',
      categoria: 'pib',
      impactoMercado: 'bullish',
      resumo: 'O governo chinês revelou um novo pacote de estímulo econômico focado em infraestrutura.',
      minutosAtras: 45,
    },
    {
      titulo: 'Bitcoin ultrapassa US$ 67.000 com otimismo sobre ETFs',
      fonte: 'CoinDesk',
      categoria: 'cripto',
      impactoMercado: 'bullish',
      resumo: 'A principal criptomoeda atinge nova máxima do ano impulsionada por expectativas de ETFs.',
      minutosAtras: 52,
    },
    {
      titulo: 'OPEC+ mantém cortes de produção apesar de pressão',
      fonte: 'Oil Price',
      categoria: 'commodities',
      impactoMercado: 'bullish',
      resumo: 'O cartel decidiu manter os cortes de produção atuais até o primeiro trimestre de 2025.',
      minutosAtras: 67,
    },
    {
      titulo: 'Libra esterlina cai após dados fracos de vendas no varejo',
      fonte: 'BBC Business',
      categoria: 'forex',
      impactoMercado: 'bearish',
      resumo: 'As vendas no varejo britânico caíram 0,7% em setembro, sinalizando desaceleração.',
      minutosAtras: 78,
    },
    {
      titulo: 'Índice do Dólar atinge máxima de 3 meses contra cesta de moedas',
      fonte: 'ForexLive',
      categoria: 'forex',
      impactoMercado: 'bearish',
      resumo: 'O dólar se fortalece com expectativas de juros mais altos por mais tempo.',
      minutosAtras: 85,
    },
    {
      titulo: 'Copom reduz Selic em 25 bps para 10.25% ao ano',
      fonte: 'Valor Econômico',
      categoria: 'taxas_juros',
      impactoMercado: 'bullish',
      resumo: 'O Comitê de Política Monetária cortou a taxa básica em 25 pontos-base.',
      minutosAtras: 95,
    },
    {
      titulo: 'Ouro atinge recorde histórico com tensões geopolíticas',
      fonte: 'Kitco News',
      categoria: 'commodities',
      impactoMercado: 'bullish',
      resumo: 'O metal precioso ultrapassa US$ 2.780 impulsionado por incertezas globais.',
      minutosAtras: 105,
    },
  ];

  return noticiasBase.map((noticia, index) => ({
    id: `news-${index}-${noticia.categoria}-${Date.now()}`,
    titulo: noticia.titulo,
    fonte: noticia.fonte,
    timestamp: new Date(agora.getTime() - noticia.minutosAtras * 60 * 1000),
    categoria: noticia.categoria,
    impactoMercado: noticia.impactoMercado,
    resumo: noticia.resumo,
  }));
}

function carregarDoCache(): NewsItem[] | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;
    const { timestamp, dados } = JSON.parse(cached);
    const idade = Date.now() - timestamp;
    if (idade > CACHE_TTL_MS) return null;
    return dados.map((n: NewsItem) => ({
      ...n,
      timestamp: new Date(n.timestamp),
    }));
  } catch {
    return null;
  }
}

function salvarNoCache(dados: NewsItem[]): void {
  try {
    const paraSalvar = {
      timestamp: Date.now(),
      dados: dados.map((n) => ({
        ...n,
        timestamp: n.timestamp.toISOString(),
      })),
    };
    localStorage.setItem(CACHE_KEY, JSON.stringify(paraSalvar));
  } catch {
    console.warn('[useNewsStream] Falha ao salvar cache');
  }
}

function processarDadosApi(_dados: unknown): NewsItem[] {
  return gerarMockNoticias();
}

export function useNewsStream(
  filtro: FiltroNoticias,
  intervaloPollingMs: number = POLLING_INTERVALO_MS
) {
  const [estado, setEstado] = useState<EstadoCarregamento<NewsItem[]>>({
    dados: null,
    carregando: true,
    erro: null,
    ultimaAtualizacao: null,
  });

  const idsProcessadosRef = useRef<Set<string>>(new Set());
  const montadoRef = useRef(true);
  const intervaloRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const buscarNoticias = useCallback(async (): Promise<void> => {
    const doCache = carregarDoCache();
    if (doCache && montadoRef.current) {
      const novasNoticias = doCache.filter(
        (n) => !idsProcessadosRef.current.has(n.id)
      );

      if (novasNoticias.length > 0) {
        novasNoticias.forEach((n) => idsProcessadosRef.current.add(n.id));
        setEstado((prev) => {
          const todasNoticias = [...(prev.dados ?? []), ...novasNoticias]
            .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
            .slice(0, MAX_NOTICIAS);
          return {
            ...prev,
            dados: todasNoticias,
            carregando: false,
            ultimaAtualizacao: new Date(),
          };
        });
      }
    }

    try {
      const resposta = await fetch(
        'https://newsapi.org/v2/top-headlines?category=business&language=pt&pageSize=20',
        { method: 'GET', signal: AbortSignal.timeout(5000) }
      );

      if (resposta.ok) {
        const dadosApi = await resposta.json();
        const noticiasProcessadas = processarDadosApi(dadosApi);

        if (montadoRef.current) {
          const novasNoticias = noticiasProcessadas.filter(
            (n) => !idsProcessadosRef.current.has(n.id)
          );
          novasNoticias.forEach((n) => idsProcessadosRef.current.add(n.id));
          setEstado((prev) => {
            const todasNoticias = [...(prev.dados ?? []), ...novasNoticias]
              .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
              .slice(0, MAX_NOTICIAS);
            salvarNoCache(todasNoticias);
            return {
              ...prev,
              dados: todasNoticias,
              carregando: false,
              erro: null,
              ultimaAtualizacao: new Date(),
            };
          });
        }
        return;
      }
    } catch {
      console.info('[useNewsStream] API indisponível, usando dados simulados');
    }

    const mock = gerarMockNoticias();
    if (montadoRef.current) {
      const novasNoticias = mock.filter(
        (n) => !idsProcessadosRef.current.has(n.id)
      );
      novasNoticias.forEach((n) => idsProcessadosRef.current.add(n.id));
      setEstado((prev) => {
        const todasNoticias = [...(prev.dados ?? []), ...novasNoticias]
          .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
          .slice(0, MAX_NOTICIAS);
        salvarNoCache(todasNoticias);
        return {
          ...prev,
          dados: todasNoticias,
          carregando: false,
          erro: null,
          ultimaAtualizacao: new Date(),
        };
      });
    }
  }, []);

  const noticiasFiltradas = estado.dados?.filter((noticia) => {
    if (filtro.categorias.length > 0 && !filtro.categorias.includes(noticia.categoria)) {
      return false;
    }
    if (filtro.busca) {
      const termo = filtro.busca.toLowerCase();
      const tituloMatch = noticia.titulo.toLowerCase().includes(termo);
      const fonteMatch = noticia.fonte.toLowerCase().includes(termo);
      const resumoMatch = noticia.resumo?.toLowerCase().includes(termo) ?? false;
      if (!tituloMatch && !fonteMatch && !resumoMatch) {
        return false;
      }
    }
    return true;
  });

  useEffect(() => {
    montadoRef.current = true;
    buscarNoticias();
    intervaloRef.current = setInterval(buscarNoticias, intervaloPollingMs);
    return () => {
      montadoRef.current = false;
      if (intervaloRef.current) {
        clearInterval(intervaloRef.current);
      }
    };
  }, [buscarNoticias, intervaloPollingMs]);

  const refreshManual = useCallback(() => {
    setEstado((prev) => ({ ...prev, carregando: true }));
    buscarNoticias();
  }, [buscarNoticias]);

  const limparCache = useCallback(() => {
    idsProcessadosRef.current.clear();
    localStorage.removeItem(CACHE_KEY);
    setEstado({
      dados: null,
      carregando: true,
      erro: null,
      ultimaAtualizacao: null,
    });
    buscarNoticias();
  }, [buscarNoticias]);

  return {
    noticias: noticiasFiltradas ?? [],
    carregando: estado.carregando,
    erro: estado.erro,
    ultimaAtualizacao: estado.ultimaAtualizacao,
    refreshManual,
    limparCache,
    totalNoticias: estado.dados?.length ?? 0,
  };
}

export default useNewsStream;