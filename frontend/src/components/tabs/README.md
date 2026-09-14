# 📅 Calendário Econômico & 📰 Notícias Globais

## Visão Geral

Sistema completo de dados de mercado em tempo real para o XAU AI PRO, com:

- **Calendário Econômico**: Eventos macroeconômicos com impacto no mercado
- **Notícias Globais**: Feed de notícias que movem o mercado financeiro

## Estrutura de Arquivos

```
tabs/
├── EconomicCalendarTab.tsx   # Componente do calendário econômico
├── NewsTab.tsx               # Componente de notícias globais
├── types.ts                  # Tipos TypeScript compartilhados
└── index.ts                  # Exportações

hooks/
├── useEconomicData.ts        # Hook para dados do calendário
├── useNewsStream.ts          # Hook para stream de notícias
└── index.ts                  # Exportações
```

## Funcionalidades

### Calendário Econômico (`EconomicCalendarTab`)

- ✅ Lista de eventos próximos (hoje, amanhã, semana)
- ✅ Cada evento: hora, país, impacto, título, anterior, consenso, real
- ✅ Filtros por: país (EUA, UK, EU, JP, BR, CN), impacto, data
- ✅ Cores por impacto: amarelo (médio), vermelho (alto), cinza (baixo)
- ✅ Countdown para próximo evento importante
- ✅ Badge de "ALTO IMPACTO" pulsante para eventos críticos
- ✅ Refresh automático a cada 5 minutos
- ✅ Cache local com localStorage

### Notícias Globais (`NewsTab`)

- ✅ Feed de notícias que movem o mercado
- ✅ Categorias: Guerras/Geopolítica, Taxas de Juros, Inflação, PIB, Emprego, Cripto, Commodities, Forex
- ✅ Cada notícia: título, fonte, timestamp, impacto no mercado
- ✅ Indicador visual de sentiment (seta verde/vermelha)
- ✅ Filtros por categoria
- ✅ Busca por palavra-chave
- ✅ Refresh automático a cada 60 segundos
- ✅ Deduplicação por ID
- ✅ Máximo 100 notícias no estado

## Hooks Customizados

### `useEconomicData(filtro, intervaloRefreshMs)`

Gerencia fetching, cache e filtros de eventos econômicos.

**Parâmetros:**
- `filtro: FiltroCalendario` - Configuração de filtros
- `intervaloRefreshMs: number` - Intervalo de refresh (padrão: 5 min)

**Retorno:**
```typescript
{
  eventos: EconomicEvent[];       // Eventos filtrados
  carregando: boolean;            // Estado de loading
  erro: string | null;            // Mensagem de erro
  ultimaAtualizacao: Date | null; // Última atualização
  proximoEventoAlto: EconomicEvent | undefined; // Próximo evento crítico
  refreshManual: () => void;      // Forçar refresh
  totalEventos: number;           // Total de eventos
}
```

### `useNewsStream(filtro, intervaloPollingMs)`

Gerencia feed de notícias com polling e deduplicação.

**Parâmetros:**
- `filtro: FiltroNoticias` - Configuração de filtros
- `intervaloPollingMs: number` - Intervalo de polling (padrão: 60s)

**Retorno:**
```typescript
{
  noticias: NewsItem[];           // Notícias filtradas
  carregando: boolean;            // Estado de loading
  erro: string | null;            // Mensagem de erro
  ultimaAtualizacao: Date | null; // Última atualização
  refreshManual: () => void;      // Forçar refresh
  limparCache: () => void;        // Limpar cache
  totalNoticias: number;          // Total de notícias
}
```

## Tipos TypeScript

### `EconomicEvent`

```typescript
interface EconomicEvent {
  id: string;
  horario: Date;
  codigoPais: string;        // Ex: "US", "BR"
  nomePais: string;          // Ex: "Estados Unidos"
  bandeira: string;          // Ex: "🇺🇸"
  impacto: ImpactLevel;      // "baixo" | "medio" | "alto"
  titulo: string;
  anterior: string | null;
  consenso: string | null;
  real: string | null;
  divulgado: boolean;
}
```

### `NewsItem`

```typescript
interface NewsItem {
  id: string;
  titulo: string;
  fonte: string;             // Ex: "Reuters", "Bloomberg"
  timestamp: Date;
  categoria: NewsCategory;   // 8 categorias disponíveis
  impactoMercado: MarketImpact; // "bullish" | "bearish" | "neutral"
  resumo?: string;
  url?: string;
}
```

## Uso

```tsx
import { EconomicCalendarTab, NewsTab } from "./components/tabs";

// No seu componente de tabs
<EconomicCalendarTab />
<NewsTab />
```

## APIs Utilizadas

### Calendário Econômico
- **Primária**: `https://api.forexfactory.com/calendar` (requer API key)
- **Fallback**: Mock realista com eventos FOMC, BCE, BOJ, Copom, etc.

### Notícias Globais
- **Primária**: `https://newsapi.org/v2/top-headlines` (requer API key)
- **Fallback**: Mock realista com notícias de guerras, FED, BCE, OPEC, etc.

## Notas

- Quando as APIs estão indisponíveis, o sistema usa mocks realistas com aviso no console
- Cache local evita requisições desnecessárias
- Deduplicação garante que notícias não sejam repetidas
- Interface responsiva com tema escuro
- Código 100% em português (comentários e labels)
