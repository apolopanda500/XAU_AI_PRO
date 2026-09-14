# Changelog - Calendário Econômico & Notícias Globais

## [1.0.0] - 2025-01-14

### Adicionado
- ✅ **EconomicCalendarTab.tsx** - Componente completo do calendário econômico
  - Lista de eventos com hora, país, impacto, título, anterior, consenso, real
  - Filtros por país (EUA, UK, EU, JP, BR, CN)
  - Filtros por impacto (baixo, médio, alto)
  - Cores visuais por nível de impacto
  - Countdown em tempo real para próximo evento de alto impacto
  - Badge pulsante "ALTO IMPACTO" para eventos críticos
  - Agrupamento de eventos por data
  - Indicador de eventos já divulgados

- ✅ **NewsTab.tsx** - Componente completo de notícias globais
  - Feed de notícias com indicadores de sentiment
  - 8 categorias: Guerras/Geopolítica, Taxas de Juros, Inflação, PIB, Emprego, Cripto, Commodities, Forex
  - Indicador visual de impacto (bullish/bearish/neutral)
  - Filtros por categoria
  - Busca por palavra-chave
  - Timestamps relativos (ex: "5min atrás")
  - Badge "LIVE" para indicar feed em tempo real

- ✅ **useEconomicData.ts** - Hook para dados do calendário econômico
  - Fetch de calendário com fallback para mock realista
  - Cache local com localStorage (TTL: 5 minutos)
  - Refresh automático configurável
  - Filtros aplicados no frontend
  - Detecção do próximo evento de alto impacto
  - Controle de estado (loading, error, data)

- ✅ **useNewsStream.ts** - Hook para stream de notícias
  - Feed com polling automático (padrão: 60 segundos)
  - Mock realista com notícias de fontes confiáveis
  - Deduplicação por ID (evita notícias repetidas)
  - Limite máximo de 100 notícias no estado
  - Cache local com localStorage (TTL: 2 minutos)
  - Função para limpar cache

- ✅ **types.ts** - Tipos TypeScript completos
  - `EconomicEvent` - Interface para eventos econômicos
  - `NewsItem` - Interface para notícias
  - `MarketImpact` - Tipo para impacto no mercado
  - `NewsCategory` - Tipo para categorias de notícias
  - `FiltroCalendario` - Interface para filtros do calendário
  - `FiltroNoticias` - Interface para filtros de notícias
  - `EstadoCarregamento<T>` - Genérico para estado de loading
  - Constantes de cores e labels

- ✅ **Documentação completa**
  - README.md com visão geral e instruções
  - EXAMPLE_USAGE.tsx com exemplo de integração
  - CHANGELOG.md com histórico de alterações

### Características Técnicas

- **TypeScript**: Tipagem completa e segura
- **React Hooks**: useState, useEffect, useCallback, useRef, useMemo
- **Cache**: localStorage com TTL configurável
- **Polling**: Refresh automático com intervalos configuráveis
- **Fallback**: Mocks realistas quando APIs indisponíveis
- **Performance**: Deduplicação, limitação de itens, lazy loading
- **UI/UX**: Tema escuro, animações, indicadores visuais
- **Código**: 100% em português (comentários e labels)

### APIs Integráveis

- **Calendário**: `https://api.forexfactory.com/calendar`
- **Notícias**: `https://newsapi.org/v2/top-headlines`

### Próximos Passos (Roadmap)

- [ ] Integração com APIs reais (requer chaves de API)
- [ ] WebSocket para notícias em tempo real (SSE)
- [ ] Notificações push para eventos de alto impacto
- [ ] Exportação de calendário (ICS)
- [ ] Histórico de eventos passados
- [ ] Análise de sentimento automática (NLP)
- [ ] Suporte a múltiplos idiomas
- [ ] Temas claro/escuro configuráveis
