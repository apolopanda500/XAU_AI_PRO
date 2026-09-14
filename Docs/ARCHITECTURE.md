# XAU AI PRO — Arquitetura e Decisões Técnicas

## Visão Geral

XAU AI PRO é um aplicativo de trading de alta performance projetado para operar em conta real com robôs no MetaTrader 5 (MT5) e outras corretoras. A arquitetura segue o padrão de apps de trading de primeira linha global em 2026.

## Arquitetura

```
┌─────────────────────────────────────────────────┐
│  Frontend (React + TypeScript + Tauri)          │
│  - Dashboard, Charts, Controle, Config          │
│  - WebSocket client ←→ Rust Core               │
└──────────────────────┬──────────────────────────┘
                       │ WebSocket (porta 9002)
                       │ HTTP API (porta 9003)
┌──────────────────────▼──────────────────────────┐
│  Core Backend (Rust)                            │
│  - Market Data Service (multi-provider)         │
│  - Execution Engine                             │
│  - MT5 Bridge                                   │
│  - Account Service                              │
│  - SQLite (cache local)                         │
└──────────────────────┬──────────────────────────┘
                       │ HTTP local (porta 9001)
┌──────────────────────▼──────────────────────────┐
│  MT5 EA (MQL5) — Executor Real                  │
│  - Recebe sinais do Rust Core                   │
│  - Executa ordens no MT5                        │
│  - Reporta resultados                           │
└─────────────────────────────────────────────────┘
```

## Stack Tecnológica

| Camada | Tecnologia | Justificativa |
|--------|------------|---------------|
| Core/Backend | Rust (axum/tokio) | Performance extrema, memory safety, sem GC |
| Frontend Desktop | React + TypeScript + Tauri | Nativo, leve, cross-platform |
| Frontend Web | React + TypeScript (Vite) | Ecossistema maduro, rápido |
| Mobile | React Native (futuro) | Compartilha código com web |
| Execução | MQL5 EA (MT5) | Padrão de fato no retail Forex/CFDs |
| Banco Local | SQLite | Leve, sem servidor, serverless |
| Banco Servidor | PostgreSQL (futuro) | Persistência robusta |
| Comunicação | WebSocket + REST | Tempo-real + controle |
| Protocolo | JSON via WebSocket | Simples, universal, debugável |

## Decisões de Design

### Por que Rust para o backend?
- Performance próxima a C++ com segurança de memória
- Sem garbage collector → latência previsível
- Sistema de tipos forte → menos bugs em produção
- Async/await nativo (tokio) → ideal para I/O bound (rede, mercado)
- Ecossistema crescente para fintech em 2026

### Por que React + Tauri para o frontend?
- React: ecossistema enorme, TypeScript, componentes reutilizáveis
- Tauri: empacota web como app nativo, sem Chromium pesado (diferente de Electron)
- Tauri: backend Rust integrado → comunicação direta com nosso core
- Tauri: apps < 10MB, startup rápido, consumo de RAM baixo

### Por que manter MQL5 EA?
- Executor real no MT5 já funciona
- MT5 é padrão de fato no retail Forex/CFDs
- Substituir MT5 exigiria integração direta com corretora (complexo)
- Rust fará bridge com MT5, não substitui o EA

## Módulos do Core Rust

| Módulo | Arquivo | Responsabilidade |
|--------|---------|------------------|
| config | src/config.rs | Configuração (JSON, env, defaults) |
| protocol | src/protocol/mod.rs | Tipos compartilhados (Quote, Order, etc.) |
| market | src/market/mod.rs | Market Data Service (WebSocket, cotações) |
| execution | src/execution/mod.rs | Engine de Execução de Ordens |
| bridge | src/bridge/mod.rs | Bridge MT5 (comunicação com EA) |
| account | src/account/mod.rs | Gerenciamento de Conta |

## Módulos do Frontend React

| Módulo | Arquivo | Responsabilidade |
|--------|---------|------------------|
| App | src/App.tsx | Componente raiz |
| Dashboard | src/components/Dashboard.tsx | Painel principal |
| Sidebar | src/components/Sidebar.tsx | Menu lateral |
| TopNav | src/components/TopNav.tsx | Navegação superior |
| useAppStore | src/hooks/useAppStore.ts | Estado global (Zustand) |
| useTheme | src/hooks/useTheme.ts | Temas (dark, xau_dark, btc_dark) |
| useMarketWebSocket | src/hooks/useMarketWebSocket.ts | Conexão WS com Rust |

## Comunicação

### WebSocket (Rust → Frontend)
- URL: `ws://127.0.0.1:9002/ws/market`
- Mensagens: Quote, AccountInfo, PositionUpdate, OrderResponse, SystemState
- Reconexão automática a cada 3s

### HTTP API (Rust)
- URL base: `http://127.0.0.1:9003/api/`
- Endpoints: /health, /quotes, /account, /positions, /order

### Bridge MT5 (Rust → EA)
- URL: `http://127.0.0.1:9001/api/mt5/`
- O EA MQL5 expõe uma API local que o Rust consome

## Temas

O app suporta 3 temas:
- **dark** — tema padrão escuro profissional
- **xau_dark** — tema dourado inspirado em ouro/XAU
- **btc_dark** — tema verde-neon inspirado em Bitcoin

## Segurança

- Nunca commitar .env ou chaves de API
- Comunicação local (127.0.0.1) por padrão
- Validação de volume e risco no Execution Engine
- Confirmação de ordens reais via dialog

## Performance

- Rust: latência de microsegundos no processamento
- WebSocket: push de dados sem polling
- SQLite: cache local sem overhead de rede
- Tauri: app nativo leve (< 10MB)

## Próximos Passos

1. Instalar dependências do frontend (npm install)
2. Compilar o core Rust (cargo build)
3. Testar comunicação WebSocket
4. Integrar com MT5 EA
5. Deploy
