# Roadmap - App Mobile XAU_AI_PRO

> Versão: 1.0 | Data: 2026-09-11

---

## Visão Geral

Transformar a Trading Desk desktop (Tkinter) em um app mobile multiplataforma (Flutter) que consome a mesma infraestrutura backend já existente.

---

## O que ja esta pronto (reaproveitar 100%)

| Componente | Local | Status |
|------------|-------|--------|
| Backend API REST | backend/server-desktop.cjs | ✅ Pronto |
| WebSocket (tempo real) | backend/server-desktop.cjs | ✅ Pronto |
| 14 endpoints HTTP | app/backend_client.py | ✅ Pronto |
| Rate limiting | backend/ | ✅ Pronto |
| SQLite (cache local) | database/trading.db | ✅ Pronto |
| Sistema de cores/tema | app/theme/mexc.py | ✅ Reutilizar design |
| Indicadores tecnicos | app/data/indicators.py | ✅ Portar lógica |

---

## Fases de Implementacao

### Fase 1: Preparacao do Backend (1-2 semanas)
- Substituir Bearer key por JWT + refresh token
- Adicionar endpoint /auth/login com biometria
- Implementar WebSocket delta (so envia mudanças)
- Adicionar CORS para origens mobile
- Documentar API com OpenAPI/Swagger

### Fase 2: App Flutter - Core (2-3 semanas)
- Setup do projeto Flutter (Android + iOS)
- Models/entities (Quote, Position, Signal, etc.)
- Servicos HTTP (Dio + interceptors)
- WebSocket client (socket_io_client)
- Cache local (drift/isar)
- Gerenciamento de estado (Riverpod)

### Fase 3: UI/UX (2-3 semanas)
- Tema dark (copiar cores do mexc.py)
- Tela de login com biometria
- Dashboard (KPIs, equity, posicoes)
- Lista de ativos com busca/filtros
- Grafico de candles (fl_chart)
- Painel de indicadores configuraveis

### Fase 4: Funcionalidades Avancadas (2 semanas)
- Strategy Tester (backtesting visual)
- Visao do Robo (tempo real)
- Push notifications (FCM/APNs)
- Ordens manuais (confirmacao biometrica)
- Modo offline (cache + indicador)

### Fase 5: Testes e Publicacao (1-2 semanas)
- Testes unitarios e integracao
- Beta testing (TestFlight + Play Store)
- Otimizacao (R8/ProGuard)
- Lancamento

---

## Seguranca

| Camada | Implementacao |
|--------|---------------|
| Credenciais | Keystore (Android) / Keychain (iOS) |
| API | JWT + refresh token + rate limiting |
| Biometria | TouchID/FaceID / Fingerprint |
| Push | FCM (Android) / APNs (iOS) |
| Comunicacao | HTTPS + certificate pinning |

---

## Proximos Passos Imediatos

1. ✅ Corrigir encoding (UTF-8) - FEITO
2. ✅ Heartbeat do EA (is_ea_active) - FEITO
3. ✅ Reduzir .exe (cleanup) - FEITO
4. JWT no backend (substituir Bearer)
5. WebSocket delta (nao reenviar snapshot)
6. Prototipo Flutter (tab Mercado + grafico)
