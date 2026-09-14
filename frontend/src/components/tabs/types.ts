/**
 * Tipos TypeScript para Calendário Econômico e Notícias Globais
 * XAU AI PRO - Sistema de Dados de Mercado
 */

/**
 * Nível de impacto de um evento econômico
 */
export type ImpactLevel = 'baixo' | 'medio' | 'alto';

/**
 * Representa um evento econômico no calendário
 */
export interface EconomicEvent {
  id: string;
  /** Horário do evento no fuso local */
  horario: Date;
  /** País de origem (código ISO 3166-1 alpha-2) */
  codigoPais: string;
  /** Nome do país para exibição */
  nomePais: string;
  /** Bandeira do país (emoji) */
  bandeira: string;
  /** Nível de impacto no mercado */
  impacto: ImpactLevel;
  /** Título do evento */
  titulo: string;
  /** Valor anterior */
  anterior: string | null;
  /** Valor consenso/expectativa */
  consenso: string | null;
  /** Valor real (após divulgação) */
  real: string | null;
  /** Indica se o evento já foi divulgado */
  divulgado: boolean;
}

/**
 * Categoria de notícia do mercado
 */
export type NewsCategory =
  | 'guerras_geopolitica'
  | 'taxas_juros'
  | 'inflacao'
  | 'pib'
  | 'emprego'
  | 'cripto'
  | 'commodities'
  | 'forex';

/**
 * Impacto da notícia no mercado
 */
export type MarketImpact = 'bullish' | 'bearish' | 'neutral';

/**
 * Item de notícia do mercado
 */
export interface NewsItem {
  id: string;
  /** Título da notícia */
  titulo: string;
  /** Fonte/publicação */
  fonte: string;
  /** Horário da publicação */
  timestamp: Date;
  /** Categoria da notícia */
  categoria: NewsCategory;
  /** Impacto estimado no mercado */
  impactoMercado: MarketImpact;
  /** Resumo/opcional */
  resumo?: string;
  /** Link para a notícia original */
  url?: string;
}

/**
 * Configuração de filtro do calendário econômico
 */
export interface FiltroCalendario {
  paises: string[];
  impactos: ImpactLevel[];
  dataInicio: Date | null;
  dataFim: Date | null;
}

/**
 * Configuração de filtro de notícias
 */
export interface FiltroNoticias {
  categorias: NewsCategory[];
  busca: string;
}

/**
 * Estado de carregamento genérico
 */
export interface EstadoCarregamento<T> {
  dados: T | null;
  carregando: boolean;
  erro: string | null;
  ultimaAtualizacao: Date | null;
}

/**
 * Mapeamento de cores por impacto
 */
export const CORES_IMPACTO: Record<ImpactLevel, string> = {
  baixo: '#6b7280',   // Cinza
  medio: '#eab308',   // Amarelo
  alto: '#ef4444',    // Vermelho
};

/**
 * Mapeamento de cores por impacto de mercado (notícias)
 */
export const CORES_IMPACTO_MERCADO: Record<MarketImpact, string> = {
  bullish: '#22c55e',   // Verde (alta)
  bearish: '#ef4444',   // Vermelho (baixa)
  neutral: '#6b7280',   // Cinza
};

/**
 * Labels de categorias de notícias
 */
export const LABELS_CATEGORIAS: Record<NewsCategory, string> = {
  guerras_geopolitica: 'Guerras & Geopolítica',
  taxas_juros: 'Taxas de Juros',
  inflacao: 'Inflação',
  pib: 'PIB',
  emprego: 'Emprego',
  cripto: 'Cripto',
  commodities: 'Commodities',
  forex: 'Forex',
};

/**
 * Configuração de polling
 */
export interface ConfiguracaoPolling {
  intervaloMs: number;
  ativo: boolean;
}

/**
 * País com dados para exibição
 */
export interface PaisInfo {
  codigo: string;
  nome: string;
  bandeira: string;
}

/**
 * Lista de países suportados
 */
export const PAISES_SUPORTADOS: PaisInfo[] = [
  { codigo: 'US', nome: 'Estados Unidos', bandeira: '🇺🇸' },
  { codigo: 'GB', nome: 'Reino Unido', bandeira: '🇬🇧' },
  { codigo: 'EU', nome: 'União Europeia', bandeira: '🇪🇺' },
  { codigo: 'JP', nome: 'Japão', bandeira: '🇯🇵' },
  { codigo: 'BR', nome: 'Brasil', bandeira: '🇧🇷' },
  { codigo: 'CN', nome: 'China', bandeira: '🇨🇳' },
];
