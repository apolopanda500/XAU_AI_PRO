# ============================================================
# DOCKER & VERcel CONTAINER REGISTRY - XAU AI PRO
# ============================================================
# Guia completo de configuracao de Docker no Windows e
# publicacao da imagem no Vercel Container Registry (VCR).
# ============================================================

## Resumo

O projeto XAU_AI_PRO usa containers de tres formas:

1. **Local (dev/teste)** - Docker Desktop ou Podman com `docker-compose.yml`
2. **CI/CD (producao)** - GitHub Actions + **Docker Build Cloud** (`rickjax123/apolopanda500`)
3. **Deploy (versoes)** - **Vercel Container Registry (VCR)** com `Dockerfile.vercel`

---

## 1. Instalacao do Docker Desktop no Windows

### 1.1 Pre-requisitos

- Windows 10/11 64-bit com virtualizacao habilitada (WSL2)
- 4 GB RAM (recomendado 8 GB)
- BIOS/UEFI com Virtualization Technology (VT-x/AMD-V) ativo

### 1.2 Instalar (Administrador obrigatorio)

Execute o script de instalacao automatica como **Administrador**:

```powershell
# Clique direito no PowerShell -> "Run as administrator"
Set-ExecutionPolicy Bypass -Scope Process -Force
.\Tools\install_docker_windows.ps1
```

O script:
1. Habilita WSL, Virtual Machine Platform e Hyper-V
2. Baixa e instala o Docker Desktop
3. Prepara reinicializacao do Windows

Apos reiniciar:
1. Abra o **Docker Desktop**
2. Aceite os termos e configure
3. Em Settings → Resources → **WSL Integration**
4. Ative a integracao com a distro do WSL

### 1.3 Verificar instalacao

```powershell
docker --version
docker compose version
docker info
```

---

## 2. Subir o projeto com Docker Compose

### 2.1 Servicos disponiveis

| Servico | Porta | Descricao |
|---------|-------|-----------|
| `backend` | 3000 | API Node.js/Nitro |
| `litellm` | 4000 | Proxy IA LiteLLM |
| `xau_ai_pro_net` | - | Rede interna entre servicos |

### 2.2 Comandos

```powershell
cd "C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO"

# Subir todos os servicos
docker compose up -d

# Subir apenas o backend
docker compose up -d backend

# Subir apenas o LiteLLM
docker compose up -d litellm

# Ver logs
docker compose logs -f backend
docker compose logs -f litellm

# Derrubar tudo
docker compose down
```

### 2.3 Testar

```powershell
# Backend
curl http://localhost:3000/api/health
# deve retornar: {"ok":true}

# LiteLLM (proxy IA)
curl http://localhost:4000/v1/models
# deve listar o modelo configurado
```
---

## 3. Docker Build Cloud (GitHub Actions)

O workflow `.github/workflows/build.yml` usa o builder Docker Build Cloud:

```yaml
- name: Configurar Docker Buildx Cloud
  uses: docker/setup-buildx-action@v3
  with:
    driver: cloud
    endpoint: "rickjax123/apolopanda500"
```

### 3.1 Secrets necessarios no GitHub

| Secret/Var | Valor |
|------------|-------|
| `DOCKER_USER` | `rickjax123` |
| `DOCKER_PAT` | Seu Personal Access Token do Docker Hub |

### 3.2 Builds multi-plataforma (GitLab CI)

O `.gitlab-ci.yml` espelha o comportamento do `build.yml` do GitHub:

```yaml
- docker buildx build --platform linux/amd64,linux/arm64 \
    --file backend/Dockerfile --push backend
```

Comportamento:

| Situação | Resultado |
|----------|-----------|
| `DOCKER_ENABLED=true` + `DOCKER_USER`/`DOCKER_PAT` configurados | `build_push` roda e publica `${DOCKER_USER}/xau-ai-pro-backend` (tags `latest` + short SHA) |
| Credenciais ausentes (padrão) | `build_push` é **pulada**; apenas `build_cache` valida o build multi-plataforma (sem login) |

Para ativar o push no GitLab, configure em **Settings > CI/CD > Variables**:

| Tipo | Chave | Valor |
|------|-------|-------|
| Variable | `DOCKER_ENABLED` | `true` |
| Variable | `DOCKER_USER` | `rickjax123` |
| Variable (masked) | `DOCKER_PAT` | Personal Access Token do Docker Hub |

### 3.3 Rodar build manualmente

```powershell
# Criar builder
docker buildx create --use --driver cloud rickjax123/apolopanda500

# Build e push para Docker Hub
docker buildx build --platform linux/amd64 --push ./backend

# Build somente cache (sem push)
docker buildx build --platform linux/amd64,linux/arm64 --output type=cacheonly ./backend
```

---

## 4. Vercel Container Registry (VCR)

### 4.1 O que e

O **VCR** (Vercel Container Registry) e um registro de containers Docker
compativel embutido na Vercel. Permite armazenar imagens OCI e usar
como Vercel Functions ou Vercel Sandbox.

**Referencia da imagem:** `vcr.vercel.com/<team-slug>/<project-name>/<repo>:<tag>`

### 4.2 Configuracao

#### Passo 1 - Verificar projeto linkado

```powershell
# Projeto Vercel
#   projectName: xau-ai-pro-api
#   projectId:   prj_RApeFNVlnOGYxtYcRDqaSUTIJD1G
#   orgId:       team_m6XXhz0AuVtzK0zxtv96h03a

vercel whoami   # deve mostrar: rickjax123-6204
vercel link     # se ainda nao estiver linkado
```

#### Passo 2 - Autenticar container tool

```powershell
vercel vcr login docker
# username: oidc
# token valido por 12 horas
```

#### Passo 3 - Build e push da imagem

```powershell
# A partir da raiz do projeto
vercel vcr build docker ./backend --push
```

Isso vai:
- Fazer build usando o `backend/Dockerfile`
- Criar o repositorio automaticamente
- Publicar em `vcr.vercel.com/apolopanda500/xau-ai-pro-api/backend:latest`

#### Passo 4 - Verificar imagem

```powershell
# Ver tags
vercel vcr tag list xau-ai-pro-backend

# Ver detalhes
vercel vcr tag inspect xau-ai-pro-backend latest

# Pull manual (fora do Vercel)
docker pull vcr.vercel.com/apolopanda500/xau-ai-pro-api/xau-ai-pro-backend:latest
```

### 4.3 Script automatizado

Execute o script completo de setup:

```powershell
.\Tools\vercel_vcr_setup.ps1
```

---

## 5. Arquivos do projeto

| Arquivo | Descricao |
|---------|-----------|
| `Dockerfile.vercel` | Dockerfile para Vercel Functions (raiz) |
| `.gitlab-ci.yml` | Pipeline GitLab CI com Docker Build Cloud |
| `docker-compose.yml` | Orquestracao local (backend + litellm) |
| `backend/Dockerfile` | Dockerfile do backend (usado em CI) |
| `litellm/docker-compose.yml` | Compose do LiteLLM (legado, manter) |
| `Tools/install_docker_windows.ps1` | Instalacao automatica do Docker Desktop |
| `Tools/vercel_vcr_setup.ps1` | Setup do Vercel Container Registry |
| `litellm/README_DOCKER.md` | Docs do LiteLLM com Docker |

---

## 6. Troubleshooting

### "O subsistema Windows para Linux não está instalado"

```powershell
wsl --install
# Reinicie o computador
```

### "docker não é reconhecido"

- Docker Desktop nao esta instalado, ou nao esta rodando
- Instale via `Tools\install_docker_windows.ps1` como Admin
- Apos instalar, reinicie e abra Docker Desktop

### "Cannot connect to Podman socket"

```powershell
podman machine init
podman machine start
podman machine list
```

### "vercel vcr login" falha

- Verifique `vercel whoami` — deve mostrar `rickjax123-6204`
- Rode `vercel login` se nao estiver logado
- Verifique que `docker` (ou Podman) esta no PATH

### Build Cloud "Authentication Error"

- Acesse https://app.docker.com e logue como `rickjax123`
- Verifique que o builder `apolopanda500` existe em
  https://app.docker.com/accounts/rickjax123/cloud/builders
- Se o builder nao existir, crie: Docker Desktop → Settings → Build Cloud