# GUIA NUVEM GRATIS 24/7 — XAU AI PRO (R$ 0,00/mes)

Arquitetura gratuita para rodar o Gateway 24/7 com HTTPS automatico e usar o APK na rua
pelo 4G/5G com o PC de casa desligado.

## Arquitetura

| Camada | Servico gratuito | Papel |
|---|---|---|
| Servidor 24/7 | Oracle Cloud Always Free | VM Ubuntu rodando Gateway FastAPI + Core Rust |
| HTTPS sem abrir portas | Cloudflare Tunnel (Zero Trust) | Endereco `https://...` criptografado apontando para a porta 9027 interna |
| App no celular | XAU AI PRO APK (v1.2.186+) | Conecta direto na URL `https://...` pelo 4G/5G, com auth Bearer fail-closed |

## Pre-requisitos
- Conta Oracle Cloud (Always Free) — regiao Sao Paulo (sa-saopaulo-1)
- Conta Cloudflare One (Zero Trust Free)
- Chave SSH (.key) para acesso a VM

## Passo 1 — Criar a VM gratuita na Oracle Cloud (5 min)

1. No painel OCI (Brazil East - Sao Paulo), clique em **Create a VM instance** (Compute → Instances → Create Instance).
2. Name: `xau-gateway-24-7`
3. Image & Shape (custo R$ 0,00):
   - Image: **Canonical Ubuntu 24.04** (Always Free-eligible). Troque a imagem padrao (Oracle Linux) para Ubuntu — simplifica Docker Compose.
   - Shape: **VM.Standard.A1.Flex** com **2 OCPUs / 12 GB RAM** (dentro da cota gratuita de 4 OCPUs / 24 GB RAM). Alternativa: VM.Standard.E2.1.Micro se faltar capacidade ARM.
4. Networking: marcar **Assign a public IPv4 address**; rede primaria = criar nova VCN publica.
5. SSH Keys: **Save Private Key** (.key) — guarde em pasta segura, so aparece uma vez.
6. Avancar (Storage: manter 50 GB Boot Volume, incluso na cota de 200 GB) → **Create**.
7. Anote o **Public IPv4 Address** quando a instancia ficar RUNNING.

> Se aparecer "Out of capacity for shape VM.Standard.A1.Flex in AD-1", tente AD-2/AD-3 ou o shape E2.1.Micro.

## Passo 2 — Criar o tunel HTTPS gratuito no Cloudflare Zero Trust (3 min)

1. No painel Cloudflare One → **Networks → Tunnels → Create a Tunnel**.
2. Escolha **Cloudflared** → nome `xau-gateway-tunnel` → Save Tunnel.
3. Copie o **Token do Tunel** (`eyJhIjoi...`) do comando de instalacao.
4. (Opcional, com dominio proprio) Adicione uma **Public Hostname**: `https://api.seudominio.com → Service: http://xau-gateway:9027`.
5. (Sem dominio pago) use a URL rapida gratuita `https://...trycloudflare.com` (gerada automaticamente pelo cloudflared).

## Passo 3 — Subir o Gateway 24/7 na VM da Oracle Cloud (1 comando)

Conecte via SSH:
```bash
ssh -i C:\caminho\para\sua_chave.key ubuntu@SEU_IP_PUBLICO_ORACLE
```

Execute o bloco unico:
```bash
# 1. Instalar Docker & Git na VM gratuita
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git openssl
sudo systemctl enable --now docker
sudo usermod -aG docker $USER

# 2. Clonar o repositorio oficial
git clone https://github.com/apolopanda500/XAU_AI_PRO.git
cd XAU_AI_PRO/deploy/cloud_free

# 3. Gerar arquivo .env.cloud seguro com token aleatorio
NOVO_TOKEN=$(openssl rand -hex 32)
cat <<EOF > .env.cloud
XAU_GATEWAY_TOKEN=$NOVO_TOKEN
XAU_MOBILE_CONTROL_ENABLED=1
ALLOW_SELF_REGISTER=0
CLOUDFLARE_TUNNEL_TOKEN=COLE_AQUI_SEU_TOKEN_CLOUDFLARE
EOF

echo "======================================================="
echo "GUARDE SEU TOKEN DE ACESSO DO APP: $NOVO_TOKEN"
echo "======================================================="

# 4. Subir Gateway + Tunel HTTPS 24/7
sudo docker compose up -d --build
```

Verifique:
```bash
sudo docker compose ps
sudo docker compose logs -f xau-gateway
```

## Passo 4 — Comando para o Agente Local preparar o build final do APK (v1.2.186)

Com a URL `https://...` no ar, envie esta instrucao ao agente local para gerar o pacote
`deploy/cloud_free/` e o build limpo v1.2.186 do APK Standalone + Instalador PC
(mantendo `.ex5` de producao `844081BF…`, porta 9027 local e tokens `.env` intocados):

> "Gere o pacote de nuvem gratuita (`deploy/cloud_free/Dockerfile`, `docker-compose.yml`,
> `.env.cloud.example` e `GUIA_NUVEM_GRATIS_24_7.md`) e prepare o build limpo v1.2.186
> do APK Standalone + Instalador PC:
> 1. Garanta que o APK aceite qualquer URL `https://...` externa na tela inicial
>    (`FirstRunWizard.tsx` e configuracoes de conexao) com botao **Testar Conexao HTTPS**
>    antes do login, funcionando 100% no 4G/5G sem precisar de PC ou Wi-Fi local.
> 2. Rode `npx tsc --noEmit`, `npx vitest run` e `pytest -q tests/test_sem_codigo_morto.py
>    tests/test_zero_hardcode_e_marcas.py` ate passar 100% verde e deixe pronto para compilar
>    o APK final assim que eu colar minha URL `https://...` da Oracle/Cloudflare."

## Notas
- O `.ex5` de producao (v1.2.214, MD5 `844081BF2D51D6A4072B150C3DDC6EBD`) e a porta 9027 local
  permanecem intocados — a nuvem roda um gateway separado.
- `XAU_MOBILE_CONTROL_ENABLED=1` ja vem habilitado no `.env.cloud.example` (destravado na nuvem).
- `ALLOW_SELF_REGISTER=0` por padrao (cadastro fechado em producao).
- O gateway de producao nao expoe WebSocket (`/ws/market`); o app cai para HTTP-polling.
  Para feed em tempo real do grafico, adicionar rota WebSocket ao gateway e rebuildar o APK.
- O token gerado (`$NOVO_TOKEN`) deve ser guardado com seguranca e usado no APK standalone
  via `VITE_API_BASE=https://...` (build) ou via tela de login em runtime.
- O MT5 EA (`.ex5`) pode rodar 24/7 instalando o terminal MT5 na VM (Windows) ou via Wine/Docker
  na mesma pasta compartilhada.
