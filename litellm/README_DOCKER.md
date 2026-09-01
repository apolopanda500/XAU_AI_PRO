# ============================================================
# LiteLLM Proxy (Docker) - XAU AI PRO
# ============================================================
# Configura o proxy da porta 4000 usado pelo dashboard:
#   Python/dashboard/app.py -> OpenAI(base_url="http://localhost:4000")
# ============================================================

## REQUISITOS
- Docker Desktop instalado e rodando:
  https://www.docker.com/products/docker-desktop/
- Escolher UM provedor no litellm_config.yaml (Ollama, DeepSeek ou OpenAI).

## PASSO A PASSO
1. Instale o Docker Desktop (se ainda não tiver) e abra-o.

2. Edite `litellm_config.yaml`:
   - Deixe apenas UM bloco de modelo ativo.
   - Se usar Ollama: instale o Ollama no Windows e baixe o modelo:
        ollama pull deepseek-v4-flash
     (o config usa http://host.docker.internal:11434 p/ o Ollama do host)
   - Se usar DeepSeek/OpenAI: defina a chave no seu ambiente
     (ex.: variável DEEPSEEK_API_KEY / OPENAI_API_KEY no Windows, ou
      substitua os.system_env por um valor literal).

3. Suba o container:
     cd C:\Users\Micro\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075\MQL5\Files\XAU_AI_PRO\litellm
     docker compose up -d

4. Verifique:
     docker compose logs -f litellm
     curl http://localhost:4000/v1/models
     # deve listar o modelo configurado

5. Abra o dashboard (painel local):
     C:\Program Files\XAU AI PRO\XAU_AI_PRO.cmd dashboard
   O chat agora conecta em http://localhost:4000.

## TROUBLESHOOTING
- "ollama: connection refused": Ollama não está rodando no host ou o
  modelo não foi baixado. Rode `ollama serve` e `ollama pull ...`.
- "401 / invalid api key": a chave do provedor (DeepSeek/OpenAI) está
  errada ou não configurada.
- Porta 4000 ocupada: outro processo já escuta. Ajuste a porta no
  docker-compose (ex.: "4001:4000") e no app.py.
- Docker não sobe no Windows sem WSL2: habilite WSL2 (wsl --install)
  e reinicie.

## ALTERNATIVA SEM DOCKER (recomendada se não quiser instalar Docker)
Já existe o script que usa o litellm do venv:
    Ultimate\start_proxy.bat
Mesma porta 4000, mesmo fluxo. Requer Ollama instalado (ou editar o
MODEL=... do .bat para um provedor com chave).