# ETAPA 19 — Política de Segurança Operacional (XAU_AI_PRO)

Data: 2026-08-24 | Status: APLICADA

## 1. Segredos fora do código
- **`.env`** (SENTRY_DSN, BROKER_API_KEY, SECRET, etc.) — **não versionado** (`.gitignore`).
- **Apenas `.env.example`** versionado (template sem valores reais).
- **Chaves de API** no `config.json`: todas **vazias** (`""`) — sem credencial hardcoded.

## 2. Autenticação local
- Senha do usuário admin armazenada como **hash pbkdf2-hmac-sha256, 100.000 iterações** + salt.
- **Rotação aplicada (2026-08-24)**: o hash/salt exposto em histórico foi substituído por novo par
  (salt `7e0704…`, hash `2400a0…`). O hash antigo está **invalidado**.
- `config.json` (com hash/salt) está **fora do versionamento** git.

## 3. Permissões claras
| Camada | Acesso |
|---|---|
| EA (MQL5) | leitura de CSV/JSON de dados e prediction; nenhuma credencial |
| Backend (Node) | leitura do Event Stream / AuditLog (somente leitura) |
| Dashboard (App) | somente-leitura via API backend; sem acesso direto a secrets |
| Python/IA | roda com dados locais; secrets via env (nunca em código) |

## 4. Logs sem dados sensíveis
- Backend/dashboard: **nenhum token/senha logado**.
- Event Stream: registra evento/símbolo/latência/estado — **nunca credenciais**.
- AuditLog: registra tickets/decisões — **sem campos sensíveis**.

## 5. Boas práticas
- Python: `import secrets`, `hashlib.pbkdf2_hmac`.
- Backend: CORS aberto apenas para uso local (127.0.0.1 dashboard).
- Nenhuma DLL externa; sem auto-update (VersionManager OFF forçado).
