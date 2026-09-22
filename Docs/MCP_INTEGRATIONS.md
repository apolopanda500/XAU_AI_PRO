# Integrações MCP e qualidade

O projeto usa MCP somente para desenvolvimento, testes e observabilidade. MCPs não enviam ordens, não alteram posições e não acessam saques ou transferências.

## Servidores configurados

- **GitHub**: consultar issues, pull requests, commits e workflows.
- **Playwright**: testar a interface desktop/web e os fluxos de conexão.
- **Context7**: consultar documentação atualizada das bibliotecas.
- **Netdata**: acompanhar CPU, memória, gateway e latência.

## Variáveis externas

As credenciais ficam fora do repositório:

- `GITHUB_PERSONAL_ACCESS_TOKEN`
- `CONTEXT7_API_KEY`
- `NETDATA_URL` (opcional; padrão local `http://127.0.0.1:19999`)

Nunca colocar API Keys de corretoras, secrets ou tokens diretamente no `.mcp.json`.

## Validação automática

O workflow `.github/workflows/xau-ai-pro-validation.yml` executa:

1. testes do gateway e adaptadores;
2. verificação TypeScript;
3. build do frontend;
4. empacotamento do gateway;
5. validação do executável gerado.

As conexões de MT5, MEXC e Binance continuam isoladas no gateway, com confirmação, auditoria, `request_id` e saques bloqueados.
